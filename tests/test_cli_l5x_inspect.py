from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

from twinforge.cli import main


DATA = Path(__file__).parent / "data"


def test_inspect_standalone_module_as_json() -> None:
    output = StringIO()
    errors = StringIO()

    result = main(
        ("inspect", str(DATA / "standalone/module.L5X"), "--format", "json"),
        stdout=output,
        stderr=errors,
    )

    assert result == 0
    assert errors.getvalue() == ""
    report = json.loads(output.getvalue())
    assert report["target_type"] == "Module"
    assert report["target_name"] == "DriveModule"
    assert report["summary"]["catalog_number"] == "ETHERNET-MODULE"
    assert report["summary"]["vendor_id"] == 1
    assert isinstance(report["diagnostics"], list)


def test_inspect_controller_as_text() -> None:
    output = StringIO()

    result = main(
        ("inspect", str(DATA / "basic/BoosterCompressor_20260128.L5X")),
        stdout=output,
    )

    assert result == 0
    assert "L5X target: Controller" in output.getvalue()
    assert "Program Count:" in output.getvalue()
    assert "Diagnostics:" in output.getvalue()


def test_inspect_aoi_reports_lifecycle_evidence() -> None:
    output = StringIO()

    assert main(
        ("inspect", str(DATA / "standalone/aoi.L5X"), "--format", "json"),
        stdout=output,
    ) == 0

    report = json.loads(output.getvalue())
    assert report["target_type"] == "AddOnInstructionDefinition"
    assert "execute_prescan" in report["summary"]
    assert "scan_mode_routine_count" in report["summary"]


def test_inspect_missing_and_malformed_l5x_return_failure(tmp_path: Path) -> None:
    errors = StringIO()
    assert main(
        ("inspect", str(tmp_path / "missing.L5X")), stderr=errors
    ) == 1
    assert "cannot inspect L5X" in errors.getvalue()

    malformed = tmp_path / "malformed.L5X"
    malformed.write_text("<RSLogix5000Content>", encoding="utf-8")
    errors = StringIO()
    assert main(("inspect", str(malformed)), stderr=errors) == 1
    assert "cannot inspect L5X" in errors.getvalue()
