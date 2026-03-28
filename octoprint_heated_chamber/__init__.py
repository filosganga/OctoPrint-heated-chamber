# coding=utf-8
from __future__ import absolute_import
from octoprint.util import RepeatedTimer
import octoprint.plugin
from simple_pid import PID

import threading
import flask


from octoprint_heated_chamber.fan import PwmFan
from octoprint_heated_chamber.temperature import Ds18b20, list_ds18b20_devices
from octoprint_heated_chamber.heater import RelayHeater, RelayMode


class HeatedChamberPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.ShutdownPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.EventHandlerPlugin,
):
    def __init__(self):
        self._fan = None
        self._heater = None
        self._temperature_sensor = None
        self._pid = None

        self._temperature_threshold = None
        self._target_temperature = None
        self._timer = None

        self._waiting_for_temperature = False
        self._purging = False
        self._purge_timer = None

    def initialize(self):
        # Fan
        if self._fan is not None:
            self._fan.idle()
            self._fan.destroy()

        pwm_fan_pin = self._settings.get_int(["fan", "pwm", "pin"], merged=True)
        pwm_fan_frequency = self._settings.get_int(
            ["fan", "pwm", "frequency"], merged=True
        )
        pwm_fan_idle_power = self._settings.get_float(
            ["fan", "pwm", "idle_power"], merged=True
        )
        self._fan = PwmFan(
            self._logger, pwm_fan_pin, pwm_fan_frequency, pwm_fan_idle_power
        )
        self._fan.idle()

        # Temperature sensor
        temperature_sensor_ds18b20_device_id = self._settings.get(
            ["temperature_sensor", "ds18b20", "device_id"], merged=True
        )
        temperature_sensor_ds18b20_max_retries = self._settings.get_int(
            ["temperature_sensor", "ds18b20", "max_retries"], merged=True
        )

        if temperature_sensor_ds18b20_device_id:
            self._temperature_sensor = Ds18b20(
                self._logger,
                temperature_sensor_ds18b20_device_id,
                temperature_sensor_ds18b20_max_retries,
            )
        else:
            self._logger.warning(
                "No DS18B20 device configured, temperature sensor disabled"
            )
            self._temperature_sensor = None

        # Heater

        if self._heater is not None:
            self._heater.turn_off()
            self._heater.destroy()

        heater_pin = self._settings.get_int(["heater", "relay", "pin"], merged=True)
        heater_relay_mode = RelayMode(
            self._settings.get_int(["heater", "relay", "relay_mode"], merged=True)
        )
        self._heater = RelayHeater(self._logger, heater_pin, heater_relay_mode)
        self._heater.turn_off()

        # Refresh rate
        refresh_rate = min(60, max(5, self._settings.get_float(["refresh_rate"], merged=True)))

        # PID
        pid_kp = self._settings.get_float(["pid", "kp"], merged=True)
        pid_kd = self._settings.get_float(["pid", "kd"], merged=True)
        pid_ki = self._settings.get_float(["pid", "ki"], merged=True)
        pid_sample_time = refresh_rate - 1

        if self._pid is not None:
            self._pid.Kp = pid_kp
            self._pid.Ki = pid_ki
            self._pid.Kd = pid_kd
            self._pid.sample_time = pid_sample_time
            self._pid.output_limits = (
                self._fan.get_idle_power(),
                self._fan.get_max_power(),
            )
        else:
            self._pid = PID(
                pid_kp,
                pid_ki,
                pid_kd,
                sample_time=pid_sample_time,
                output_limits=(
                    self._fan.get_idle_power(),
                    self._fan.get_max_power(),
                ),
            )

        if self._target_temperature is not None:
            self._pid.setpoint = self._target_temperature
            self._pid.auto_mode = True
        else:
            self._pid.auto_mode = False

        # Misc
        self._temperature_threshold = self._settings.get_float(
            ["temperature_threshold"], merged=True
        )

        self._logger.debug(f"temperature_threshold={self._temperature_threshold}")

        # Timer
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

        self._timer = RepeatedTimer(refresh_rate, self._regulate_chamber, daemon=True)
        self._timer.start()

    ##~~ ShutdownPlugin mixin

    def on_shutdown(self):
        self._logger.debug("on_shutdown called")

        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

        if self._purge_timer is not None:
            self._purge_timer.cancel()
            self._purge_timer = None

        self._temperature_sensor = None

        if self._fan is not None:
            self._fan.destroy()

        if self._heater is not None:
            self._heater.destroy()

        if self._pid is not None:
            self._pid = None

        return octoprint.plugin.ShutdownPlugin.on_shutdown(self)

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return dict(
            refresh_rate=15,
            temperature_threshold=2.5,
            purge_duration=300,
            pid=dict(kp=-5, kd=-0.05, ki=-0.02),
            fan=dict(pwm=dict(pin=18, frequency=25000, idle_power=15)),
            temperature_sensor=dict(
                ds18b20=dict(device_id=None, max_retries=10)
            ),
            heater=dict(relay=dict(pin=23, relay_mode=0)),
        )

    def get_settings_version(self):
        return 1

    def on_settings_save(self, data):
        old_settings = self._settings.get_all_data()
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        new_settings = self._settings.get_all_data()
        if old_settings != new_settings:
            self._logger.info("Settings changed, reinitializing plugin")
            self.initialize()

    def on_settings_load(self):
        data = octoprint.plugin.SettingsPlugin.on_settings_load(self)

        self._logger.debug(f"Settings loaded: {data}")

        return data

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/heated-chamber.js"],
            "css": ["css/heated-chamber.css"],
            "less": ["less/heated-chamber.less"],
        }

    ##~~ SimpleApiPlugin mixin

    def is_api_protected(self):
        return True

    def get_api_commands(self):
        return {"listDs18b20Devices": []}

    def on_api_command(self, command, data):
        if command == "listDs18b20Devices":
            try:
                devices = list_ds18b20_devices()
            except Exception as e:
                self._logger.error(f"Failed to list DS18B20 devices: {e}")
                devices = []
            if not devices:
                self._logger.warning("No DS18B20 devices found. Check 1-wire setup.")
            else:
                self._logger.debug(f"Found DS18B20 devices: {devices}")
            return flask.jsonify({"devices": devices})

    ##~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [dict(type="settings", custom_bindings=True, autoescape=True)]

    ##~~ softwareupdate.check_config hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "HeatedChamber": {
                "displayName": "Heated chamber",
                "displayVersion": self._plugin_version,
                # version check: github repository
                "type": "github_release",
                "user": "filosganga",
                "repo": "OctoPrint-heated-chamber",
                "current": self._plugin_version,
                # update method: pip
                "pip": "https://github.com/filosganga/OctoPrint-heated-chamber/archive/{target_version}.zip",
            }
        }

    ##~~ temperatures.received hook

    # OctoPrint's temperatures_received hook expects the dict to be mutated in place and returned
    def enrich_temperatures(self, comm_instance, parsed_temperatures, *args, **kwargs):
        self._logger.debug(f"Original parsed_temperatures={parsed_temperatures}")

        target_temperature = 0  # 0 means off for the preheat plugin
        if self._target_temperature is not None:
            target_temperature = self._target_temperature

        if self._temperature_sensor is not None:
            parsed_temperatures["C"] = (
                self._temperature_sensor.get_temperature(),
                target_temperature,
            )

        self._logger.debug(f"Enriched parsed_temperatures={parsed_temperatures}")

        return parsed_temperatures

    ##~~ gcode.queuing hook

    def detect_m141_m191(
        self,
        comm_instance,
        phase,
        cmd,
        cmd_type,
        gcode,
        subcode=None,
        tags=None,
        *args,
        **kwargs,
    ):
        # chamber temp can be set either via M141 or M191
        if gcode and (gcode == "M141" or gcode == "M191"):
            target_temperature = int(cmd[cmd.index("S") + 1 :])

            # 0 means no target temp
            if target_temperature == 0:
                target_temperature = None

            self._logger.debug(f"Detected target_temperature={target_temperature}")
            self.set_target_temperature(target_temperature)

            # M191 blocks until target temperature is reached
            if gcode == "M191" and target_temperature is not None:
                self._waiting_for_temperature = True
                self._logger.info(
                    f"M191: holding print until chamber reaches {target_temperature}°C"
                )
                if self._printer is not None:
                    self._printer.set_job_on_hold(True)

            return None

    ##~~ Plugin logic

    def _regulate_chamber(self) -> None:

        try:
            if self._purging:
                return

            target_temperature = self._target_temperature

            if (
                target_temperature is not None
                and self._temperature_sensor is not None
                and self._pid is not None
                and self._heater is not None
                and self._fan is not None
            ):
                current_temperature = self._temperature_sensor.get_temperature()
                new_value = self._pid(current_temperature)

                self._logger.debug(
                    f"New PID value calculated current_temperature={current_temperature}, target_temperature={target_temperature}, new_value={new_value}, pid={self._pid.components}"
                )

                if new_value > self._fan.get_max_power():
                    self._logger.warn(
                        f"PID has produced a value out of range: {new_value}"
                    )
                    new_value = self._fan.get_max_power()
                elif new_value < self._fan.get_idle_power():
                    self._logger.warn(
                        f"PID has produced a value out of range: {new_value}"
                    )
                    new_value = self._fan.get_idle_power()

                self._fan.set_power(new_value)

                if not self._heater.state() and current_temperature < (
                    target_temperature - self._temperature_threshold
                ):
                    self._heater.turn_on()
                elif self._heater.state() and current_temperature > (
                    target_temperature + self._temperature_threshold
                ):
                    self._heater.turn_off()

                # Release hold if M191 was waiting for this temperature
                if self._waiting_for_temperature and current_temperature >= (
                    target_temperature - self._temperature_threshold
                ):
                    self._waiting_for_temperature = False
                    self._logger.info(
                        f"Chamber reached target temperature ({current_temperature}°C), releasing hold"
                    )
                    if self._printer is not None:
                        self._printer.set_job_on_hold(False)

            elif self._heater is not None and self._fan is not None:
                self._heater.turn_off()
                self._fan.idle()

                self._logger.debug(
                    f"No new PID value calculated target_temperature={target_temperature}, "
                    f"temperature_sensor={self._temperature_sensor is not None}, "
                    f"pid={self._pid is not None}"
                )
            else:
                self._logger.debug(
                    f"Skipping the loop: target_temperature={target_temperature is not None}, temperature_sensor={self._temperature_sensor is not None}, pid={self._pid is not None}, heater={self._heater is not None}, fan={self._fan is not None}"
                )

        except Exception as e:
            self._logger.error(f"Error while looping: {e}")

    def set_target_temperature(self, target_temperature):
        old_target = self._target_temperature
        self._target_temperature = target_temperature
        self._logger.debug(
            f"Set target chamber temperature to: {self._target_temperature}"
        )

        if self._target_temperature is not None and self._pid is not None:
            if old_target != self._target_temperature:
                self._pid.reset()
            self._pid.setpoint = self._target_temperature
            self._pid.set_auto_mode(True)
        elif self._pid is not None:
            self._pid.reset()
            self._pid.set_auto_mode(False)

        # React immediately instead of waiting for the next scheduled loop
        self._regulate_chamber()

    ##~~ EventHandlerPlugin mixin

    def on_event(self, event, payload):
        if event in ("PrintDone", "PrintFailed", "PrintCancelled"):
            self._logger.info(
                f"Print ended ({event}), turning off heater and starting purge"
            )
            self._waiting_for_temperature = False
            self.set_target_temperature(None)
            if self._heater is not None:
                self._heater.turn_off()
            self._start_purge()

    def _start_purge(self):
        if self._purge_timer is not None:
            self._purge_timer.cancel()
            self._purge_timer = None

        purge_duration = self._settings.get_int(["purge_duration"], merged=True)
        self._logger.info(f"Starting purge: fan at 100% for {purge_duration}s")
        self._purging = True
        if self._fan is not None:
            self._fan.set_power(self._fan.get_max_power())

        self._purge_timer = threading.Timer(purge_duration, self._end_purge)
        self._purge_timer.daemon = True
        self._purge_timer.start()

    def _end_purge(self):
        self._logger.info("Purge complete, returning fan to idle")
        self._purging = False
        self._purge_timer = None
        if self._fan is not None:
            self._fan.idle()


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Heated chamber"


# Set the Python version your plugin is compatible with below. Recommended is Python 3 only for all new plugins.
# OctoPrint 1.4.0 - 1.7.x run under both Python 3 and the end-of-life Python 2.
# OctoPrint 1.8.0 onwards only supports Python 3.
__plugin_pythoncompat__ = ">=3,<4"  # Only Python 3


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = HeatedChamberPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.temperatures.received": __plugin_implementation__.enrich_temperatures,
        "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.detect_m141_m191,
    }
