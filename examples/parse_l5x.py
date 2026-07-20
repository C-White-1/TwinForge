import argparse
from collections.abc import Iterable
from pathlib import Path

from twinforge.converters import ConversionDiagnostic
from twinforge.model import Module, Plant
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
        default="none",
        help="Capture report detail level. Defaults to none.",
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
    parser.add_argument(
        "--list-modules",
        action="store_true",
        help="List modules beneath each chassis.",
    )
    parser.add_argument(
        "--list-tags",
        action="store_true",
        help="List controller- and program-scoped tags.",
    )
    parser.add_argument(
        "--list-routines",
        action="store_true",
        help="List routines beneath each program.",
    )
    return parser.parse_args()


def print_model_summary(
    plant: Plant,
    *,
    list_modules: bool = False,
    list_tags: bool = False,
    list_routines: bool = False,
) -> None:
    print(f"Plant: {plant.name}")

    for controller in plant.iter_controllers():
        modules = list(_controller_modules(controller))
        print(f"\nController: {controller.name}")
        print(f"  Processor: {controller.identity.product_name or 'Unknown'}")
        print(f"  Chassis: {len(controller.chassis)}")
        print(f"  Modules: {len(modules)}")
        print(f"  Datatypes: {len(controller.datatypes)}")
        print(f"  Controller tags: {len(controller.tags)}")
        print(f"  Programs: {len(controller.programs)}")
        print(f"  Tasks: {len(controller.tasks)}")
        if controller.unplaced_modules:
            print(f"  Unplaced modules: {len(controller.unplaced_modules)}")

        if list_modules:
            for chassis in controller.iter_chassis():
                print(f"\n  Chassis: {chassis.name}")
                for module in chassis.iter_modules():
                    _print_module(module, indent="    ")
            if controller.unplaced_modules:
                print("\n  Unplaced modules:")
                for module in controller.unplaced_modules:
                    _print_module(module, indent="    ")

        if list_tags and controller.tags:
            print("\n  Controller tags:")
            for tag in controller.iter_tags():
                detail = tag.alias_for or tag.data_type or "Unknown"
                print(f"    {tag.name}: {tag.tag_type or 'Unknown'} ({detail})")

        for program in controller.iter_programs():
            print(f"\n  Program: {program.name}")
            main_name = program.main_routine.name if program.main_routine else "None"
            print(f"    Main routine: {main_name}")
            print(f"    Program tags: {len(program.tags)}")
            print(f"    Routines: {len(program.routines)}")
            if list_tags and program.tags:
                print("    Tags:")
                for tag in program.iter_tags():
                    detail = tag.alias_for or tag.data_type or "Unknown"
                    print(f"      {tag.name}: {tag.tag_type or 'Unknown'} ({detail})")
            if list_routines:
                print("    Routine list:")
                for routine in program.iter_routines():
                    print(f"      {routine.name}: {routine.language or 'Unknown'}")

        for task in controller.iter_tasks():
            programs = ", ".join(task.scheduled_program_names) or "None"
            print(f"\n  Task: {task.name}")
            print(f"    Type: {task.task_type or 'Unknown'}")
            print(f"    Programs: {programs}")


def print_diagnostics(diagnostics: Iterable[ConversionDiagnostic]) -> None:
    diagnostics = list(diagnostics)
    if not diagnostics:
        return
    print(f"\nDiagnostics: {len(diagnostics)}")
    for diagnostic in diagnostics:
        location = f" [{diagnostic.object_name}]" if diagnostic.object_name else ""
        print(
            f"  {diagnostic.severity.value.upper()} {diagnostic.code}{location}: "
            f"{diagnostic.message}"
        )


def _controller_modules(controller) -> Iterable[Module]:
    for chassis in controller.iter_chassis():
        for module in chassis.iter_modules():
            yield from _module_tree(module)
    for module in controller.unplaced_modules:
        yield from _module_tree(module)


def _module_tree(module: Module) -> Iterable[Module]:
    yield module
    for child in module.child_modules:
        yield from _module_tree(child)


def _print_module(module: Module, *, indent: str) -> None:
    location = f"slot {module.slot}" if module.slot is not None else (
        f"address {module.address}" if module.address else "unaddressed"
    )
    vendor = str(module.identity.vendor) if module.identity.vendor else "Unknown"
    print(f"{indent}{location}: {module.name} [{module.catalog}] ({vendor})")
    for child in module.child_modules:
        _print_module(child, indent=indent + "  ")


def main() -> None:
    args = parse_args()
    parser = L5XParser()

    report_mode = None if args.report_mode == "none" else args.report_mode
    plant = parser.parse(
        args.filename,
        report_mode=report_mode,
        report_depth=args.report_depth,
    )

    print_model_summary(
        plant,
        list_modules=args.list_modules,
        list_tags=args.list_tags,
        list_routines=args.list_routines,
    )
    print_diagnostics(parser.diagnostics)


if __name__ == "__main__":
    main()
