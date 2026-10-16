"""The text handling of the CODESYS drum pattern editor script.

The script runs inside CODESYS's IronPython; its dialog cannot run here, but
its formatting, reading back and merging of a drum's pattern block can.
"""
import importlib.util
from pathlib import Path

from twinforge.exporters.plcopen_library_checks import DRUM_CONSTANTS

SCRIPT = Path(__file__).parents[1] / "examples/CODESYS/scripts/drum_pattern_editor.py"
_spec = importlib.util.spec_from_file_location("drum_pattern_editor", SCRIPT)
assert _spec is not None and _spec.loader is not None
editor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(editor)  # outside CODESYS: no dialog

_PATTERN = DRUM_CONSTANTS["PATTERN"]
assert isinstance(_PATTERN, tuple)
FIXTURE_WORDS = list(_PATTERN)  # fixture 14: step 1 B0+B1, step 2 B2, step 3 B3
NAMES = ["xLamp0", "xLamp1", "xLamp2", "xLamp3"] + [""] * 12


def test_block_reads_back_what_it_wrote():
    block = editor.format_block("DR0", 4, FIXTURE_WORDS, NAMES)
    declaration = editor.merge_block("", "DR0", block)

    assert editor.parse_block(declaration, "DR0") == (4, FIXTURE_WORDS, NAMES)
    assert "    DR0_NSTEPS : INT := 4;" in declaration
    assert "    DR0_PATTERN : ARRAY[0..7] OF WORD := [" in declaration
    assert "        2#0000_0000_0000_0011,  // step 1" in declaration
    assert "        2#0000_0000_0000_0000  // step 7 (unused)" in declaration  # no comma after the last
    assert declaration.startswith("VAR_GLOBAL CONSTANT\n") and declaration.rstrip().endswith("END_VAR")


def test_editing_replaces_only_that_drums_block():
    first = editor.merge_block("", "DR0", editor.format_block("DR0", 4, FIXTURE_WORDS, NAMES))
    both = editor.merge_block(first, "DR1", editor.format_block("DR1", 2, [0, 1] + [0] * 6, [""] * 16))
    edited = editor.merge_block(both, "DR0", editor.format_block("DR0", 3, [0, 7, 8, 0, 0, 0, 0, 0], NAMES))

    assert edited.count("VAR_GLOBAL CONSTANT") == 1
    assert editor.parse_block(edited, "DR0") == (3, [0, 7, 8, 0, 0, 0, 0, 0], NAMES)
    assert editor.parse_block(edited, "DR1") == (2, [0, 1, 0, 0, 0, 0, 0, 0], [""] * 16)


def test_other_declarations_are_left_alone():
    existing = "VAR_GLOBAL\n    xMotor : BOOL;\nEND_VAR\n"
    merged = editor.merge_block(existing, "DR0", editor.format_block("DR0", 4, FIXTURE_WORDS, NAMES))

    assert merged.startswith(existing)
    assert merged.count("VAR_GLOBAL CONSTANT") == 1
    constant_section = "VAR_GLOBAL CONSTANT\n    xLimit : INT := 5;\nEND_VAR\n"
    merged = editor.merge_block(constant_section, "DR0", editor.format_block("DR0", 4, FIXTURE_WORDS, NAMES))
    assert merged.startswith("VAR_GLOBAL CONSTANT\n    xLimit : INT := 5;\n    // TwinForge drum pattern DR0: begin")


def test_a_drum_without_a_block_is_new():
    assert editor.parse_block("VAR_GLOBAL CONSTANT\nEND_VAR\n", "DR0") is None


def test_drum_names_must_make_iec_identifiers():
    assert editor.valid_drum_name("DR0") and editor.valid_drum_name("Filler_Drum")
    assert not any(editor.valid_drum_name(name) for name in ("0DR", "DR 0", "DR__0", "DR0_", "%DR0", ""))


def test_usage_wires_the_pattern_and_every_bit():
    text = editor.usage("DR0", NAMES)
    # Qualified: CODESYS creates a new list with {attribute 'qualified_only'}.
    assert "NSTEPS := TF_DrumPatterns.DR0_NSTEPS, PATTERN := TF_DrumPatterns.DR0_PATTERN" in text
    assert "PATTERN := MyPatterns.DR0_PATTERN" in editor.usage("DR0", NAMES, "MyPatterns")
    assert "B0 := xLamp0" in text and "B15 := xSpare" in text
