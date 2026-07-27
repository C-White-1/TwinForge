"""Export a cyclic I/O contract from related L5X component files."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.analysis import analyze_cyclic_io_contract
from twinforge.exporters import CyclicIOContractMarkdownExporter
from twinforge.model import AddOnInstruction, Module
from twinforge.parsers.l5x import L5XParser


def export_cyclic_io_report(
    aoi_source: Path,
    module_source: Path,
    destination: Path,
) -> None:
    """Parse the AOI context and module connection, then write Markdown."""

    parser = L5XParser()
    plant = parser.parse(aoi_source, report_mode=None)
    controller = next(iter(plant.controllers))
    implementation = next(
        item
        for item in controller.add_on_instructions.values()
        if item.name == "Dvc_PF525"
    )
    module_document = parser.parse_document(module_source)
    if not isinstance(module_document.target, Module):
        raise ValueError(f"expected a Module export: {module_source}")
    connection = (
        module_document.target.connections[0]
        if module_document.target.connections
        else None
    )
    report = analyze_cyclic_io_contract(
        controller,
        _require_aoi(implementation),
        connection,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        CyclicIOContractMarkdownExporter().export(report),
        encoding="utf-8",
    )


def _require_aoi(value: object) -> AddOnInstruction:
    if not isinstance(value, AddOnInstruction):
        raise TypeError("selected implementation is not an AOI")
    return value


def main() -> None:
    """Parse command-line arguments and export the report."""

    parser = argparse.ArgumentParser(
        description="Export an AOI cyclic I/O contract."
    )
    parser.add_argument("aoi_source", type=Path)
    parser.add_argument("module_source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    export_cyclic_io_report(
        args.aoi_source,
        args.module_source,
        args.destination,
    )
    print(f"Exported cyclic I/O report to {args.destination}")


if __name__ == "__main__":
    main()
