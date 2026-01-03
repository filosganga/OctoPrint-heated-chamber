import random
import glob
import time
from os.path import basename
from octoprint.util import RepeatedTimer


class TemperatureSensor:
    def get_temperature(self) -> float:
        pass


class DummyTemperatureSensor(TemperatureSensor):
    def get_temperature(self) -> float:
        return random.uniform(15.0, 70.0)


class Ds18b20(TemperatureSensor):
    def __init__(self, logger, update_frequency, device_id, max_retries=10):
        self._logger = logger
        self._update_frequency = update_frequency
        self._device_id = device_id
        self._max_retries = max_retries

        self._running = False
        self._temperature = None
        self._device_file = f"/sys/bus/w1/devices/{device_id}/w1_slave"
        self._timer = RepeatedTimer(
            self._update_frequency, self._loop, condition=self.is_running, daemon=True
        )

        self._logger.debug(
            f"Ds18b20 initiated with update_frequency={self._update_frequency}, device_id={self._device_id}, max_retries={self._max_retries}"
        )

    def is_running(self) -> bool:
        return self._running

    def get_temperature(self) -> float:
        return self._temperature

    def start(self) -> None:
        self._running = True
        self._timer.start()
        self._logger.debug("Ds18b20 sensor started")

    def stop(self) -> None:
        self._timer.cancel()
        self._running = False
        self._logger.debug("Ds18b20 sensor stopped")

    def _read_temp_raw(self):
        with open(self._device_file, "r") as f:
            lines = f.readlines()
        return lines

    def _loop(self):
        retries = 0
        lines = self._read_temp_raw()
        while lines[0].strip()[-3:] != "YES":
            retries += 1
            if retries >= self._max_retries:
                self._logger.warning(
                    f"DS18B20 sensor read timed out after {self._max_retries} retries"
                )
                return
            time.sleep(0.2)
            lines = self._read_temp_raw()

        equals_pos = lines[1].find("t=")
        if equals_pos != -1:
            temp_string = lines[1][equals_pos + 2 :]
            temp_value = float(temp_string) / 1000.0
            if temp_value == 85.0:
                self._logger.warning(
                    "DS18B20 returned 85.0°C (power-on reset value), ignoring reading"
                )
                return
            self._temperature = temp_value


def list_ds18b20_devices():
    base_dir = "/sys/bus/w1/devices/"
    folders = glob.glob(base_dir + "28*")
    device_names = list(map(lambda path: basename(path), folders))

    return device_names
