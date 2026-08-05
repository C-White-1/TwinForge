from __future__ import annotations

from io import StringIO
from pathlib import Path

from twinforge.cli import main


DATA = Path(__file__).parent / "data"
CONTROLLER = DATA / "basic/BoosterCompressor_20260128.L5X"


def test_report_writes_controller_engineering_bundle(tmp_path: Path) -> None:
    destination = tmp_path / "reports"
    output = StringIO()
    errors = StringIO()

    result = main(
        ("report", str(CONTROLLER), "--output", str(destination)),
        stdout=output,
        stderr=errors,
    )

    assert result == 0
    assert errors.getvalue() == ""
    assert {path.name for path in destination.iterdir()} == {
        "controller.txt",
        "tags.txt",
        "datatypes.txt",
        "add_on_instructions.txt",
        "modules.txt",
        "tasks.txt",
        "programs.txt",
    }
    assert "Exported 7 reports" in output.getvalue()
    assert "1756-IB16" in (destination / "modules.txt").read_text(
        encoding="utf-8"
    )


def test_report_rejects_non_controller_target(tmp_path: Path) -> None:
    destination = tmp_path / "reports"
    errors = StringIO()

    result = main(
        (
            "report",
            str(DATA / "standalone/program.L5X"),
            "--output",
            str(destination),
        ),
        stderr=errors,
    )

    assert result == 1
    assert not destination.exists()
    assert "require a Controller L5X target" in errors.getvalue()


def test_report_returns_failure_for_invalid_source(tmp_path: Path) -> None:
    errors = StringIO()

    assert main(
        (
            "report",
            str(tmp_path / "missing.L5X"),
            "--output",
            str(tmp_path / "reports"),
        ),
        stderr=errors,
    ) == 1
    assert "cannot generate reports" in errors.getvalue()
