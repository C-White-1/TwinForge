"""Round-trip a native CODESYS visualization through the neutral model."""

import argparse
from pathlib import Path

from twinforge.converters.codesys_visualization import (
    convert_codesys_visualization,
)
from twinforge.exporters.codesys_native_visualization import (
    CodesysNativeVisualizationExporter,
)
from twinforge.parsers.codesys_native import CodesysNativeExportParser


def main() -> None:
    """Parse, lower, and safely re-export a source-backed visualization."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    parsed = CodesysNativeExportParser().parse(args.source)
    document = convert_codesys_visualization(parsed)
    result = CodesysNativeVisualizationExporter().export(document)
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(result.xml, encoding="utf-8")


if __name__ == "__main__":
    main()
