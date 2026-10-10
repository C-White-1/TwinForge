"""PLCopen export of COMPARISON / ASSIGNMENT network instructions.

Expressions are decomposed into single IEC standard functions chained by
EN/ENO. These tests execute the emitted graph (functions, temporaries,
contacts) against a variable store and require the same final values and
coil states as evaluating the network's expression trees directly, over
random inputs, so a wrong decomposition or execution order cannot pass on
structure alone.
"""
from pathlib import Path
import random
import xml.etree.ElementTree as ET

import pytest

from twinforge.exporters.plcopen import PLCopenExporter
from twinforge.exporters.plcopen_validation import validate_plcopen_xml
from twinforge.model import (
    Controller, Expression, Identity, LadderInstruction, LadderOperation, LadderParallel, LadderRung, LadderSeries,
    Program, Routine,
)
from twinforge.parsers.machine_expert_basic import capture_file, parse_project
from twinforge.parsers.machine_expert_basic.expression import expression_instruction

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "examples/machine_expert_basic"
XSD = ROOT / "reference/PLCopenXML/standard/tc6_xml_v201.xsd"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _divide(a, b):
    if isinstance(a, float) or isinstance(b, float):
        return a / b
    quotient = abs(a) // abs(b)  # IEC integer division truncates toward zero
    return quotient if (a >= 0) == (b >= 0) else -quotient


# IEC bit strings, as (width, unsigned bits); integer <-> bit string
# conversions copy the bits (two's complement).
def _to_bits(width: int):
    return lambda a: (width, a & ((1 << width) - 1))


def _from_bits(value) -> int:
    width, bits = value
    return bits - (1 << width) if bits >> (width - 1) else bits


def _rotate(value, n: int, left: bool):
    width, bits = value
    n = n if left else width - n
    return (width, ((bits << n) | (bits >> (width - n))) & ((1 << width) - 1))


_FUNCTIONS = {
    "ADD": lambda a, b: a + b, "SUB": lambda a, b: a - b, "MUL": lambda a, b: a * b, "DIV": _divide,
    "EQ": lambda a, b: a == b, "NE": lambda a, b: a != b, "LT": lambda a, b: a < b, "GT": lambda a, b: a > b,
    "LE": lambda a, b: a <= b, "GE": lambda a, b: a >= b,
    "INT_TO_WORD": _to_bits(16), "DINT_TO_DWORD": _to_bits(32), "WORD_TO_INT": _from_bits, "DWORD_TO_DINT": _from_bits,
    "SHL": lambda a, n: (a[0], (a[1] << n) & ((1 << a[0]) - 1)), "SHR": lambda a, n: (a[0], a[1] >> n),
    "ROL": lambda a, n: _rotate(a, n, True), "ROR": lambda a, n: _rotate(a, n, False),
}
_OPERATORS = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "=": "EQ", "<>": "NE", "<": "LT", ">": "GT",
              "<=": "LE", ">=": "GE"}


def _literal(text: str):
    return float(text) if "." in text else int(text)


# --- the emitted graph, executed ----------------------------------------------

