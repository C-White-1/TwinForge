"""Compare two native CODESYS visualization exports."""

import argparse
from pathlib import Path

from twinforge.analysis.codesys_visualization_diff import (
    compare_codesys_visualizations,
)
from twinforge.exporters.codesys_visualization_diff_markdown import (
    CodesysVisualizationDiffMarkdownExporter,
)
from twinforge.parsers.codesys_native import CodesysNativeExportParser


def main() -> None:
    """Run the controlled-differential report."""
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    archive_parser = CodesysNativeExportParser()
    before = archive_parser.parse(args.before)
    after = archive_parser.parse(args.after)
    result = compare_codesys_visualizations(before, after)
    report = CodesysVisualizationDiffMarkdownExporter().export(result)
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
