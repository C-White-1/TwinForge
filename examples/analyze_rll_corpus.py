"""Publish per-fixture RLL conversion coverage for an L5X directory."""

from __future__ import annotations

import argparse
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

from twinforge.analysis import analyze_rll_coverage
from twinforge.model import Controller, Identity, Program
from twinforge.parsers.l5x import L5XParser


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Directory containing L5X fixtures")
    parser.add_argument("output", type=Path, help="Markdown report destination")
    args = parser.parse_args()

    rows: list[tuple[str, str, str, str, str]] = []
    for path in sorted(args.source.rglob("*.L5X")):
        relative = path.relative_to(args.source).as_posix()
        try:
            document = L5XParser().parse_document(path)
        except (ET.ParseError, OSError, ValueError) as error:
            rows.append(
                (
                    relative,
                    "Parse failure",
                    "Not measured",
                    "Not measured",
                    str(error).replace("|", "\\|"),
                )
            )
            continue
        controller = _coverage_controller(document.target)
        if controller is None:
            rows.append(
                (
                    relative,
                    document.target_type.value,
                    "Not applicable",
                    "Not applicable",
                    "No controller/program RLL body",
                )
            )
            continue
        report = analyze_rll_coverage(controller)
        rows.append(
            (
                relative,
                document.target_type.value,
                f"{report.executable_rungs}/{report.total_rungs}",
                (
                    f"{report.executable_instruction_occurrences}/"
                    f"{report.total_instruction_occurrences}"
                ),
                f"{len(report.issues)} blocking rung(s)",
            )
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(_markdown(args.source, rows), encoding="utf-8")
    print(f"Wrote coverage for {len(rows)} fixtures to {args.output}")


def _coverage_controller(target: object) -> Controller | None:
    if isinstance(target, Controller):
        return target
    if isinstance(target, Program):
        controller = Controller(name="Fixture", identity=Identity())
        controller.add_program(target)
        return controller
    return None


def _markdown(source: Path, rows: list[tuple[str, str, str, str, str]]) -> str:
    lines = [
        "# Per-fixture L5X RLL coverage",
        "",
        f"Source corpus: `{source.as_posix()}`",
        "",
        "Coverage means executable by the current PLCopen/CODESYS lowering; it is",
        "not a claim of general Logix compatibility.",
    ]
    for fixture, target, rungs, instructions, notes in rows:
        lines.extend(
            [
                "",
                f"## `{fixture}`",
                "",
                f"- Target: {target}",
                f"- Executable rungs: {rungs}",
                f"- Executable instructions: {instructions}",
            ]
        )
        lines.extend(
            textwrap.wrap(
                notes,
                width=76,
                initial_indent="- Notes: ",
                subsequent_indent="  ",
            )
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
