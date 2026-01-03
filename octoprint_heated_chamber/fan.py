import pigpio


class Fan:
    def set_power(self, power) -> None:
        pass

    def get_power(self) -> float:
        pass

    def destroy(self) -> None:
        pass


class DummyFan(Fan):
    def __init__(self, logger):
        self._logger = logger
        self._power = 0
        pass

    def set_power(self, power) -> None:
        self._power = power
        self._logger.debug(f"Set power to {self._power}")
        pass

    def get_power(self):
        return self._power


class PwmFan(Fan):
    """A class the represent a PWM controlled fan"""

    def __init__(self, logger, pwm_pin, pwm_frequency, idle_power):
        self._logger = logger
        self._frequency = pwm_frequency
        self._pin = pwm_pin
        self._pi = pigpio.pi()
        self._idle_power = idle_power
        self._power = idle_power
        self._connected = self._pi.connected

        if not self._connected:
            self._logger.error("Error connecting to pigpio daemon. Fan control disabled.")
            return

        self.set_power(self._idle_power)

    def destroy(self):
        if self._connected:
            self._pi.stop()

    def get_max_power(self) -> float:
        return 100

    def get_idle_power(self) -> float:
        return self._idle_power

    def idle(self) -> None:
        self.set_power(self._idle_power)

    def get_power(self) -> float:
        return self._power

    def set_power(self, power) -> None:
        self._logger.debug(f"Setting power to {power}")

        assert power >= 0
        assert power <= 100

        self._power = power
        self._logger.debug(f"Set power to {self._power}")
        if self._connected:
            self._pi.hardware_PWM(
                self._pin, self._frequency, self._pwm_duty_cycle(self._power)
            )

    def _pwm_duty_cycle(self, power) -> int:
        return int(power / 100 * 1000000)
