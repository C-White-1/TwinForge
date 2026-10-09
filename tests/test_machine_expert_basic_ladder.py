"""Ladder network building from synthetic `.smbp` grid cells: the paths the fixtures do not reach."""
import pytest

from twinforge.model import LadderInstruction, LadderOperation, LadderParallel, LadderPosition, LadderSeries
from twinforge.parsers.machine_expert_basic.ladder import NetworkUnresolved, build_network


def cell(kind: str, row: int, column: int, connection: str = "Left, Right", **fields: str) -> dict[str, str]:
    return {"ElementType": kind, "Row": str(row), "Column": str(column), "ChosenConnection": connection, **fields}


def wire(row: int, first: int, last: int) -> list[dict[str, str]]:
    return [cell("Line", row, column) for column in range(first, last + 1)]


def instruction(operation: LadderOperation, kind: str, operand: str | None, row: int, column: int,
                annotations: tuple[str, ...] = ()) -> LadderInstruction:
    return LadderInstruction(operation, kind, operand, annotations=annotations,
                             position=LadderPosition(column=column, row=row))


def instructions(series: LadderSeries) -> list[LadderInstruction]:
    """A branch's elements, asserted to be plain instructions."""
    assert all(isinstance(element, LadderInstruction) for element in series.elements)
    return [element for element in series.elements if isinstance(element, LadderInstruction)]


def test_series_contacts_and_coil():
    cells = [cell("NormalContact", 0, 0, Descriptor="%I0.0"), *wire(0, 1, 9), cell("Coil", 0, 10, "Left", Descriptor="%Q0.0")]

    network, disconnected = build_network(cells)

    assert network == LadderSeries((
        instruction(LadderOperation.NORMALLY_OPEN_CONTACT, "NormalContact", "%I0.0", 0, 0),
        instruction(LadderOperation.COIL, "Coil", "%Q0.0", 0, 10),
    ))
    assert disconnected == []


def test_parallel_branches_are_ordered_top_to_bottom():
    cells = [
        cell("NormalContact", 1, 0, "Up, Left", Descriptor="%I0.1"),
        cell("NormalContact", 0, 0, "Down, Left, Right", Descriptor="%I0.0"),
        *wire(0, 1, 9), cell("Coil", 0, 10, "Left", Descriptor="%Q0.0"),
    ]

    network, _ = build_network(cells)

    (parallel, coil) = network.elements
    assert isinstance(parallel, LadderParallel)
    assert [instructions(branch)[0].operand for branch in parallel.branches] == ["%I0.0", "%I0.1"]
    assert isinstance(coil, LadderInstruction) and coil.operand == "%Q0.0"


def test_placeholder_cells_are_ignored():
    base = [cell("NormalContact", 0, 0, Descriptor="%I0.0"), *wire(0, 1, 9), cell("Coil", 0, 10, "Left", Descriptor="%Q0.0")]

    assert build_network([*base, cell("None", 1, 4, "None")]) == build_network(base)


def test_short_is_a_wire_negative_coil_is_negated_and_others_stay_unsupported():
    cells = [
        cell("Short", 0, 0),
        cell("Not", 0, 1),
        cell("Xor", 0, 2, Descriptor="%I0.3"),
        *wire(0, 3, 9),
        cell("NegativeCoil", 0, 10, "Left", Descriptor="%Q0.2"),
    ]

    network, _ = build_network(cells)

    assert network == LadderSeries((
        instruction(LadderOperation.UNSUPPORTED, "Not", None, 0, 1),
        instruction(LadderOperation.UNSUPPORTED, "Xor", "%I0.3", 0, 2),
        instruction(LadderOperation.NEGATED_COIL, "NegativeCoil", "%Q0.2", 0, 10),
    ))


def test_block_pins_use_fixed_rows_not_il_order():
    # Counter with only R (row 0) and CU (row 2) wired; D (row 1) drives a coil.
    cells = [
        cell("NormalContact", 0, 0, Descriptor="%I0.1"), cell("Line", 0, 1),
        cell("Counter", 0, 2, Descriptor="%C0"),
        cell("NormalContact", 2, 0, Descriptor="%I0.0"), cell("Line", 2, 1),
        *wire(1, 4, 9), cell("Coil", 1, 10, "Left", Descriptor="%Q0.0"),
    ]

    network, _ = build_network(cells)

    (parallel,) = network.elements
    assert isinstance(parallel, LadderParallel)
    assert [branch.elements for branch in parallel.branches] == [
        (instruction(LadderOperation.NORMALLY_OPEN_CONTACT, "NormalContact", "%I0.1", 0, 0),
         instruction(LadderOperation.FUNCTION_BLOCK_INPUT, "Counter", "%C0.R", 0, 2)),
        (LadderInstruction(LadderOperation.BLOCK_OUTPUT_REFERENCE, "Counter", "%C0.D",
                           position=LadderPosition(column=2, row=1)),
         instruction(LadderOperation.COIL, "Coil", "%Q0.0", 1, 10)),
        (instruction(LadderOperation.NORMALLY_OPEN_CONTACT, "NormalContact", "%I0.0", 2, 0),
         instruction(LadderOperation.FUNCTION_BLOCK_INPUT, "Counter", "%C0.CU", 0, 2)),
    ]


