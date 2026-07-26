"""Generate human-readable engineering reports from an L5X project."""

import argparse
from pathlib import Path

from twinforge.exporters import TextReportExporter
from twinforge.parsers import L5XParser


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export model-driven text reports from an L5X file."
    )
    parser.add_argument("source", type=Path, help="Source L5X file")
    parser.add_argument("destination", type=Path, help="Report directory")
    args = parser.parse_args()

    plant = L5XParser().parse(args.source, report_mode=None)
    controllers = list(plant.iter_controllers())
    if len(controllers) != 1:
        raise ValueError(f"expected one controller, found {len(controllers)}")

    paths = TextReportExporter().export(controllers[0]).write_to(
        args.destination
    )
    print(f"Exported {len(paths)} reports to {args.destination}")


if __name__ == "__main__":
    main()
