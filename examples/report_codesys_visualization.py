"""Create an inventory from a native CODESYS visualization export."""

import argparse
from pathlib import Path

from twinforge.exporters.codesys_visualization_markdown import (
    CodesysVisualizationMarkdownExporter,
)
from twinforge.parsers.codesys_native import CodesysNativeExportParser


def main() -> None:
    """Run the command-line report."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    document = CodesysNativeExportParser().parse(args.source)
    report = CodesysVisualizationMarkdownExporter().export(document)
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
