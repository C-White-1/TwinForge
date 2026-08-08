"""Compatibility wrapper for PLCopen and CODESYS installed CLI targets."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.cli import main as twinforge_main


def main() -> int:
    """Translate the original profile option to one installed target."""
    parser = argparse.ArgumentParser(
        description="Export L5X through the installed TwinForge CLI."
    )
    parser.add_argument("source", type=Path, help="Source L5X file")
    parser.add_argument("destination", type=Path, help="Destination XML file")
    parser.add_argument(
        "--profile",
        choices=("standard_201", "codesys"),
        default="standard_201",
        help="Legacy profile name mapped to an installed export target",
    )
    parser.add_argument("--xsd", type=Path)
    args = parser.parse_args()
    target = "plcopen" if args.profile == "standard_201" else "codesys"
    command = [
        "export",
        str(args.source),
        "--target",
        target,
        "--output",
        str(args.destination),
    ]
    if args.xsd is not None:
        command.extend(("--xsd", str(args.xsd)))
    return twinforge_main(command)


if __name__ == "__main__":
    raise SystemExit(main())
