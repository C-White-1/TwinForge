from pathlib import Path
import xml.etree.ElementTree as ET

from twinforge.converters.l5x import captured_to_source_extension
from twinforge.parsers.l5x.capture import CapturedSection, capture_section
from twinforge.schema.l5x import CONTROLLER_ATTRIBUTES, CONTROLLER_ELEMENTS


SAMPLE_L5X = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"


def test_sample_program_and_routines_are_captured_recursively():
    controller_element = ET.parse(SAMPLE_L5X).getroot().find("Controller")
    assert controller_element is not None
    controller = capture_section(
        controller_element,
        CONTROLLER_ATTRIBUTES,
        CONTROLLER_ELEMENTS,
    )

    programs = controller.elements["Programs"][0]
    program = programs.elements["Program"][0]

    assert isinstance(program, CapturedSection)
    assert program.attributes == {
        "Name": "MainProgram",
        "TestEdits": "false",
        "MainRoutineName": "MainRoutine",
        "Disabled": "false",
        "UseAsFolder": "false",
    }
    assert program.extra_attributes == {}
    assert set(program.elements) == {"Tags", "Routines"}

    routines = program.elements["Routines"][0].elements["Routine"]
    assert len(routines) == 10
    assert routines[0].attributes == {"Name": "MainRoutine", "Type": "RLL"}
    assert routines[-1].attributes == {"Name": "R08_Outputs", "Type": "RLL"}
    assert "RLLContent" in routines[0].elements
    rungs = routines[0].elements["RLLContent"][0].elements["Rung"]
    assert rungs[0].attributes == {"Number": "0", "Type": "N"}
    rung_text = rungs[0].elements["Text"][0].text
    assert rung_text is not None
    assert "JSR(R00_AnalogAlarms,0);" in rung_text


def test_program_source_extension_preserves_routine_logic_content():
    controller_element = ET.parse(SAMPLE_L5X).getroot().find("Controller")
    assert controller_element is not None
    controller = capture_section(
        controller_element,
        CONTROLLER_ATTRIBUTES,
        CONTROLLER_ELEMENTS,
    )
    program = controller.elements["Programs"][0].elements["Program"][0]

    extension = captured_to_source_extension(program)
    routines = next(child for child in extension.root.children if child.name == "Routines")
    main_routine = routines.children[0]
    rll_content = main_routine.children[0]

    assert main_routine.attributes == {"Name": "MainRoutine", "Type": "RLL"}
    assert rll_content.name == "RLLContent"
    assert rll_content.children[0].name == "Rung"
    source_text = rll_content.children[0].children[1].text
    assert source_text is not None
    assert "JSR(R00_AnalogAlarms,0);" in source_text
