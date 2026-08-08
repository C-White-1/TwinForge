"""Compatibility wrapper for ``twinforge export --target automationml``."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.cli import main as twinforge_main


def main() -> int:
    """Translate the original positional interface to the installed CLI."""
    parser = argparse.ArgumentParser(
        description="Export AutomationML through the TwinForge CLI."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--plcopen", type=Path)
    parser.add_argument("--base-library", type=Path, required=True)
    parser.add_argument("--xsd", type=Path)
    args = parser.parse_args()
    command = [
        "export",
        str(args.source),
        "--target",
        "automationml",
        "--output",
        str(args.destination),
        "--base-library",
        str(args.base_library),
    ]
    if args.plcopen is not None:
        command.extend(("--plcopen-reference", str(args.plcopen)))
    if args.xsd is not None:
        command.extend(("--xsd", str(args.xsd)))
    return twinforge_main(command)


if __name__ == "__main__":
    raise SystemExit(main())