def run_graph(elements: list[ET.Element], store: dict, contacts: dict[str, bool]) -> dict[str, bool]:
    """Execute one rung's LD elements, updating `store`; returns coil -> energised."""
    by_id = {e.get("localId"): e for e in elements if e.get("localId")}
    memo: dict[tuple, bool] = {}

    def refs(point: ET.Element) -> list[tuple[str, str | None]]:
        return [(c.get("refLocalId") or "", c.get("formalParameter")) for c in point.iter() if _local(c.tag) == "connection"]

    def value(local_id: str):
        element = by_id[local_id]
        text = next(c.text for c in element if _local(c.tag) == "expression") or ""
        return store[text] if text in store else _literal(text)

    def power(local_id: str, pin: str | None = None) -> bool:
        key = (local_id, pin)
        if key in memo:
            return memo[key]
        element = by_id[local_id]
        kind = _local(element.tag)
        if kind == "leftPowerRail":
            result = True
        elif kind == "block":  # an IEC function: runs when EN is true; ENO = EN
            variables = [v for v in element.iter() if _local(v.tag) == "variable"]
            enable = next(v for v in variables if v.get("formalParameter") == "EN")
            result = any(power(*ref) for ref in refs(enable))
            if result:
                inputs = [value(refs(v)[0][0]) for v in variables
                          if v.get("formalParameter") == "" and any(_local(c.tag) == "connectionPointIn" for c in v)]
                output = next(v for v in variables if v.get("formalParameter") == ""
                              and any(_local(c.tag) == "connectionPointOut" for c in v))
                destination = next(c.text for c in output.iter() if _local(c.tag) == "expression") or ""
                type_name = element.get("typeName") or ""
                store[destination] = inputs[0] if type_name == "MOVE" else _FUNCTIONS[type_name](*inputs)
        else:
            incoming = any(power(*ref) for ref in refs(element))
            variable = next(c.text for c in element if _local(c.tag) == "variable") or ""
            if kind == "contact":
                # Read only when powered: an unpowered function never wrote its result.
                state = incoming and (bool(store[variable]) if variable in store else contacts[variable])
                result = incoming and (not state if element.get("negated") == "true" else state)
            else:
                result = incoming
        memo[key] = result
        return result

    coils = {}
    for element in elements:
        if _local(element.tag) == "block":
            power(element.get("localId") or "", "ENO")  # assignments that end a branch
        elif _local(element.tag) == "coil":
            name = next(c.text for c in element if _local(c.tag) == "variable") or ""
            coils[name] = coils.get(name, False) or power(element.get("localId") or "")
    return coils


# --- the source network, evaluated --------------------------------------------

def _schneider_shift(name: str, value: int, n: int, width: int) -> int:
    """The guide's word/double-word shift, worked on the bit pattern as text."""
    bits = format(value & ((1 << width) - 1), f"0{width}b")
    shifted = {"SHL": bits[n:] + "0" * n, "SHR": "0" * n + bits[:width - n],
               "ROL": bits[n:] + bits[:n], "ROR": bits[width - n:] + bits[:width - n]}[name]
    result = int(shifted, 2)
    return result - (1 << width) if shifted[0] == "1" else result


def evaluate(node: Expression, store: dict, rename: dict[str, str]):
    if node.kind == "literal":
        return _literal(node.text)
    if node.kind == "variable":
        return store[rename.get(node.text, node.text)]
    if node.kind == "call":
        assert node.left is not None and node.right is not None and node.operator is not None
        width = {"INT": 16, "DINT": 32}[node.data_type]
        return _schneider_shift(node.operator, int(evaluate(node.left, store, rename)), int(node.right.text), width)
    assert node.left is not None and node.right is not None and node.operator is not None
    return _FUNCTIONS[_OPERATORS[node.operator]](evaluate(node.left, store, rename), evaluate(node.right, store, rename))


def run_network(network: LadderSeries, store: dict, contacts: dict[str, bool], rename: dict[str, str]) -> dict:
    coils: dict[str, bool] = {}

    def walk(series: LadderSeries, flow: bool) -> bool:
        for element in series.elements:
            if isinstance(element, LadderParallel):
                flow = any([walk(branch, flow) for branch in element.branches])
            elif element.operation is LadderOperation.COMPARISON:
                assert element.expression is not None
                flow = flow and bool(evaluate(element.expression, store, rename))
            elif element.operation is LadderOperation.ASSIGNMENT:
                expression = element.expression
                assert expression is not None and expression.left is not None and expression.right is not None
                if flow:
                    store[rename.get(expression.left.text, expression.left.text)] = evaluate(expression.right, store, rename)
            elif element.operation is LadderOperation.NORMALLY_OPEN_CONTACT:
                flow = flow and contacts[rename.get(element.operand or "", element.operand or "")]
            else:  # coil
                name = rename.get(element.operand or "", element.operand or "")
                coils[name] = coils.get(name, False) or flow
        return flow

    walk(network, True)
    return coils


def _variables(network: LadderSeries) -> dict[str, str]:
    """Source variable name -> type, over every expression in the network."""
    found: dict[str, str] = {}

    def walk(series: LadderSeries) -> None:
        for element in series.elements:
            if isinstance(element, LadderParallel):
                for branch in element.branches:
                    walk(branch)
            elif element.expression is not None:
                for node in element.expression.iter_nodes():
                    if node.kind == "variable":
                        found[node.text] = node.data_type
    walk(network)
    return found


