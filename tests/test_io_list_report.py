from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from twinforge.analysis import build_io_list_report
from twinforge.exporters import IOListCSVExporter, IOListMarkdownExporter
from twinforge.parsers import L5XParser


SAMPLE = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def test_renders_reviewable_markdown_and_complete_csv() -> None:
    controller = L5XParser().parse(SAMPLE, report_mode=None).controllers[0]
    report = build_io_list_report(controller)

    markdown = IOListMarkdownExporter().export(report)
    rows = list(csv.DictReader(StringIO(IOListCSVExporter().export(report))))

    assert "## Channels" in markdown
    assert "## Unresolved local aliases" in markdown
    assert "Spare candidates" in markdown
    pt102 = next(row for row in rows if "PT102_PV" in row["AssignedTags"])
    assert pt102["CatalogNumber"] == "1756-IF8"
    assert pt102["EngineeringUnit"] == "barg"
    assert pt102["LowerRange"] == "0.0"
    assert pt102["UpperRange"] == "150.0"
