# OctoPrint-heated-chamber

This plugin controls the enclosure temperature via a temperature sensor, a heater and the enclosure air extraction fan.

At the moment it only supports those:

* The DS18B20 temperature sensor
* A PWM-controlled fan
* An active-low GPIO-controlled relay heater

The settings are still a draft and not working

## Prerequisites

### DS18B20 Temperature Sensor Setup

1. Enable the 1-wire interface by adding the following to `/boot/config.txt`:

   ```ini
   dtoverlay=w1-gpio
   ```

2. Reboot the Raspberry Pi:

   ```bash
   sudo reboot
   ```

3. Load the 1-wire kernel modules (these should load automatically after reboot):

   ```bash
   sudo modprobe w1-gpio
   sudo modprobe w1-therm
   ```

4. Verify the sensor is detected:

   ```bash
   ls /sys/bus/w1/devices/
   ```

   You should see a directory starting with `28-` (e.g., `28-0000057065d7`).

### pigpio Daemon

The plugin uses pigpio for PWM fan control. Install and start the daemon:

```bash
sudo apt-get install pigpio
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

```text
https://github.com/filosganga/OctoPrint-heated-chamber/archive/master.zip
```

## Configuration

You can configure the frequency at which the plugin runs the duty cycle, by default every 5 seconds.