def _random_value(data_type: str, rng: random.Random):
    if data_type == "REAL":
        return round(rng.uniform(-50, 50), 2)
    # Mostly small values; full-range ones exercise the sign bit of shifts.
    bound = 2 ** 15 if data_type == "INT" else 2 ** 31
    return rng.choice([rng.randint(-20, 20), 0, 1, 10, rng.randint(-bound, bound - 1)])


def assert_executes_equivalently(network: LadderSeries, result, contact_names: list[str], trials: int = 300):
    rename = {d.raw_value: d.object_name for d in result.diagnostics
              if d.code in ("raw_operand_rewritten", "tag_name_rewritten")}
    elements = list(next(e for e in ET.fromstring(result.xml).iter() if _local(e.tag) == "LD"))
    variables = _variables(network)
    rng = random.Random(7)
    checked = 0
    for _ in range(trials):
        start = {rename.get(name, name): _random_value(kind, rng) for name, kind in variables.items()}
        contacts = {rename.get(name, name): rng.random() < 0.5 for name in contact_names}
        expected_store, actual_store = dict(start), dict(start)
        try:
            expected = run_network(network, expected_store, contacts, rename)
        except ZeroDivisionError:
            continue  # the controller sets %S18 here; not modelled
        actual = run_graph(elements, actual_store, contacts)
        assert actual == expected, (start, contacts)
        assert {k: actual_store[k] for k in start} == {k: expected_store[k] for k in start}, (start, contacts)
        checked += 1
    assert checked > trials // 2


# --- helpers to build networks --------------------------------------------------

def plc_with(*elements) -> tuple[Controller, LadderSeries]:
    network = LadderSeries(tuple(elements))
    plc = Controller(name="PLC", identity=Identity())
    program = Program("Main")
    routine = Routine(name="Main", language="LD")
    routine.ladder_rungs = [LadderRung(number=0, network=network)]
    program.add_routine(routine)
    plc.add_program(program)
    return plc, network


def contact(name: str) -> LadderInstruction:
    return LadderInstruction(LadderOperation.NORMALLY_OPEN_CONTACT, "NormalContact", name)


def coil(name: str) -> LadderInstruction:
    return LadderInstruction(LadderOperation.COIL, "Coil", name)


@pytest.mark.parametrize("text", [
    "%MW1 := %MW1 + 1",
    "%MW1 := %MW2",  # a bare MOVE
    "%MW107 := (%MW1 + 1) * 2",
    "%MW0 := %MW1 / %MW2",  # integer division truncates toward zero
    "%MF1 := %MF3 * (%MF2 * 3.0 + %MF5) + -99.0",
    "%MD0 := %MD1 - %MD2 * 4",
])
def test_assignments_execute_like_the_expression(text: str):
    plc, network = plc_with(contact("Run"), expression_instruction(text, "Operation"))
    result = PLCopenExporter("standard_201").export(plc)

    assert not [d for d in result.diagnostics if d.code == "unsupported_network_rung"]
    assert_executes_equivalently(network, result, ["Run"])


@pytest.mark.parametrize("text", [
    "%MW10 := ROR(%KW9, 10)",  # as in the samples
    "%MW0 := SHL(%MW10, 5)",
    "%MW1 := SHR(%MW2, 3)",
    "%MW1 := ROL(%MW2, 16)",  # a full rotation
    "%MW1 := SHR(%MW2, 16)",  # everything shifted out
    "%MD0 := ROR(%MD1, 7)",
    "%MD0 := SHL(%MD1, 31)",
    "%MW0 := SHL(%MW1, 2) + %MW2",  # a shift nested in arithmetic
])
def test_shifts_execute_like_the_word_operation(text: str):
    plc, network = plc_with(contact("Run"), expression_instruction(text, "Operation"))
    result = PLCopenExporter("standard_201").export(plc)

    assert not [d for d in result.diagnostics if d.code == "unsupported_network_rung"]
    assert_executes_equivalently(network, result, ["Run"])


