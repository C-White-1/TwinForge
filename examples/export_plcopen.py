import argparse
from pathlib import Path

from twinforge.exporters import (
    PLCopenExporter,
    PLCopenProfile,
    PLCopenValidationUnavailable,
    validate_plcopen_xml,
)
from twinforge.parsers import L5XParser


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export an L5X file as PLCopen XML.")
    parser.add_argument("source", type=Path, help="Source L5X file")
    parser.add_argument("destination", type=Path, help="Destination XML file")
    parser.add_argument(
        "--profile",
        choices=[profile.value for profile in PLCopenProfile],
        default=PLCopenProfile.STANDARD_201.value,
        help="PLCopen output profile",
    )
    parser.add_argument(
        "--xsd",
        type=Path,
        help="Optional PLCopen 2.01 XSD used to validate standard_201 output",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    parser = L5XParser()
    plant = parser.parse(args.source, report_mode=None)
    controllers = list(plant.iter_controllers())
    if len(controllers) != 1:
        raise ValueError(f"expected one controller, found {len(controllers)}")

    exporter = PLCopenExporter(args.profile)
    result = exporter.export(
        controllers[0],
        destination=args.destination,
        project_name=plant.name,
    )
    if args.xsd:
        if exporter.profile is not PLCopenProfile.STANDARD_201:
            raise ValueError("the supplied 2.01 XSD validates only the standard_201 profile")
        try:
            validate_plcopen_xml(result.xml, args.xsd)
        except PLCopenValidationUnavailable as error:
            raise SystemExit(str(error)) from error

    print(f"Exported PLCopen XML to {args.destination}")
    for diagnostic in [*parser.diagnostics, *result.diagnostics]:
        name = f" [{diagnostic.object_name}]" if diagnostic.object_name else ""
        print(f"{diagnostic.severity.value.upper()} {diagnostic.code}{name}: {diagnostic.message}")


if __name__ == "__main__":
    main()
