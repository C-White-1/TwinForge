"""Analyze L5X Add-On Instructions before target-specific conversion."""

import argparse
from pathlib import Path

from twinforge.analysis import analyze_aoi_portability
from twinforge.exporters import AOIPlantUMLExporter
from twinforge.parsers import L5XParser


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assess AOI portability from captured model evidence."
    )
    parser.add_argument("source", type=Path, help="Source L5X file")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional text report destination",
    )
    parser.add_argument(
        "--puml",
        type=Path,
        help="Optional PlantUML diagram destination",
    )
    args = parser.parse_args()

    plant = L5XParser().parse(args.source, report_mode=None)
    controllers = list(plant.iter_controllers())
    if len(controllers) != 1:
        raise ValueError(f"expected one controller, found {len(controllers)}")

    report = analyze_aoi_portability(controllers[0])
    text = report.render_text()
    print(text, end="")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    if args.puml is not None:
        args.puml.parent.mkdir(parents=True, exist_ok=True)
        args.puml.write_text(
            AOIPlantUMLExporter().export(report),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
