"""Export the composed PowerFlex core and CODESYS module adapter."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.exporters import (
    CodesysIRPLCopenExporter,
    PowerFlex525CodesysDevice,
    build_codesys_sys_module_binding_unit,
    build_powerflex525_iec_unit,
    powerflex525_codesys_application_integration,
    powerflex525_codesys_multi_application_integration,
)


def _drive(value: str) -> PowerFlex525CodesysDevice:
    """Parse ``NAME=DEVICE_VARIABLE`` from the command line."""

    name, separator, device_variable = value.partition("=")
    if not separator or not name or not device_variable:
        raise argparse.ArgumentTypeError(
            "drive must use NAME=DEVICE_VARIABLE"
        )
    try:
        return PowerFlex525CodesysDevice(name, device_variable)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def main() -> int:
    """Write the composed importable PLCopen XML application."""

    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--device-variable",
        default="Dev_PF525",
        help="single configured CODESYS RemoteAdapter_diag IEC object",
    )
    parser.add_argument(
        "--drive",
        action="append",
        default=[],
        type=_drive,
        metavar="NAME=DEVICE_VARIABLE",
        help=(
            "repeatable named drive instance; when supplied, replaces "
            "--device-variable"
        ),
    )
    args = parser.parse_args()
    integration = (
        powerflex525_codesys_multi_application_integration(
            tuple(args.drive)
        )
        if args.drive
        else powerflex525_codesys_application_integration(
            args.device_variable
        )
    )
    result = CodesysIRPLCopenExporter().export(
        build_powerflex525_iec_unit(),
        additional_units=(build_codesys_sys_module_binding_unit(),),
        destination=args.destination,
        project_name="TwinForgePowerFlex525Application",
        integration=integration,
    )
    print(f"Wrote {args.destination}")
    return 0 if result.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
