---
layout: plugin

id: HeatedChamber
title: OctoPrint-Heatedchamber
description: Controls a heated printer enclosure using a DS18B20 temperature sensor, relay-controlled heater, and PWM fan with PID control.
authors:
- Filippo De Luca
license: AGPLv3

date: 2026-01-03

homepage: https://github.com/filosganga/OctoPrint-heated-chamber
source: https://github.com/filosganga/OctoPrint-heated-chamber
archive: https://github.com/filosganga/OctoPrint-heated-chamber/archive/master.zip

tags:
- heated chamber
- enclosure
- temperature
- ds18b20
- pid
- raspberry pi
- gpio
- relay
- pwm fan

compatibility:

  octoprint:
  - 1.4.0

  os:
  - linux

  python: ">=3,<4"

---

A plugin for OctoPrint that controls your printer enclosure temperature using a DS18B20 temperature sensor, a relay-controlled heater, and a PWM-controlled extraction fan.

## Features

- **Temperature Monitoring**: Reads temperature from a DS18B20 1-wire sensor
- **PID Control**: Uses PID algorithm to maintain target chamber temperature
- **Heater Control**: Controls a relay-driven heater with configurable GPIO pin and active-high/low modes
- **Fan Control**: PWM control of extraction fan via pigpio daemon
- **G-code Integration**: Responds to M141 (set chamber temp) and M191 (wait for chamber temp) commands
- **OctoPrint Integration**: Displays chamber temperature in OctoPrint's temperature graph

## Requirements

- Raspberry Pi with GPIO access
- DS18B20 temperature sensor connected via 1-wire interface
- Relay module for heater control
- PWM-capable fan for air extraction
- pigpio daemon running (`sudo pigpiod`)

## Configuration

Configure via OctoPrint Settings > Heated Chamber:

- **Temperature Sensor**: Select your DS18B20 device ID and polling frequency
- **Heater**: Set GPIO pin and relay mode (active-high or active-low)
- **Fan**: Configure PWM pin, frequency, and idle power level
- **PID**: Tune Kp, Ki, Kd parameters and sample time
