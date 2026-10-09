"""Instruction List -> ladder network conversion for `.smbp` rungs written in IL."""
import pytest

from twinforge.model import LadderInstruction, LadderOperation, LadderParallel, LadderSeries
from twinforge.parsers.machine_expert_basic.instruction_list import build_network_from_instruction_list
from twinforge.parsers.machine_expert_basic.ladder import NetworkUnresolved

_SHORT = {
    LadderOperation.NORMALLY_OPEN_CONTACT: "NO", LadderOperation.NORMALLY_CLOSED_CONTACT: "NC",
    LadderOperation.POSITIVE_TRANSITION_CONTACT: "P", LadderOperation.NEGATIVE_TRANSITION_CONTACT: "N",
    LadderOperation.COIL: "COIL", LadderOperation.SET_COIL: "SET", LadderOperation.RESET_COIL: "RESET",
    LadderOperation.NEGATED_COIL: "NCOIL", LadderOperation.BLOCK_OUTPUT_REFERENCE: "OUT",
}


def shape(series: LadderSeries) -> str:
    parts = []
    for element in series.elements:
        if isinstance(element, LadderParallel):
            parts.append("[" + " | ".join(shape(branch) for branch in element.branches) + "]")
        else:
            if element.expression is not None:  # COMPARISON / ASSIGNMENT: the typed tree
                label = "CMP" if element.operation is LadderOperation.COMPARISON else "ASSIGN"
                parts.append(f"{label}({element.expression.render()})")
                continue
            label = _SHORT.get(element.operation) or element.source_mnemonic
            parts.append(f"{label}({element.operand})")
    return " ".join(parts)


def convert(*lines: str, symbols: dict[str, str] | None = None) -> str:
    return shape(build_network_from_instruction_list(list(lines), symbols))


@pytest.mark.parametrize(("lines", "expected"), [
    (("LD    %I0.0", "ANDN  %I0.1", "ST    %Q0.0"), "NO(%I0.0) NC(%I0.1) COIL(%Q0.0)"),
    (("LD %I0.0", "OR %I0.1", "ST %Q0.0"), "[NO(%I0.0) | NO(%I0.1)] COIL(%Q0.0)"),
    (("LDR %I0.0", "ST %Q0.0"), "P(%I0.0) COIL(%Q0.0)"),
    (("LDF %I0.1", "STN %Q0.1"), "N(%I0.1) NCOIL(%Q0.1)"),
    (("LD %I0.0", "S %Q0.0"), "NO(%I0.0) SET(%Q0.0)"),
    # LD 1 is the always-true rail.
    (("LD 1", "ST %M10"), "COIL(%M10)"),
    # Nested brackets, as 03_nested's IL writes them.
    (("LD %I0.0", "AND( %I0.1", "OR( %I0.2", "AND %I0.3", ")", ")", "ST %Q0.0"),
     "NO(%I0.0) [NO(%I0.1) | NO(%I0.2) NO(%I0.3)] COIL(%Q0.0)"),
    (("LD [ %MW0 > 10 ]", "[ %MW1 := %MW1 + 1 ]"), "CMP(%MW0 > 10) ASSIGN(%MW1 := (%MW1 + 1))"),
    (("LD %I0.0", "OPER [ %MF1 := ( %MF2 * 3.0 ) ]", "ST %Q0.0"),
     "NO(%I0.0) [ASSIGN(%MF1 := (%MF2 * 3.0)) | COIL(%Q0.0)]"),
])
def test_conditions_and_outputs(lines, expected):
    assert convert(*lines) == expected


def test_consecutive_outputs_share_their_condition():
    assert convert("LD %I0.0", "ST %Q0.0", "ST %Q0.1") == "NO(%I0.0) [COIL(%Q0.0) | COIL(%Q0.1)]"


def test_continuing_after_an_output_branches_from_the_shared_condition():
    assert convert("LD %I0.0", "ST %Q0.0", "AND %I0.1", "ST %Q0.1") == \
        "NO(%I0.0) [COIL(%Q0.0) | NO(%I0.1) COIL(%Q0.1)]"


def test_mps_mrd_mpp_rebuild_the_branch_point():
    network = convert("LD %M100", "MPS", "R %Q0.0", "MPP", "AND %I0.0", "MPS", "R %M100", "MRD",
                      "ANDN %I0.2", "S %M101", "MPP", "AND %I0.2", "S %M105")
    assert network == ("NO(%M100) [RESET(%Q0.0) | NO(%I0.0) [RESET(%M100) | NC(%I0.2) SET(%M101) "
                       "| NO(%I0.2) SET(%M105)]]")


def test_block_pins_and_outputs_follow_the_grid_conventions():
    network = convert("BLK %C0", "LD %I0.1", "R", "LD %I0.0", "CU", "OUT_BLK", "LD D", "ST %Q0.0",
                      "LD F", "ST %Q0.1", "END_BLK")
    assert network == ("[NO(%I0.1) Counter(%C0.R) | NO(%I0.0) Counter(%C0.CU) | OUT(%C0.D) COIL(%Q0.0) "
                       "| OUT(%C0.F) COIL(%Q0.1)]")


def test_operands_use_declared_symbols_with_the_address_kept():
    network = build_network_from_instruction_list(["BLK %TM0", "LD %I0.0", "IN", "OUT_BLK", "LD Q", "ST %Q0.0",
                                                   "END_BLK"], {"%I0.0": "START_PB", "%TM0": "DELAY"})
    (parallel,) = network.elements
    assert isinstance(parallel, LadderParallel)
    (contact, pin), (reference, coil) = (branch.elements for branch in parallel.branches)
    assert isinstance(contact, LadderInstruction) and isinstance(pin, LadderInstruction)
    assert isinstance(reference, LadderInstruction) and isinstance(coil, LadderInstruction)
    assert (contact.operand, contact.annotations) == ("START_PB", ("address=%I0.0",))
    assert (pin.operation, pin.source_mnemonic, pin.operand, pin.annotations) == (
        LadderOperation.FUNCTION_BLOCK_INPUT, "Timer", "DELAY.IN", ("address=%TM0",))
    assert (reference.operand, reference.annotations) == ("DELAY.Q", ("address=%TM0",))
    assert (coil.operand, coil.annotations) == ("%Q0.0", ())


@pytest.mark.parametrize("lines", [
    ("LD %I0.0", "RISING0", "ST %Q0.0"),  # rising-edge block: no grid-evidenced IL form yet
    ("LD 1", "MULTIFB", "ST %Q0.0"),  # MULTIFB temporaries are not modelled
    ("LD %I0.0", "AND( %I0.1", "ST %Q0.0"),  # unbalanced bracket
    ("LD %I0.0", "MPP", "ST %Q0.0"),  # MPP without MPS
    ("LD %I0.0", "AND %I0.1"),  # no output
    ("BLK %XYZ0", "LD %I0.0", "IN", "END_BLK"),  # unknown block type
])
def test_unconvertible_instruction_list_is_refused_not_guessed(lines):
    with pytest.raises(NetworkUnresolved) as error:
        build_network_from_instruction_list(list(lines))
    assert error.value.code == "instruction_list_not_converted"
