"""Export one L5X controller for native OpenPLC evaluation."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from twinforge.parsers import L5XParser
from twinforge.targets.openplc import OpenPLCExporter


def _creation_time(value: str) -> datetime:
    """Parse an ISO 8601 timestamp supplied on the command line."""

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "creation time must be an ISO 8601 timestamp"
        ) from error


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export an L5X controller as standard PLCopen XML for OpenPLC.",
    )
    parser.add_argument("source", type=Path, help="Source L5X file")
    parser.add_argument("destination", type=Path, help="Destination XML file")
    parser.add_argument(
        "--creation-time",
        type=_creation_time,
        help="Optional ISO 8601 timestamp for deterministic output",
    )
    return parser.parse_args()


def main() -> None:
    """Parse one controller and write OpenPLC-targeted PLCopen XML."""

    args = _arguments()
    parser = L5XParser()
    plant = parser.parse(args.source, report_mode=None)
    controllers = list(plant.iter_controllers())
    if len(controllers) != 1:
        raise ValueError(f"expected one controller, found {len(controllers)}")

    result = OpenPLCExporter().export(
        controllers[0],
        destination=args.destination,
        project_name=plant.name,
        creation_time=args.creation_time,
    )

    print(f"Exported OpenPLC evaluation document to {args.destination}")
    for diagnostic in [*parser.diagnostics, *result.diagnostics]:
        name = f" [{diagnostic.object_name}]" if diagnostic.object_name else ""
        print(
            f"{diagnostic.severity.value.upper()} "
            f"{diagnostic.code}{name}: {diagnostic.message}"
        )


if __name__ == "__main__":
    main()
