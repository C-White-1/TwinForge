"""Resolve Structured Text symbols and calls in an L5X document."""

import argparse
from pathlib import Path

from twinforge.analysis import analyze_structured_text_semantics
from twinforge.parsers import L5XParser


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze captured Structured Text semantics."
    )
    parser.add_argument("source", type=Path, help="Source L5X file")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional text report destination",
    )
    args = parser.parse_args()

    plant = L5XParser().parse(args.source, report_mode=None)
    controllers = list(plant.iter_controllers())
    if len(controllers) != 1:
        raise ValueError(f"expected one controller, found {len(controllers)}")

    text = analyze_structured_text_semantics(controllers[0]).render_text()
    print(text, end="")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
