import argparse
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

from twinforge.parsers.l5x.capture import CapturedSection, capture_section
from twinforge.schema.l5x import CONTROLLER_ATTRIBUTES, CONTROLLER_ELEMENTS
from twinforge.schema.l5x.modules import MODULE_ATTRIBUTES


CSV_FIELDS = ("Slot", "Type", "CatalogNumber", "Vendor")


def module_rows(filename: str | Path) -> Iterable[dict[str, str]]:
    root = ET.parse(filename).getroot()
    controller = root.find("Controller")
    if controller is None:
        raise ValueError("L5X file does not contain a Controller element.")

    captured = capture_section(
        controller,
        CONTROLLER_ATTRIBUTES,
        CONTROLLER_ELEMENTS,
    )

    for modules in captured.elements.get("Modules", []):
        for module in modules.elements.get("Module", []):
            yield {
                "Slot": _module_slot(module),
                "Type": _module_type(module),
                "CatalogNumber": module.attributes.get("CatalogNumber", ""),
                "Vendor": _vendor(module.attributes.get("Vendor")),
            }


def export_module_csv(source: str | Path, destination: str | Path) -> None:
    destination = Path(destination)
    with destination.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(module_rows(source))


def _module_slot(module: CapturedSection) -> str:
    addressed_ports = [
        port
        for ports in module.elements.get("Ports", [])
        for port in ports.elements.get("Port", [])
        if "Address" in port.attributes
    ]
    upstream = next(
        (
            port
            for port in addressed_ports
            if port.attributes.get("Upstream") == "true"
        ),
        None,
    )
    port = upstream or (addressed_ports[0] if addressed_ports else None)
    return port.attributes["Address"] if port is not None else ""


def _module_type(module: CapturedSection) -> str:
    if module.attributes.get("ParentModule") == module.attributes.get("Name"):
        return "Controller"

    connection_types = {
        connection.attributes["Type"]
        for communications in module.elements.get("Communications", [])
        for connections in communications.elements.get("Connections", [])
        for connection in connections.elements.get("Connection", [])
        if connection.attributes.get("Type")
    }
    return "/".join(sorted(connection_types))


def _vendor(vendor_id: str | None) -> str:
    if vendor_id is None:
        return ""
    for known_id, label in MODULE_ATTRIBUTES["Vendor"].value_labels:
        if str(known_id) == vendor_id:
            return label
    return vendor_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export an L5X module inventory to CSV."
    )
    parser.add_argument("source", type=Path, help="Source L5X file")
    parser.add_argument("destination", type=Path, help="Destination CSV file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    export_module_csv(args.source, args.destination)
    print(f"Exported module inventory to {args.destination}")


if __name__ == "__main__":
    main()
