import xml.etree.ElementTree as ET
from pathlib import Path

from twinforge.converters import DiagnosticSeverity
from twinforge.converters.l5x import convert_program
from twinforge.parsers import L5XParser
from twinforge.parsers.l5x.capture import capture_section
from twinforge.schema.l5x import PROGRAM_ATTRIBUTES, PROGRAM_ELEMENTS


SAMPLE_L5X = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def _program(xml: str):
    return capture_section(
        ET.fromstring(xml),
        PROGRAM_ATTRIBUTES,
        PROGRAM_ELEMENTS,
    )


def test_parser_converts_sample_program_and_routine_shells():
    parser = L5XParser()

    plant = parser.parse(SAMPLE_L5X, report_mode=None)

    controller = plant.controllers[0]
    program = controller.get_program("MainProgram")
    assert program is not None
    assert program.parent is controller
    assert program.test_edits is False
    assert program.disabled is False
    assert program.use_as_folder is False
    assert len(program.routines) == 10
    assert program.main_routine is program.get_routine("MainRoutine")
    assert program.main_routine is not None
    assert program.main_routine.language == "RLL"
    assert sum(len(routine.ladder_rungs) for routine in program.routines.values()) == 134
    first_rung = program.main_routine.ladder_rungs[0]
    assert first_rung.number == 0
    assert first_rung.rung_type == "N"
    assert first_rung.comment is not None
    assert "BOOSTER GAS COMPRESSOR STATION" in first_rung.comment
    assert first_rung.text == "JSR(R00_AnalogAlarms,0);"
    assert first_rung.source_extensions[0].root.name == "Rung"
    assert program.main_routine.parent is program
    assert program.source_extensions[0].root.name == "Program"
    assert program.main_routine.source_extensions[0].root.children[0].name == (
        "RLLContent"
    )
    assert parser.diagnostics == []


def test_program_converter_reports_invalid_metadata_and_references():
    section = _program(
        """
        <Program Name="Broken" Disabled="perhaps" MainRoutineName="Missing">
          <Routines>
            <Routine Name="Future" Type="FutureLanguage"><FutureLogic /></Routine>
            <Routine Name="Future" Type="RLL" />
            <Routine Type="RLL" />
          </Routines>
        </Program>
        """
    )
    diagnostics = []

    program = convert_program(section, diagnostics=diagnostics)

    assert list(program.routines) == ["Future"]
    assert program.main_routine is None
    assert program.routines["Future"].language == "FutureLanguage"
    assert (
        program.routines["Future"].source_extensions[0].root.children[0].name
        == "FutureLogic"
    )
    assert {item.code for item in diagnostics} == {
        "invalid_boolean",
        "unknown_routine_language",
        "duplicate_routine_name",
        "routine_missing_name",
        "unresolved_main_routine",
    }
    assert any(item.severity is DiagnosticSeverity.ERROR for item in diagnostics)


def test_rll_conversion_reports_bad_rungs_without_losing_logic():
    section = _program(
        """
        <Program Name="RungProblems" MainRoutineName="Main">
          <Routines>
            <Routine Name="Main" Type="RLL">
              <RLLContent>
                <Rung Number="bad" Type="N"><Text>XIC(Start)OTE(Run);</Text></Rung>
                <Rung Number="1" Type="N"><Comment>Keep me</Comment></Rung>
                <Rung Number="1" Type="N"><Text>OTE(Done);</Text></Rung>
                <Rung Type="N"><Text>OTE(MissingNumber);</Text></Rung>
              </RLLContent>
            </Routine>
          </Routines>
        </Program>
        """
    )
    diagnostics = []

    program = convert_program(section, diagnostics=diagnostics)

    routine = program.get_routine("Main")
    assert routine is not None
    assert len(routine.ladder_rungs) == 4
    assert routine.ladder_rungs[0].number is None
    assert routine.ladder_rungs[0].text == "XIC(Start)OTE(Run);"
    assert routine.ladder_rungs[1].comment == "Keep me"
    assert routine.ladder_rungs[3].source_extensions[0].root.attributes["Type"] == "N"
    assert {item.code for item in diagnostics} == {
        "invalid_integer",
        "rung_text_missing",
        "duplicate_rung_number",
        "rung_number_missing",
    }
