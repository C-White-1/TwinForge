"""Compatibility wrapper for ``twinforge report``."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.cli import main as twinforge_main


def main() -> int:
    """Translate the original positional interface to the installed CLI."""
    parser = argparse.ArgumentParser(
        description="Export model-driven reports through the TwinForge CLI."
    )
    parser.add_argument("source", type=Path, help="Source L5X file")
    parser.add_argument("destination", type=Path, help="Report directory")
    args = parser.parse_args()
    return twinforge_main(
        (
            "report",
            str(args.source),
            "--output",
            str(args.destination),
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
