from pathlib import Path

from twinforge.analysis import analyze_structured_text
from twinforge.parsers import L5XParser


DATA = Path(__file__).parent / "data/aoi"


def test_controller_analysis_preserves_and_parses_str_capacity():
    plant = L5XParser().parse(
        DATA / "Str_Capacity_AOI.L5X",
        report_mode=None,
    )

    report = analyze_structured_text(next(plant.iter_controllers()))

    assert len(report.routines) == 1
    assert report.total_statements == 1
    assert report.unsupported_statements == 0
    assert report.all_source_preserved
    assert report.routines[0].owner == "AOI:Str_Capacity"
    assert "All source preserved: yes" in report.render_text()
