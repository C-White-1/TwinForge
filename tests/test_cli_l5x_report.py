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
        "tag_dependencies.md",
        "tag_dependencies.csv",
        "tag_dependencies.json",
        "alarm_trip_candidates.md",
        "alarm_trip_candidates.csv",
        "alarm_trip_candidates.json",
    }
    assert "Exported 13 reports" in output.getvalue()
    assert "1756-IB16" in (destination / "modules.txt").read_text(
        encoding="utf-8"
    )
    dependency_report = (destination / "tag_dependencies.md").read_text(
        encoding="utf-8"
    )
    assert "booster_compressor tag and program dependency report" in (
        dependency_report
    )
    assert "## Unresolved references" in dependency_report
    alarm_report = (destination / "alarm_trip_candidates.md").read_text(
        encoding="utf-8"
    )
    assert "alarm and trip candidate report" in alarm_report
    assert "not a verified alarm philosophy" in alarm_report


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
