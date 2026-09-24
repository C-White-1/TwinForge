from io import StringIO
from pathlib import Path

from twinforge.cli import main


_SINGLE_NETWORK = '''<FEFExchangeFile><logicConf><resource><taskDesc task="MAST" taskType="cyclic">
<sectionDesc name="Rungs"/></taskDesc></resource></logicConf>
<program><identProgram name="Rungs" task="MAST"/>
<LDSource nbColumns="11"><networkLD>
<typeLine>
<contact typeContact="openContact" contactVariableName="A"/>
<HLink nbCells="9"/>
<coil typeCoil="coil" coilVariableName="Out"/>
</typeLine>
</networkLD></LDSource>
</program></FEFExchangeFile>'''


def _write(tmp_path: Path, xml: str) -> Path:
    path = tmp_path / "ladder.xef"
    path.write_text(xml, encoding="utf-8")
    return path


def test_cli_renders_one_svg_per_network(tmp_path: Path):
    path = _write(tmp_path, _SINGLE_NETWORK)
    out_dir = tmp_path / "out"
    output = StringIO()

    assert main(("control-expert", "render", str(path), "--output", str(out_dir)), stdout=output) == 0

    files = sorted(out_dir.glob("*.svg"))
    assert len(files) == 1
    svg = files[0].read_text(encoding="utf-8")
    assert svg.startswith("<svg ")
    assert ">A<" in svg
    assert ">Out<" in svg
    assert "1 rungs ->" in output.getvalue()


def test_cli_render_filters_by_routine_name(tmp_path: Path):
    path = _write(tmp_path, _SINGLE_NETWORK)
    out_dir = tmp_path / "out"

    assert main(
        ("control-expert", "render", str(path), "--output", str(out_dir), "--routine", "NoSuchRoutine"),
        stdout=StringIO(), stderr=(errors := StringIO()),
    ) == 1
    assert "no matching ladder network found" in errors.getvalue()


def test_cli_render_has_clean_error_on_missing_input(tmp_path: Path):
    output, errors = StringIO(), StringIO()

    assert main(
        ("control-expert", "render", str(tmp_path / "missing.xef"), "--output", str(tmp_path / "out")),
        stdout=output, stderr=errors,
    ) == 1
    assert not output.getvalue()
    assert "could not inspect Control Expert input" in errors.getvalue()
