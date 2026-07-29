"""Export the CODESYS EtherNet/IP module-service equivalence report."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.exporters import CodesysModuleEquivalenceMarkdownExporter


def main() -> None:
    """Write the deterministic equivalence report."""

    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    report = CodesysModuleEquivalenceMarkdownExporter().export()
    args.destination.write_text(report, encoding="utf-8")
    print(f"Wrote {args.destination}")


if __name__ == "__main__":
    main()
