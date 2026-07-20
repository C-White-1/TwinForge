import xml.etree.ElementTree as ET
from pathlib import Path

from twinforge.converters import DiagnosticSeverity
from twinforge.converters.l5x import convert_task
from twinforge.model import Program
from twinforge.parsers import L5XParser
from twinforge.parsers.l5x.capture import capture_section
from twinforge.schema.l5x import TASK_ATTRIBUTES, TASK_ELEMENTS


SAMPLE_L5X = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def _task(xml: str):
    return capture_section(ET.fromstring(xml), TASK_ATTRIBUTES, TASK_ELEMENTS)


def test_parser_converts_sample_task_and_resolves_scheduled_program():
    parser = L5XParser()

    plant = parser.parse(SAMPLE_L5X, report_mode=None)

    controller = plant.controllers[0]
    task = controller.get_task("MainTask")
    program = controller.get_program("MainProgram")
    assert task is not None
    assert program is not None
    assert task.parent is controller
    assert task.task_type == "CONTINUOUS"
    assert task.priority == 10
    assert task.watchdog == 500
    assert task.disable_update_outputs is False
    assert task.inhibited is False
    assert task.scheduled_program_names == ["MainProgram"]
    assert task.scheduled_programs == [program]
    assert task.scheduled_programs[0] is program
    assert task.source_extensions[0].root.name == "Task"
    assert parser.diagnostics == []


def test_task_converter_preserves_order_and_reports_unresolved_programs():
    first = Program(name="First")
    section = _task(
        """
        <Task Name="Periodic" Type="PERIODIC" Rate="100"
              Priority="bad" InhibitTask="perhaps">
          <ScheduledPrograms>
            <ScheduledProgram Name="First" />
            <ScheduledProgram Name="Missing" />
          </ScheduledPrograms>
        </Task>
        """
    )
    diagnostics = []

    task = convert_task(section, {"First": first}, diagnostics=diagnostics)

    assert task.rate == 100
    assert task.priority is None
    assert task.inhibited is None
    assert task.scheduled_program_names == ["First", "Missing"]
    assert task.scheduled_programs == [first]
    assert {item.code for item in diagnostics} == {
        "invalid_integer",
        "invalid_boolean",
        "unresolved_scheduled_program",
    }
    unresolved = next(
        item for item in diagnostics if item.code == "unresolved_scheduled_program"
    )
    assert unresolved.severity is DiagnosticSeverity.ERROR
    assert unresolved.raw_value == "Missing"


def test_task_converter_reports_unknown_type_and_missing_periodic_rate():
    unknown_diagnostics = []
    periodic_diagnostics = []

    unknown = convert_task(
        _task('<Task Name="Future" Type="FUTURE" />'),
        {},
        diagnostics=unknown_diagnostics,
    )
    convert_task(
        _task('<Task Name="Periodic" Type="PERIODIC" />'),
        {},
        diagnostics=periodic_diagnostics,
    )

    assert unknown.task_type == "FUTURE"
    assert unknown_diagnostics[0].code == "unknown_task_type"
    assert periodic_diagnostics[0].code == "periodic_rate_missing"


def test_missing_scheduled_program_name_is_preserved_in_source():
    section = _task(
        """
        <Task Name="Broken" Type="CONTINUOUS">
          <ScheduledPrograms><ScheduledProgram Future="keep" /></ScheduledPrograms>
        </Task>
        """
    )
    diagnostics = []

    task = convert_task(section, {}, diagnostics=diagnostics)

    reference = task.source_extensions[0].root.children[0].children[0]
    assert reference.attributes == {"Future": "keep"}
    assert diagnostics[0].code == "scheduled_program_missing_name"