def test_shift_converts_through_the_bit_string_type():
    plc, _ = plc_with(contact("Run"), expression_instruction("%MD0 := ROR(%MD1, 7)", "Operation"))
    root = ET.fromstring(PLCopenExporter("standard_201").export(plc).xml)

    assert [b.get("typeName") for b in root.iter() if _local(b.tag) == "block"] == [
        "DINT_TO_DWORD", "ROR", "DWORD_TO_DINT"]
    declared = {v.get("name"): _local(next(c for c in v if _local(c.tag) == "type")[0].tag)
                for v in root.iter() if _local(v.tag) == "variable" and v.get("name", "").startswith("TF_Expr")}
    assert sorted(declared.values()) == ["DWORD", "DWORD"]


@pytest.mark.parametrize("text", ["%MW0 > 10", "%MW0 + %MW1 <= %MW2 * 2", "%MF0 <> 2.5", "%MW0 = 0"])
def test_comparisons_gate_the_rung_like_the_expression(text: str):
    plc, network = plc_with(contact("Run"), expression_instruction(text, "Comparison"), coil("Out"))
    result = PLCopenExporter("standard_201").export(plc)

    assert_executes_equivalently(network, result, ["Run"])


def test_comparison_feeding_an_assignment_in_one_rung():
    # Fixture 07's shape: [%MW0 > 10] then %MW1 := %MW1 + 1.
    plc, network = plc_with(expression_instruction("%MW0 > 10", "Comparison"),
                            expression_instruction("%MW1 := %MW1 + 1", "Operation"))
    result = PLCopenExporter("standard_201").export(plc)

    assert_executes_equivalently(network, result, [])


def test_fixture_07_executes_equivalently_and_validates():
    plc = parse_project(capture_file(FIXTURES / "07_compare_operate.smbp")).controller
    (program,) = plc.programs.values()
    (routine,) = program.routines.values()
    network = routine.ladder_rungs[0].network
    assert network is not None

    result = PLCopenExporter("standard_201").export(plc)

    assert not [d for d in result.diagnostics if d.code == "unsupported_network_rung"]
    assert_executes_equivalently(network, result, [])
    if XSD.exists():
        validate_plcopen_xml(result.xml, XSD)


def test_unnamed_operands_and_temporaries_are_declared_with_their_types():
    plc, _ = plc_with(contact("Run"), expression_instruction("%MF1 := (%MF2 + 1.0) * 2.0", "Operation"))
    result = PLCopenExporter("standard_201").export(plc)

    declared = {}
    for variable in ET.fromstring(result.xml).iter():
        if _local(variable.tag) == "variable" and variable.get("name"):
            type_element = next(c for c in variable if _local(c.tag) == "type")
            declared[variable.get("name")] = _local(type_element[0].tag)
    assert declared["TF_MF1"] == declared["TF_MF2"] == "REAL"
    temporaries = [name for name in declared if name.startswith("TF_Expr_")]
    assert len(temporaries) == 1 and declared[temporaries[0]] == "REAL"


def test_execution_is_chained_through_eno():
    plc, _ = plc_with(expression_instruction("%MW0 > 10", "Comparison"),
                      expression_instruction("%MW1 := %MW1 + 1", "Operation"))
    elements = list(next(e for e in ET.fromstring(PLCopenExporter("standard_201").export(plc).xml).iter()
                         if _local(e.tag) == "LD"))
    blocks = [e for e in elements if _local(e.tag) == "block"]
    (gate,) = [e for e in elements if _local(e.tag) == "contact"]
    assert [b.get("typeName") for b in blocks] == ["GT", "ADD"]
    gate_refs = [(c.get("refLocalId"), c.get("formalParameter")) for c in gate.iter() if _local(c.tag) == "connection"]
    assert gate_refs == [(blocks[0].get("localId"), "ENO")]  # the contact reads GT's result after GT runs
    enable = next(v for v in blocks[1].iter() if v.get("formalParameter") == "EN")
    assert [c.get("refLocalId") for c in enable.iter() if _local(c.tag) == "connection"] == [gate.get("localId")]


def test_untyped_expression_keeps_the_rung_as_a_comment():
    refused = expression_instruction("%TM0.P := %MW0", "Comparison")
    plc, _ = plc_with(contact("Run"), refused)

    result = PLCopenExporter("standard_201").export(plc)

    assert [d.code for d in result.diagnostics] == ["unsupported_network_rung"]
