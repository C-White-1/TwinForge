import argparse
import csv
from pathlib import Path
from typing import Any, Iterable, TypedDict, cast

from twinforge.model import Controller, Module, Plant
from twinforge.parsers import L5XParser


CSV_FIELDS = ("Slot", "Type", "CatalogNumber", "Vendor")


class ModuleRow(TypedDict):
    """One stable row in the module inventory CSV contract."""

    Slot: str
    Type: str
    CatalogNumber: str
    Vendor: str


def module_rows(filename: str | Path) -> Iterable[ModuleRow]:
    plant = L5XParser().parse(filename, report_mode=None)
    yield from plant_rows(plant)


def plant_rows(plant: Plant) -> Iterable[ModuleRow]:
    for controller in plant.iter_controllers():
        for chassis in controller.iter_chassis():
            for chassis_module in chassis.iter_modules():
                for module in _module_tree(chassis_module):
                    yield _module_row(
                        module,
                        controller,
                        is_root_slot=chassis_module.slot == 0,
                    )


def export_module_csv(source: str | Path, destination: str | Path) -> None:
    destination = Path(destination)
    with destination.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        # ``csv.DictWriter`` infers literal field-name keys that TypedDict
        # cannot currently express covariantly in its ``writerows`` stub.
        writer.writerows(cast(Any, module_rows(source)))


def _module_row(
    module: Module,
    controller: Controller,
    *,
    is_root_slot: bool,
) -> ModuleRow:
    is_controller = (
        is_root_slot and module.catalog == controller.identity.product_name
    )
    return {
        "Slot": str(module.slot) if module.slot is not None else (module.address or ""),
        "Type": "Controller" if is_controller else _module_type(module),
        "CatalogNumber": module.catalog,
        "Vendor": str(module.identity.vendor) if module.identity.vendor else "",
    }


def _module_tree(module: Module) -> Iterable[Module]:
    yield module
    for child in module.child_modules:
        yield from _module_tree(child)


def _module_type(module: Module) -> str:
    connection_types = {
        connection.connection_type
        for connection in module.connections
        if connection.connection_type
    }
    return "/".join(sorted(connection_types))


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
