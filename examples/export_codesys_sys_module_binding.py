"""Export the normalized CODESYS EtherNet/IP module binding."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.exporters import (
    CodesysIRPLCopenExporter,
    build_codesys_sys_module_binding_unit,
    codesys_sys_module_binding_integration,
)


def main() -> int:
    """Export the binding function block, PLC_PRG, and MainTask."""

    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    result = CodesysIRPLCopenExporter().export(
        build_codesys_sys_module_binding_unit(),
        destination=args.destination,
        project_name="TwinForgeCodesysSysModuleBinding",
        integration=codesys_sys_module_binding_integration(),
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
