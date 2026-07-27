"""Modify verified fields through the neutral model and export to CODESYS."""

import argparse
from pathlib import Path

from twinforge.converters.codesys_visualization import (
    convert_codesys_visualization,
)
from twinforge.exporters.codesys_native_visualization import (
    CodesysNativeVisualizationExporter,
)
from twinforge.model import VisualizationGeometry
from twinforge.parsers.codesys_native import CodesysNativeExportParser


def main() -> None:
    """Apply explicit control changes and create a source-backed export."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("identifier")
    parser.add_argument("--text")
    parser.add_argument("--x", type=int)
    parser.add_argument("--y", type=int)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    args = parser.parse_args()

    parsed = CodesysNativeExportParser().parse(args.source)
    document = convert_codesys_visualization(parsed)
    control = next(
        (
            control
            for canvas in document.canvases
            for control in canvas.controls
            if control.identifier == args.identifier
        ),
        None,
    )
    if control is None:
        parser.error(f"control not found: {args.identifier}")

    geometry = control.geometry
    control.geometry = VisualizationGeometry(
        x=args.x if args.x is not None else geometry.x,
        y=args.y if args.y is not None else geometry.y,
        width=args.width if args.width is not None else geometry.width,
        height=args.height if args.height is not None else geometry.height,
    )
    if args.text is not None:
        control.text = args.text

    result = CodesysNativeVisualizationExporter().export(document)
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(result.xml, encoding="utf-8")


if __name__ == "__main__":
    main()
