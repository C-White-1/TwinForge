"""Export the composed PowerFlex core and CODESYS module adapter."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.exporters import (
    CodesysIRPLCopenExporter,
    build_codesys_sys_module_binding_unit,
    build_powerflex525_iec_unit,
    powerflex525_codesys_application_integration,
)


def main() -> int:
    """Write the composed importable PLCopen XML application."""

    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--device-variable",
        default="Dev_PF525",
        help="configured CODESYS RemoteAdapter_diag IEC object",
    )
    args = parser.parse_args()
    result = CodesysIRPLCopenExporter().export(
        build_powerflex525_iec_unit(),
        additional_units=(build_codesys_sys_module_binding_unit(),),
        destination=args.destination,
        project_name="TwinForgePowerFlex525Application",
        integration=powerflex525_codesys_application_integration(
            args.device_variable
        ),
    )
    print(f"Wrote {args.destination}")
    return 0 if result.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
