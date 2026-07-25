import argparse
from pathlib import Path

from twinforge.exporters import (
    AutomationMLExporter,
    AutomationMLValidationUnavailable,
    validate_automationml_references,
    validate_automationml_xml,
)
from twinforge.parsers import L5XParser


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export an L5X model as AutomationML 2.1 CAEX."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--plcopen", type=Path)
    parser.add_argument(
        "--base-library",
        type=Path,
        required=True,
        help="AutomationML 2.1 base-library AML reference",
    )
    parser.add_argument(
        "--xsd",
        type=Path,
        help="Optional CAEX 3.0 XSD used to validate the AML output",
    )
    args = parser.parse_args()

    l5x_parser = L5XParser()
    plant = l5x_parser.parse(args.source, report_mode=None)
    controllers = list(plant.iter_controllers())
    if len(controllers) != 1:
        raise ValueError(f"expected one controller, found {len(controllers)}")
    result = AutomationMLExporter().export(
        controllers[0],
        project_name=plant.name,
        plcopen_path=args.plcopen,
        base_library_path=args.base_library,
        destination=args.destination,
    )
    if args.xsd:
        try:
            validate_automationml_xml(result.xml, args.xsd)
        except AutomationMLValidationUnavailable as error:
            raise SystemExit(str(error)) from error
    validate_automationml_references(result.xml, args.destination)
    print(f"Exported AutomationML to {result.destination}")


if __name__ == "__main__":
    main()
