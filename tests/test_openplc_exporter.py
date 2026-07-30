import ast
from datetime import datetime, timezone
import inspect
import xml.etree.ElementTree as ET

from twinforge.exporters import (
    PLCOPEN_201_NAMESPACE,
    PLCopenExporter,
    PLCopenProfile,
)
from twinforge.model import (
    Controller,
    Identity,
    LadderRung,
    Program,
    Routine,
    Tag,
    Task,
)
from twinforge.targets.openplc import OpenPLCExporter
from twinforge.targets.openplc import exporter as openplc_module


FIXED_TIME = datetime(2026, 7, 30, tzinfo=timezone.utc)


def _controller() -> Controller:
    controller = Controller(name="OpenPLCTest", identity=Identity())
    controller.add_tag(Tag(name="Enable", data_type="BOOL"))
    controller.add_tag(Tag(name="Output", data_type="BOOL"))
    program = Program(name="PLC_PRG")
    routine = Routine(name="MainRoutine", language="RLL")
    routine.ladder_rungs.append(
        LadderRung(number=0, text="XIC(Enable)OTE(Output);")
    )
    program.add_routine(routine)
    controller.add_program(program)
    controller.add_task(
        Task(
            name="MainTask",
            task_type="Periodic",
            rate=20,
            priority=1,
            scheduled_program_names=[program.name],
            scheduled_programs=[program],
        )
    )
    return controller


def test_openplc_target_matches_standard_plcopen_profile() -> None:
    controller = _controller()
    expected = PLCopenExporter(PLCopenProfile.STANDARD_201).export(
        controller,
        project_name="OpenPLC Project",
        creation_time=FIXED_TIME,
    )

    actual = OpenPLCExporter().export(
        controller,
        project_name="OpenPLC Project",
        creation_time=FIXED_TIME,
    )

    assert actual.xml == expected.xml
    assert actual.diagnostics == expected.diagnostics


def test_openplc_document_contains_no_codesys_extensions() -> None:
    result = OpenPLCExporter().export(
        _controller(),
        creation_time=FIXED_TIME,
    )
    root = ET.fromstring(result.xml)

    assert root.tag == f"{{{PLCOPEN_201_NAMESPACE}}}project"
    assert "3s-software.com" not in result.xml
    assert "ProjectStructure" not in result.xml
    assert "ObjectId" not in result.xml


def test_openplc_adapter_has_no_direct_codesys_import() -> None:
    tree = ast.parse(inspect.getsource(openplc_module))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )

    assert not any("codesys" in module.casefold() for module in imported)
