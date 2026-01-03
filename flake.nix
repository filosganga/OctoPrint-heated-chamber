{
  description = "OctoPrint Heated Chamber Plugin";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3;
        pythonPackages = python.pkgs;
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            python
            pythonPackages.pip
            pythonPackages.setuptools
            pythonPackages.wheel
            pythonPackages.simple-pid
            pythonPackages.flask
            pythonPackages.flask-login

            # Development tools
            pythonPackages.black
            pythonPackages.ruff
            pythonPackages.mypy

            # For RPi GPIO (stubs for local dev, real libs on Pi)
            pkgs.pigpio
          ];

          shellHook = ''
            echo "OctoPrint Heated Chamber development environment"
            echo ""
            echo "Note: Full testing requires a Raspberry Pi with:"
            echo "  - DS18B20 sensor connected via 1-wire"
            echo "  - pigpiod daemon running"
            echo ""
            echo "For local development without hardware:"
            echo "  - The plugin will log errors for missing pigpio connection"
            echo "  - Temperature sensor will fail gracefully"
            echo ""
          '';
        };
      }
    );
}
