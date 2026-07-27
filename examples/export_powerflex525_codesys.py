"""Export the neutral PowerFlex 525 core as importable CODESYS XML."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.exporters import (
    CodesysIRPLCopenExporter,
    build_powerflex525_iec_unit,
    powerflex525_codesys_integration,
)


def main() -> int:
    """Export the portable function block, PLC_PRG, and MainTask."""

    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    result = CodesysIRPLCopenExporter().export(
        build_powerflex525_iec_unit(),
        destination=args.destination,
        project_name="TwinForgePowerFlex525Core",
        integration=powerflex525_codesys_integration(),
    )
    print(f"Wrote {args.destination}")
    for diagnostic in result.diagnostics:
        print(f"{diagnostic.code}: {diagnostic.message}")
    if result.requirements:
        values = ", ".join(item.value for item in result.requirements)
        print(f"Unresolved target requirements: {values}")
    return 0 if result.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
