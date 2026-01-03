# Contributing to OctoPrint Heated Chamber

Thank you for your interest in contributing to this plugin!

## Development Setup

### Prerequisites

- [Nix](https://nixos.org/download.html) with flakes enabled
- For hardware testing: Raspberry Pi with OctoPrint installed

### Local Development Environment

1. Clone the repository:

   ```bash
   git clone https://github.com/filosganga/OctoPrint-heated-chamber.git
   cd OctoPrint-heated-chamber
   ```

2. Enter the Nix development shell:

   ```bash
   nix develop
   ```

   This provides Python with all dependencies, plus development tools (black, ruff, mypy).

### Testing on Raspberry Pi

The plugin requires actual hardware for full testing. On your Raspberry Pi running OctoPrint:

1. Clone or sync the repository to your Pi

2. Install the plugin in development mode:

   ```bash
   # Activate OctoPrint's virtual environment
   source ~/oprint/bin/activate

   # Install in editable mode
   cd /path/to/OctoPrint-heated-chamber
   pip install -e .
   ```

3. Ensure prerequisites are running:

   ```bash
   # Start pigpio daemon
   sudo systemctl start pigpiod

   # Verify DS18B20 sensor is detected
   ls /sys/bus/w1/devices/28-*
   ```

4. Restart OctoPrint:

   ```bash
   sudo systemctl restart octoprint
   ```

5. Changes to Python files require an OctoPrint restart. JavaScript/template changes often just need a browser refresh.

## Code Style

- Python: Format with `black`, lint with `ruff`
- JavaScript: Follow existing style in the codebase

Run before committing:

```bash
black octoprint_heated_chamber/
ruff check octoprint_heated_chamber/
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run code formatters and linters
5. Test on actual hardware if possible
6. Commit with clear, descriptive messages
7. Push to your fork and open a Pull Request

## Hardware Requirements

For full testing, you need:

- Raspberry Pi (3/4/5) with GPIO access
- DS18B20 temperature sensor (1-wire interface)
- Relay module for heater control
- PWM-capable fan

See [README.md](README.md) for hardware setup instructions.

## Reporting Issues

When reporting bugs, please include:

- OctoPrint version
- Plugin version
- Raspberry Pi model
- Relevant logs from OctoPrint (`~/.octoprint/logs/octoprint.log`)
- Hardware configuration (GPIO pins, sensor model)

## License

By contributing, you agree that your contributions will be licensed under the AGPLv3 license.
