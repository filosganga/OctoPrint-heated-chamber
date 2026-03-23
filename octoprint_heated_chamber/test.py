import glob
from os.path import basename


def list_ds18b20_devices():
    base_dir = "/sys/bus/w1/devices/"
    folders = glob.glob(base_dir + "28*")
    device_names = list(map(lambda path: basename(path), folders))

    return device_names


print(list_ds18b20_devices())
