"""Public read-only Control Expert inspection contract."""
from io import StringIO
import json
from pathlib import Path
import zipfile

from twinforge.cli import main


def test_sfc_inspection_exposes_structure_and_unresolved_execution(tmp_path: Path):
    path = tmp_path / "sequence.xef"
    path.write_text('<FEFExchangeFile><SFCProgram><identProgram name="S"/>'
                    '<chartSource name="C"><networkSFC><step stepName="Start"/>'
                    '<transition/></networkSFC></chartSource></SFCProgram></FEFExchangeFile>')
    output = StringIO()
    assert main(("control-expert", "inspect", str(path), "--format", "json"), stdout=output) == 0
    chart = json.loads(output.getvalue())["projects"][0]["programs"][0]["routines"][0]["sequential_charts"][0]
    assert chart["elements"][0]["children"][0]["properties"]["name"] == "Start"
    assert chart["connectivity_resolved"] is False
    assert chart["execution_resolved"] is False
    output = StringIO()
    assert main(("control-expert", "inspect", str(path)), stdout=output) == 0
    assert "SFC chart C: steps: 1; transitions: 1; connectivity: unresolved; execution unresolved" in output.getvalue()


def exchange(name: str) -> bytes:
    return (f'<ZEFExchangeFile><contentHeader name="{name}"/>'
            '<logicConf><resource><taskDesc task="MAST" taskType="cyclic">'
            '<sectionDesc name="logic"/></taskDesc></resource></logicConf>'
            '<program><identProgram name="logic" task="MAST"/>'
            '<STSource>x := 1;</STSource></program></ZEFExchangeFile>').encode()


def test_inspection_json_is_deterministic_and_leaves_source_unchanged(tmp_path: Path):
    path = tmp_path / "example.xef"
    data = exchange("Example")
    path.write_bytes(data)
    outputs = []
    for _ in range(2):
        output, errors = StringIO(), StringIO()
        assert main(("control-expert", "inspect", str(path), "--format", "json"),
                    stdout=output, stderr=errors) == 0
        assert not errors.getvalue()
        outputs.append(output.getvalue())
    assert outputs[0] == outputs[1]
    report = json.loads(outputs[0])
    assert report["status"] == "inspected"
    assert report["native_validation"] == "not_performed"
    assert report["projects"][0]["tasks"][0]["cycle_policy"] == "successive_cycles_while_active"
    assert report["projects"][0]["programs"][0]["routines"][0]["task_schedule"][0]["section_index"] == 0
    assert path.read_bytes() == data


def test_st_step_state_reference_is_exposed_in_the_tag_dependency_graph(tmp_path: Path):
    path = tmp_path / "step_state.xef"
    path.write_bytes(
        '<ZEFExchangeFile><contentHeader name="Example"/>'
        '<logicConf><resource><taskDesc task="MAST" taskType="cyclic">'
        '<sectionDesc name="Voyants"/></taskDesc></resource></logicConf>'
        '<program><identProgram name="Voyants" task="MAST"/>'
        '<STSource>IF G1_0.X THEN X := TRUE; END_IF;</STSource></program>'
        '<SFCProgram><identProgram name="G1" task="MAST"/><chartSource><networkSFC>'
        '<step stepName="G1_0" stepType="initialStep"/>'
        '</networkSFC></chartSource></SFCProgram></ZEFExchangeFile>'.encode()
    )
    output = StringIO()
    assert main(("control-expert", "inspect", str(path), "--format", "json"), stdout=output) == 0
    graph = json.loads(output.getvalue())["projects"][0]["tag_dependency_graph"]
    assert graph["step_state_references"] == [{
        "step_name": "G1_0", "program_name": "Voyants", "routine_name": "Voyants",
        "operand": "G1_0.X", "line_number": 1,
    }]
    assert graph["ambiguous_step_state_references"] == []


def test_archive_projects_remain_separate_in_text_output(tmp_path: Path):
    path = tmp_path / "examples.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("first.xef", exchange("First"))
        archive.writestr("second.xef", exchange("Second"))
    output = StringIO()
    assert main(("control-expert", "inspect", str(path)), stdout=output) == 0
    assert "Projects: 2" in output.getvalue()
    assert "Project 1: First" in output.getvalue()
    assert "Project 2: Second" in output.getvalue()
    assert "[0] first.xef" in output.getvalue()
    assert "Task MAST (cyclic): logic" in output.getvalue()


def test_partial_capture_emits_report_but_returns_failure(tmp_path: Path):
    path = tmp_path / "partial.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("good.xef", exchange("Good"))
        archive.writestr("broken.zef", b"bad archive")
    output, errors = StringIO(), StringIO()
    assert main(("control-expert", "inspect", str(path), "--format", "json"),
                stdout=output, stderr=errors) == 1
    report = json.loads(output.getvalue())
    assert report["status"] == "incomplete_capture"
    assert len(report["projects"]) == 1
    assert report["capture_diagnostics"][0]["code"] == "archive_read_error"
    assert "capture was incomplete" in errors.getvalue()


def test_unrecognized_input_does_not_report_empty_success(tmp_path: Path):
    path = tmp_path / "not-project.xml"
    path.write_text("<Other/>")
    output, errors = StringIO(), StringIO()
    assert main(("control-expert", "inspect", str(path), "--format", "json"),
                stdout=output, stderr=errors) == 1
    assert json.loads(output.getvalue())["status"] == "no_supported_projects"


def test_missing_input_has_clean_error(tmp_path: Path):
    output, errors = StringIO(), StringIO()
    assert main(("control-expert", "inspect", str(tmp_path / "missing.zef")),
                stdout=output, stderr=errors) == 1
    assert not output.getvalue()
    assert "could not inspect Control Expert input" in errors.getvalue()
