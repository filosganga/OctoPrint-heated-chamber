import random
import glob
import time
from typing import Optional
from os.path import basename


class TemperatureSensor:
    def get_temperature(self) -> Optional[float]:
        pass


class DummyTemperatureSensor(TemperatureSensor):
    def get_temperature(self) -> float:
        return random.uniform(15.0, 70.0)


class Ds18b20(TemperatureSensor):
    def __init__(self, logger, device_id, max_retries=10):
        self._logger = logger
        self._device_id = device_id
        self._max_retries = max_retries

        self._device_file = f"/sys/bus/w1/devices/{device_id}/w1_slave"

        self._logger.debug(
            f"Ds18b20 initiated with device_id={self._device_id}, max_retries={self._max_retries}"
        )

    def get_temperature(self) -> Optional[float]:
        retries = 0
        lines = self._read_temp_raw()
        while lines[0].strip()[-3:] != "YES":
            retries += 1
            if retries >= self._max_retries:
                self._logger.warning(
                    f"DS18B20 sensor read timed out after {self._max_retries} retries"
                )
                return None
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
                return None
            return temp_value

        return None

    def _read_temp_raw(self):
        with open(self._device_file, "r") as f:
            lines = f.readlines()
        return lines


def list_ds18b20_devices():
    base_dir = "/sys/bus/w1/devices/"
    folders = glob.glob(base_dir + "28*")
    device_names = list(map(lambda path: basename(path), folders))

    return device_names
