from pathlib import Path

from twinforge.exporters import TextReportExporter
from twinforge.parsers import L5XParser


SAMPLE_L5X = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def _reports():
    controller = L5XParser().parse(
        SAMPLE_L5X, report_mode=None
    ).controllers[0]
    return TextReportExporter().export(controller)


def test_exports_model_driven_engineering_reports() -> None:
    reports = _reports().files

    assert set(reports) == {
        "controller.txt",
        "tags.txt",
        "datatypes.txt",
        "add_on_instructions.txt",
        "modules.txt",
        "tasks.txt",
        "programs.txt",
    }
    assert "1756-L82E" in reports["controller.txt"]
    assert "CFG_PT102_HH" in reports["tags.txt"]
    assert "120.0" in reports["tags.txt"]
    assert "barg" in reports["tags.txt"]
    assert "1756-IB16" in reports["modules.txt"]
    assert "Digital" in reports["modules.txt"]
    assert "MainTask" in reports["tasks.txt"]
    assert "MainProgram" in reports["tasks.txt"]
    assert "R00_AnalogAlarms" in reports["programs.txt"]
    assert "GRT(PT102_PV,CFG_PT102_HH)" in reports["programs.txt"]


def test_writes_reports_as_utf8(tmp_path: Path) -> None:
    paths = _reports().write_to(tmp_path / "reports")

    assert len(paths) == 7
    assert all(path.is_file() for path in paths)
    assert (tmp_path / "reports/tags.txt").read_text(
        encoding="utf-8"
    ).startswith("CONTROLLER TAGS")
