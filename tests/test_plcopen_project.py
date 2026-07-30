from collections.abc import Sequence
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

from twinforge.exporters.plcopen_project import PLCopenProjectOrchestrator
from twinforge.model import Controller, Identity, Program, Tag, Task


NAMESPACE = "urn:twinforge:test:project"
NS = {"p": NAMESPACE}
CREATION_TIME = datetime(2026, 7, 30, 12, 30, tzinfo=timezone.utc)


def _controller() -> Controller:
    controller = Controller(name="Controller1", identity=Identity())
    controller.add_tag(Tag(name="ControllerTag", data_type="BOOL"))
    controller.add_program(Program(name="FirstProgram"))
    controller.add_program(Program(name="SecondProgram"))
    controller.add_task(Task(name="MainTask"))
    return controller


def test_standard_project_traverses_content_in_source_order() -> None:
    calls: list[tuple[str, object]] = []
    generated = Tag(name="GeneratedTag", data_type="BOOL")

    def emit_program(parent: ET.Element, program: Program) -> None:
        calls.append(("program", program.name))
        ET.SubElement(parent, f"{{{NAMESPACE}}}pou", {"name": program.name})

    def emit_task(parent: ET.Element, task: Task) -> None:
        calls.append(("task", task.name))
        ET.SubElement(parent, f"{{{NAMESPACE}}}task", {"name": task.name})

    def emit_variables(
        parent: ET.Element,
        tags: Sequence[Tag],
    ) -> ET.Element:
        names = tuple(tag.name for tag in tags)
        calls.append(("variables", names))
        return ET.SubElement(parent, f"{{{NAMESPACE}}}globalVars")

    root = PLCopenProjectOrchestrator(
        namespace=NAMESPACE,
        emit_program=emit_program,
        emit_task=emit_task,
        emit_global_variables=emit_variables,
    ).build(
        _controller(),
        [generated],
        project_name="Project1",
        creation_time=CREATION_TIME,
    )

    assert calls == [
        ("program", "FirstProgram"),
        ("program", "SecondProgram"),
        ("task", "MainTask"),
        ("variables", ("ControllerTag", "GeneratedTag")),
    ]
    assert [
        pou.attrib["name"]
        for pou in root.findall("p:types/p:pous/p:pou", NS)
    ] == ["FirstProgram", "SecondProgram"]
    assert root.find(
        "p:instances/p:configurations/p:configuration/"
        "p:resource[@name='Application']/p:task[@name='MainTask']",
        NS,
    ) is not None


def test_headers_and_coordinate_scaling_are_deterministic() -> None:
    root = PLCopenProjectOrchestrator(
        namespace=NAMESPACE,
        emit_program=lambda _parent, _program: None,
        emit_task=lambda _parent, _task: None,
        emit_global_variables=lambda _parent, _tags: None,
    ).build(
        Controller(name="", identity=Identity()),
        [],
        project_name="TwinForge Test",
        creation_time=CREATION_TIME,
    )

    header = root.find("p:fileHeader", NS)
    assert header is not None
    assert header.attrib == {
        "companyName": "TwinForge",
        "productName": "TwinForge",
        "productVersion": "0.1.0",
        "creationDateTime": "2026-07-30T12:30:00+00:00",
    }
    content_header = root.find("p:contentHeader", NS)
    assert content_header is not None
    assert content_header.attrib["name"] == "TwinForge Test"
    for language in ("fbd", "ld", "sfc"):
        scaling = root.find(
            f"p:contentHeader/p:coordinateInfo/p:{language}/p:scaling",
            NS,
        )
        assert scaling is not None and scaling.attrib == {"x": "1", "y": "1"}
    configuration = root.find(
        "p:instances/p:configurations/p:configuration",
        NS,
    )
    assert configuration is not None
    assert configuration.attrib["name"] == "PLC"


def test_target_application_callback_owns_controller_wrapping() -> None:
    calls: list[tuple[str, tuple[str, ...]]] = []
    generated = Tag(name="GeneratedTag", data_type="BOOL")

    def emit_target(
        root: ET.Element,
        controller: Controller,
        generated_tags: Sequence[Tag],
    ) -> None:
        calls.append(
            (
                controller.name,
                tuple(tag.name for tag in generated_tags),
            )
        )
        ET.SubElement(root, f"{{{NAMESPACE}}}targetApplication")

    root = PLCopenProjectOrchestrator(
        namespace=NAMESPACE,
        emit_program=lambda _parent, _program: None,
        emit_task=lambda _parent, _task: None,
        emit_global_variables=lambda _parent, _tags: None,
        emit_target_application=emit_target,
    ).build(
        _controller(),
        [generated],
        project_name="Target Project",
        creation_time=CREATION_TIME,
    )

    assert calls == [("Controller1", ("GeneratedTag",))]
    assert root.find("p:targetApplication", NS) is not None
    assert root.findall("p:types/p:pous/*", NS) == []
    assert root.findall(
        "p:instances/p:configurations/*",
        NS,
    ) == []
