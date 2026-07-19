import csv
import runpy
from pathlib import Path

SAMPLE_L5X = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"
SCRIPT = Path(__file__).parents[1] / "examples/export_module_csv.py"
SCRIPT_GLOBALS = runpy.run_path(str(SCRIPT), run_name="export_module_csv")
export_module_csv = SCRIPT_GLOBALS["export_module_csv"]
module_rows = SCRIPT_GLOBALS["module_rows"]


def test_module_rows_extract_slot_type_catalog_and_vendor():
    rows = list(module_rows(SAMPLE_L5X))

    assert rows[0] == {
        "Slot": "0",
        "Type": "Controller",
        "CatalogNumber": "1756-L82E",
        "Vendor": "Allen-Bradley / Rockwell Automation",
    }
    assert rows[1] == {
        "Slot": "1",
        "Type": "Input",
        "CatalogNumber": "1756-IB16",
        "Vendor": "Allen-Bradley / Rockwell Automation",
    }
    assert rows[3]["Type"] == "Output"


def test_export_module_csv_writes_inventory(tmp_path):
    destination = tmp_path / "modules.csv"

    export_module_csv(SAMPLE_L5X, destination)

    with destination.open(encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) == 7
    assert list(rows[0]) == ["Slot", "Type", "CatalogNumber", "Vendor"]
    assert rows[-1]["Slot"] == "6"
