import argparse
import csv
from pathlib import Path

from twinforge.analysis import RLLCoverageReport, analyze_rll_coverage
from twinforge.parsers import L5XParser


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure PLCopen/CODESYS RLL conversion coverage."
    )
    parser.add_argument("source", type=Path, help="Source L5X file")
    parser.add_argument(
        "--csv",
        type=Path,
        help="Optional destination for the per-instruction CSV table",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    parser = L5XParser()
    plant = parser.parse(args.source, report_mode=None)
    controllers = list(plant.iter_controllers())
    if len(controllers) != 1:
        raise ValueError(f"expected one controller, found {len(controllers)}")

    report = analyze_rll_coverage(controllers[0])
    print_report(args.source, report)
    if args.csv is not None:
        write_csv(args.csv, report)
        print(f"\nInstruction table written to {args.csv}")


def print_report(source: Path, report: RLLCoverageReport) -> None:
    print(f"RLL coverage: {source}")
    print(
        f"Rungs: {report.executable_rungs}/{report.total_rungs} "
        f"executable ({report.rung_coverage_percent:.1f}%)"
    )
    print(
        "Instruction occurrences: "
        f"{report.executable_instruction_occurrences}/"
        f"{report.total_instruction_occurrences} executable "
        f"({report.occurrence_coverage_percent:.1f}%)"
    )
    print(
        f"Distinct mnemonics used: {len(report.instructions)} "
        f"({sum(item.supported_mnemonic for item in report.instructions.values())} "
        "known by the exporter)"
    )

    print("\nInstruction usage")
    print("Mnemonic  Total  Executable  Coverage  Exporter")
    for item in sorted(
        report.instructions.values(),
        key=lambda value: (-value.occurrences, value.mnemonic),
    ):
        status = "supported" if item.supported_mnemonic else "unknown"
        print(
            f"{item.mnemonic:<8}  {item.occurrences:>5}  "
            f"{item.executable_occurrences:>10}  "
            f"{item.occurrence_coverage_percent:>7.1f}%  {status}"
        )

    if not report.issues:
        print("\nStructural blockers: none")
        return
    print(f"\nStructural blockers ({len(report.issues)} rungs)")
    for issue in report.issues:
        number = "?" if issue.rung_number is None else issue.rung_number
        mnemonics = ", ".join(issue.mnemonics) or "(none detected)"
        print(
            f"- {issue.program}/{issue.routine} rung {number}: "
            f"{issue.reason}; instructions: {mnemonics}"
        )
        print(f"  {issue.text}")


def write_csv(destination: Path, report: RLLCoverageReport) -> None:
    with destination.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "mnemonic",
                "occurrences",
                "executable_occurrences",
                "occurrence_coverage_percent",
                "supported_mnemonic",
            ]
        )
        for item in sorted(report.instructions.values(), key=lambda value: value.mnemonic):
            writer.writerow(
                [
                    item.mnemonic,
                    item.occurrences,
                    item.executable_occurrences,
                    f"{item.occurrence_coverage_percent:.1f}",
                    str(item.supported_mnemonic).lower(),
                ]
            )


if __name__ == "__main__":
    main()
