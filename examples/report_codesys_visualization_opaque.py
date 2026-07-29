"""Report unmapped native CODESYS visualization properties."""

import argparse
from pathlib import Path

from twinforge.analysis import inventory_opaque_visualization_properties
from twinforge.exporters import CodesysVisualizationOpaqueMarkdownExporter
from twinforge.parsers.codesys_native import CodesysNativeExportParser


def main() -> None:
    """Parse one native export and write its opaque-property register."""

    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    document = CodesysNativeExportParser().parse(args.source)
    properties = inventory_opaque_visualization_properties(document)
    report = CodesysVisualizationOpaqueMarkdownExporter().export(
        properties,
        profile=document.profile,
    )
    args.destination.write_text(report, encoding="utf-8")
    print(f"Wrote {args.destination}")


if __name__ == "__main__":
    main()
