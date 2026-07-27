"""Export Markdown and CSV parameter reports from a related L5X corpus."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from twinforge.analysis import build_parameter_setpoint_report
from twinforge.assembly import AssembledSoftwareDevice, assemble_corpus_devices
from twinforge.exporters import (
    ParameterReportCSVExporter,
    ParameterReportMarkdownExporter,
)
from twinforge.parsers.l5x import L5XCorpusParser


def export_parameter_report(
    source: Path,
    markdown_destination: Path,
    csv_destination: Path,
    *,
    device_name: str | None = None,
) -> None:
    """Assemble one device and write its parameter reports."""

    corpus = L5XCorpusParser().parse_directory(source)
    candidates = assemble_corpus_devices(corpus)
    selected = _select_device(candidates, device_name)
    report = build_parameter_setpoint_report(selected.device)

    markdown_destination.parent.mkdir(parents=True, exist_ok=True)
    markdown_destination.write_text(
        ParameterReportMarkdownExporter().export(report),
        encoding="utf-8",
    )
    csv_destination.parent.mkdir(parents=True, exist_ok=True)
    csv_destination.write_text(
        ParameterReportCSVExporter().export(report),
        encoding="utf-8-sig",
        newline="",
    )


def _select_device(
    candidates: Sequence[AssembledSoftwareDevice],
    device_name: str | None,
) -> AssembledSoftwareDevice:
    if device_name is not None:
        matches = [
            candidate
            for candidate in candidates
            if candidate.device.name.casefold() == device_name.casefold()
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ValueError(f"assembled device not found: {device_name}")
        raise ValueError(f"assembled device name is ambiguous: {device_name}")
    if len(candidates) == 1:
        return candidates[0]
    raise ValueError(
        "device selection is required when the corpus does not assemble "
        "exactly one device"
    )


def main() -> None:
    """Parse command-line arguments and export both report formats."""

    parser = argparse.ArgumentParser(
        description="Export parameter and setpoint evidence from an L5X corpus."
    )
    parser.add_argument("source", type=Path, help="Related L5X directory")
    parser.add_argument(
        "markdown_destination",
        type=Path,
        help="Destination Markdown report",
    )
    parser.add_argument(
        "csv_destination",
        type=Path,
        help="Destination CSV report",
    )
    parser.add_argument(
        "--device",
        help="Assembled device name when the corpus contains multiple devices",
    )
    args = parser.parse_args()

    try:
        export_parameter_report(
            args.source,
            args.markdown_destination,
            args.csv_destination,
            device_name=args.device,
        )
    except ValueError as error:
        parser.error(str(error))
    print(
        f"Exported parameter reports to {args.markdown_destination} and "
        f"{args.csv_destination}"
    )


if __name__ == "__main__":
    main()
