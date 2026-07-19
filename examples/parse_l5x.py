import argparse
from pathlib import Path

from twinforge.parsers import L5XParser

DEFAULT_L5X = Path("tests/data/basic/BoosterCompressor_20260128.L5X")


def parse_report_depth(value):
    if value.lower() == "unlimited":
        return None

    depth = int(value)
    if depth < 0:
        raise argparse.ArgumentTypeError("report depth must be 0 or greater")
    return depth


def parse_args():
    parser = argparse.ArgumentParser(description="Parse and report an L5X file.")
    parser.add_argument(
        "--report-mode",
        choices=("summary", "debug", "none"),
        default="summary",
        help="Report detail level. Defaults to summary.",
    )
    parser.add_argument(
        "filename",
        nargs="?",
        default=DEFAULT_L5X,
        type=Path,
        help=f"L5X file to parse. Defaults to {DEFAULT_L5X}.",
    )
    parser.add_argument(
        "--report-depth",
        default=2,
        type=parse_report_depth,
        help="Nested report depth. Use a number or 'unlimited'. Defaults to 2.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    parser = L5XParser()

    report_mode = None if args.report_mode == "none" else args.report_mode
    plant = parser.parse(
        args.filename,
        report_mode=report_mode,
        report_depth=args.report_depth,
    )

    print(plant)

    for controller in plant.iter_controllers():
        print(controller)

        for chassis in controller.iter_chassis():
            print(chassis)

            for module in chassis.iter_modules():
                print(module)

        for program in controller.iter_programs():
            print(program)

            for routine in program.iter_routines():
                print(routine)


if __name__ == "__main__":
    main()
