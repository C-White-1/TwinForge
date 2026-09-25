"""Standalone Derived Function Block export (.xdb/.XDB) inspection via the CLI."""
from io import StringIO
import json
from pathlib import Path

from twinforge.cli import main


def _xdb(name: str) -> bytes:
    return (
        '<FBExchangeFile>'
        '<fileHeader company="Schneider Automation" product="UnitySoControl V14.0" '
        'dateTime="date_and_time#2021-1-29-13:34:41" content="Function Block source file" '
        'DTDVersion="41"></fileHeader>'
        '<contentHeader name="Project" version="0.0.1" dateTime="date_and_time#2021-1-29-12:59:44"></contentHeader>'
        f'<FBSource nameOfFBType="{name}">'
        '<inputParameters><variables name="A" typeName="INT"/></inputParameters>'
        '<outputParameters><variables name="SUM" typeName="INT"/></outputParameters>'
        '<FBProgram><STSource>SUM := A + 1;</STSource></FBProgram>'
        '</FBSource></FBExchangeFile>'
    ).encode()


def test_inspect_reports_a_standalone_dfb_library_as_json(tmp_path: Path):
    path = tmp_path / "block.xdb"
    path.write_bytes(_xdb("M_ADD"))
    output = StringIO()

    assert main(("control-expert", "inspect", str(path), "--format", "json"), stdout=output) == 0

    report = json.loads(output.getvalue())
    assert report["status"] == "inspected"
    assert report["projects"] == []
    assert len(report["function_block_libraries"]) == 1
    library = report["function_block_libraries"][0]
    assert library["name"] == "M_ADD"
    aoi = library["function_blocks"][0]
    assert [(p["name"], p["usage"]) for p in aoi["parameters"]] == [("A", "input"), ("SUM", "output")]
    assert aoi["body"][0]["language"] == "ST"


def test_inspect_reports_a_standalone_dfb_library_as_text(tmp_path: Path):
    path = tmp_path / "block.xdb"
    path.write_bytes(_xdb("M_ADD"))
    output = StringIO()

    assert main(("control-expert", "inspect", str(path)), stdout=output) == 0

    text = output.getvalue()
    assert "Standalone Function Block libraries: 1" in text
    assert "Function Block library 1: M_ADD" in text
    assert "Parameters: 2; local tags: 0; body sections: 1" in text


def test_inspect_of_an_xdb_with_no_project_still_exits_cleanly(tmp_path: Path):
    path = tmp_path / "block.xdb"
    path.write_bytes(_xdb("Solo"))
    output = StringIO()

    assert main(("control-expert", "inspect", str(path)), stdout=output) == 0