def test_element_reaching_no_output_is_reported_and_left_out():
    cells = [
        cell("NormalContact", 0, 0, Descriptor="%I0.0"), *wire(0, 1, 9), cell("Coil", 0, 10, "Left", Descriptor="%Q0.0"),
        # Wired from the rail but going nowhere.
        cell("NormalContact", 1, 0, Descriptor="%I0.5"),
    ]

    network, disconnected = build_network(cells)

    assert [element.operand for element in instructions(network)] == ["%I0.0", "%Q0.0"]
    assert disconnected == ["NormalContact"]


def test_unknown_element_type_gets_no_network():
    cells = [cell("Pid", 0, 0, Descriptor="%PID0"), *wire(0, 1, 9), cell("Coil", 0, 10, "Left", Descriptor="%Q0.0")]

    with pytest.raises(NetworkUnresolved) as error:
        build_network(cells)

    assert error.value.code == "ladder_unknown_element"
    assert "'Pid'" in str(error.value)


def test_no_reachable_output_gets_no_network():
    with pytest.raises(NetworkUnresolved) as error:
        build_network([cell("Coil", 0, 10, "Left", Descriptor="%Q0.0")])

    assert error.value.code == "ladder_no_output"


def test_bridge_wiring_is_not_guessed():
    # A Wheatstone bridge: A then B then C on row 0; G (row 1) bypasses B and
    # C from after A; E (row 2) bypasses A and B into the node after B. The
    # 2-wide Comparison boxes pass over node (1, 2) without touching it.
    cells = [
        cell("NormalContact", 0, 0, "Down, Left, Right", Descriptor="A"),
        cell("NormalContact", 0, 1, "Down, Left, Right", Descriptor="B"),
        cell("NormalContact", 0, 2, Descriptor="C"),
        *wire(0, 3, 9), cell("Coil", 0, 10, "Left", Descriptor="%Q0.0"),
        cell("Comparison", 1, 1, "Up, Left, Right", ComparisonExpression="G"),
        cell("Comparison", 2, 0, "Up, Left, Right", ComparisonExpression="E"),
    ]

    with pytest.raises(NetworkUnresolved) as error:
        build_network(cells)

    assert error.value.code == "ladder_not_series_parallel"


def test_operand_is_the_declared_symbol_with_the_address_kept():
    cells = [
        cell("NormalContact", 0, 0, Descriptor="%I0.0"), cell("Line", 0, 1),
        cell("Timer", 0, 2, Descriptor="%TM0"), *wire(0, 4, 9), cell("Coil", 0, 10, "Left", Descriptor="%Q0.0"),
    ]

    network, _ = build_network(cells, {"%I0.0": "START_PB", "%TM0": "DELAY"})

    (parallel,) = network.elements
    assert isinstance(parallel, LadderParallel)
    (contact, pin), (reference, coil) = (instructions(branch) for branch in parallel.branches)
    assert (contact.operand, contact.annotations) == ("START_PB", ("address=%I0.0",))
    assert (pin.operation, pin.operand, pin.annotations) == (
        LadderOperation.FUNCTION_BLOCK_INPUT, "DELAY.IN", ("address=%TM0",))
    assert (reference.operand, reference.annotations) == ("DELAY.Q", ("address=%TM0",))
    # No declared symbol: the address is the operand.
    assert (coil.operand, coil.annotations) == ("%Q0.0", ())


def test_timer_output_read_as_a_contact_uses_the_timer_symbol():
    cells = [cell("NegatedContact", 0, 0, Descriptor="%TM2.Q"), *wire(0, 1, 9),
             cell("Coil", 0, 10, "Left", Descriptor="%Q0.0")]

    network, _ = build_network(cells, {"%TM2": "DELAY"})

    contact = instructions(network)[0]
    assert (contact.operand, contact.annotations) == ("DELAY.Q", ("address=%TM2.Q",))
