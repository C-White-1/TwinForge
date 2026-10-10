"""TwinForge-generated function blocks in PLCopen export (Machine Expert - Basic counters).

The behaviour tests execute the generated Structured Text body and replay
the sequences recorded in the Machine Expert - Basic simulator
(docs/experiments/machine-expert-basic-counter-simulator.md); that check is
what marks the counter verified, so it exports by default.
"""
from dataclasses import replace
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from twinforge.exporters import plcopen_operands
from twinforge.exporters.plcopen import PLCopenExporter
from twinforge.exporters.plcopen_library import LIBRARY, MACHINE_EXPERT_BASIC_COUNTER
from twinforge.exporters.plcopen_validation import validate_plcopen_xml
from twinforge.model import (
    Controller, Identity, LadderInstruction, LadderOperation, LadderParallel, LadderRung, LadderSeries, Program,
    Routine, Tag,
)
from twinforge.parsers.machine_expert_basic import capture_file, parse_project
from twinforge.schema.machine_expert_basic import BASIC_MAPPING
from twinforge.structured_text.parser import parse_structured_text
from twinforge.structured_text.syntax import (
    AssignmentStatement, BinaryExpression, IfStatement, LiteralExpression, NameExpression, ParenthesizedExpression,
    UnaryExpression,
)

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "examples/machine_expert_basic"
XSD = ROOT / "reference/PLCopenXML/standard/tc6_xml_v201.xsd"
Op = LadderOperation


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def counter_tag(name: str = "%C0", preset: str = "3") -> Tag:
    return Tag(name=name, data_type="Counter", metadata={
        "function_block_semantics": "machine-expert-basic.counter", "iec_function_block_inputs": {"PV": preset}})


def counter_plc(*counters: Tag) -> Controller:
    """Each counter: Reset -> R, Pulse -> CU, D -> coil, plus a contact on D."""
    plc = Controller(name="PLC", identity=Identity())
    rungs = []
    for index, counter in enumerate(counters):
        plc.add_tag(counter)
        name = counter.name
        rungs.append(LadderRung(number=index, network=LadderSeries((LadderParallel((
            LadderSeries((LadderInstruction(Op.NORMALLY_OPEN_CONTACT, "NormalContact", "Reset"),
                          LadderInstruction(Op.FUNCTION_BLOCK_INPUT, "Counter", f"{name}.R"))),
            LadderSeries((LadderInstruction(Op.NORMALLY_OPEN_CONTACT, "NormalContact", "Pulse"),
                          LadderInstruction(Op.FUNCTION_BLOCK_INPUT, "Counter", f"{name}.CU"))),
            LadderSeries((LadderInstruction(Op.BLOCK_OUTPUT_REFERENCE, "Counter", f"{name}.D"),
                          LadderInstruction(Op.COIL, "Coil", f"Done{index}"))),
        )),))))
        rungs.append(LadderRung(number=100 + index, network=LadderSeries((
            LadderInstruction(Op.NORMALLY_OPEN_CONTACT, "NormalContact", f"{name}.D"),
            LadderInstruction(Op.COIL, "Coil", f"Seen{index}")))))
    program = Program("Main")
    routine = Routine(name="Main", language="LD")
    routine.ladder_rungs = rungs
    program.add_routine(routine)
    plc.add_program(program)
    return plc


def export(plc: Controller, profile: str = "standard_201", *, include_unverified_blocks: bool = False):
    return PLCopenExporter(profile, include_unverified_blocks=include_unverified_blocks).export(plc)


def pous(xml: str) -> list[ET.Element]:
    return [e for e in ET.fromstring(xml).iter() if _local(e.tag) == "pou"]


def test_parser_and_library_agree_on_the_semantics_identifier():
    assert BASIC_MAPPING.counters.semantics in LIBRARY


def test_counter_is_verified():
    assert MACHINE_EXPERT_BASIC_COUNTER.verified


@pytest.fixture
def unverified_counter(monkeypatch):
    semantics = BASIC_MAPPING.counters.semantics
    monkeypatch.setitem(plcopen_operands.GENERATED_LIBRARY, semantics,
                        replace(LIBRARY[semantics], verified=False))


@pytest.mark.usefixtures("unverified_counter")
def test_an_unverified_generated_block_is_withheld_by_default():
    result = export(counter_plc(counter_tag()))

    codes = [d.code for d in result.diagnostics]
    assert codes.count("generated_block_unverified") == 1
    assert codes.count("unsupported_network_rung") == 2
    assert [p.get("name") for p in pous(result.xml)] == ["Main"]


@pytest.mark.usefixtures("unverified_counter")
def test_an_unverified_generated_block_exports_when_opted_in():
    result = export(counter_plc(counter_tag()), include_unverified_blocks=True)

    assert "generated_block_unverified" not in [d.code for d in result.diagnostics]
    assert [p.get("name") for p in pous(result.xml)] == ["TF_MEBasic_Counter", "Main"]


def test_generated_block_is_written_once_before_the_programs_using_it():
    result = export(counter_plc(counter_tag("%C0", "3"), counter_tag("%C1", "7")))

    assert [(p.get("name"), p.get("pouType")) for p in pous(result.xml)] == [
        ("TF_MEBasic_Counter", "functionBlock"), ("Main", "program")]
    (definition, _) = pous(result.xml)
    declared = {v.get("name"): _local(next(c for c in v if _local(c.tag) == "type")[0].tag)
                for v in definition.iter() if _local(v.tag) == "variable" and v.get("name")}
    assert declared == {**dict(MACHINE_EXPERT_BASIC_COUNTER.inputs), **dict(MACHINE_EXPERT_BASIC_COUNTER.outputs),
                        **dict(MACHINE_EXPERT_BASIC_COUNTER.locals)}
    body = next(e for e in definition.iter() if _local(e.tag) == "xhtml").text or ""
    assert body == MACHINE_EXPERT_BASIC_COUNTER.body
    assert not [d for d in result.diagnostics if d.code == "unsupported_network_rung"]


def test_instances_are_wired_with_their_preset_as_a_constant():
    result = export(counter_plc(counter_tag("%C0", "3")))
    elements = {e.get("localId"): e for e in ET.fromstring(result.xml).iter() if e.get("localId")}

    (block,) = [e for e in elements.values() if _local(e.tag) == "block"]
    assert (block.get("typeName"), block.get("instanceName")) == ("TF_MEBasic_Counter", "TF_C0")

    def feeds(pin: str) -> list[ET.Element]:
        variable = next(v for v in block.iter() if v.get("formalParameter") == pin)
        return [elements[c.get("refLocalId")] for c in variable.iter() if _local(c.tag) == "connection"]

    (preset,) = feeds("PV")
    assert next(c.text for c in preset if _local(c.tag) == "expression") == "3"
    assert [next(c.text for c in e if _local(c.tag) == "variable") for e in feeds("R")] == ["Reset"]
    assert [next(c.text for c in e if _local(c.tag) == "variable") for e in feeds("CU")] == ["Pulse"]
    assert feeds("S") == [] and feeds("CD") == []  # unwired pins stay unconnected
    coil = next(e for e in elements.values() if _local(e.tag) == "coil"
                and next(c.text for c in e if _local(c.tag) == "variable") == "Done0")
    assert [(c.get("refLocalId"), c.get("formalParameter")) for c in coil.iter() if _local(c.tag) == "connection"] \
        == [(block.get("localId"), "D")]
    # A contact on %C0.D reads the instance member.
    variables = [e.text for e in ET.fromstring(result.xml).iter() if _local(e.tag) == "variable" and e.text]
    assert "TF_C0.D" in variables


def test_instance_is_declared_as_the_generated_type_without_the_standard_library():
    for profile in ("standard_201", "codesys"):
        xml = export(counter_plc(counter_tag()), profile).xml
        declared = {v.get("name"): next(c for c in v if _local(c.tag) == "type")[0].get("name")
                    for v in ET.fromstring(xml).iter() if _local(v.tag) == "variable" and v.get("name") == "TF_C0"}
        assert declared == {"TF_C0": "TF_MEBasic_Counter"}
        assert '<Library Name="#Standard"' not in xml


def test_codesys_project_tree_lists_the_generated_block():
    xml = export(counter_plc(counter_tag()), "codesys").xml

    assert 'Object Name="TF_MEBasic_Counter"' in xml


@pytest.mark.skipif(not XSD.exists(), reason="TC6 XSD is local-only (reference/ is gitignored)")
@pytest.mark.parametrize("source", ["synthetic", "06_counter", "06b_counter", "13_counter_simulation"])
def test_generated_block_export_validates_against_tc6(source: str):
    plc = counter_plc(counter_tag()) if source == "synthetic" else \
        parse_project(capture_file(FIXTURES / f"{source}.smbp")).controller
    validate_plcopen_xml(export(plc).xml, XSD)


def test_fixture_counter_exports():
    result = export(parse_project(capture_file(FIXTURES / "06_counter.smbp")).controller)

    assert not [d for d in result.diagnostics if d.code == "unsupported_network_rung"]
    (block,) = [e for e in ET.fromstring(result.xml).iter() if _local(e.tag) == "block"]
    assert block.get("typeName") == "TF_MEBasic_Counter"


class CounterRun:
    """Executes the generated counter body one controller scan at a time."""

    BINARY = {
        "AND": lambda a, b: a and b, "OR": lambda a, b: a or b, "=": lambda a, b: a == b,
        ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, "+": lambda a, b: a + b, "-": lambda a, b: a - b,
    }

    def __init__(self, preset: int = 3):
        document = parse_structured_text(MACHINE_EXPERT_BASIC_COUNTER.body)
        assert not document.diagnostics
        self.statements = document.statements
        self.state: dict[str, bool | int] = {
            name: (0 if data_type == "INT" else False)
            for name, data_type in (*MACHINE_EXPERT_BASIC_COUNTER.inputs, *MACHINE_EXPERT_BASIC_COUNTER.outputs,
                                    *MACHINE_EXPERT_BASIC_COUNTER.locals)}
        self.state["PV"] = preset

    def scan(self, **inputs: bool) -> None:
        for pin in ("R", "S", "CU", "CD"):
            self.state[pin] = inputs.get(pin, False)
        self._run(self.statements)

    def pulse(self, *pins: str) -> None:
        """Pins on together for one scan, then off (an input forced to 1, then 0)."""
        self.scan(**dict.fromkeys(pins, True))
        self.scan()

    def outputs(self) -> tuple[bool | int, ...]:
        """(V, D, E, F), the columns recorded in the simulator."""
        return (self.state["CV"], self.state["D"], self.state["E"], self.state["F"])

    def _run(self, statements) -> None:
        for statement in statements:
            if isinstance(statement, AssignmentStatement):
                assert isinstance(statement.target, NameExpression)
                self.state[statement.target.name] = self._value(statement.value)
            elif isinstance(statement, IfStatement):
                branch = next((b for b in statement.branches if self._value(b.condition)), None)
                self._run(branch.statements if branch else statement.else_statements)
            else:
                raise AssertionError(f"unexpected statement {statement!r}")

    def _value(self, expression):
        if isinstance(expression, NameExpression):
            return self.state[expression.name]
        if isinstance(expression, LiteralExpression):
            value = expression.value.upper()
            return value == "TRUE" if value in ("TRUE", "FALSE") else int(value)
        if isinstance(expression, ParenthesizedExpression):
            return self._value(expression.expression)
        if isinstance(expression, UnaryExpression):
            assert expression.operator.upper() == "NOT"
            return not self._value(expression.operand)
        if isinstance(expression, BinaryExpression):
            return self.BINARY[expression.operator.upper()](self._value(expression.left), self._value(expression.right))
        raise AssertionError(f"unexpected expression {expression!r}")


# Steps from docs/experiments/machine-expert-basic-counter-simulator.md;
# expected values are (V, D, E, F) as recorded in the simulator.

def test_counts_and_done_follow_equality_with_the_preset():
    counter = CounterRun(preset=3)
    for _ in range(3):
        counter.pulse("CU")
    assert counter.outputs() == (3, True, False, False)    # A1
    counter.pulse("CU")
    assert counter.outputs() == (4, False, False, False)   # A2: D clears off the preset
    counter.pulse("CD")
    assert counter.outputs() == (3, True, False, False)    # A3: and sets again from above


def test_empty_flag_sets_on_the_down_wrap_only_and_clears_on_the_next_count():
    counter = CounterRun(preset=3)
    counter.pulse("CU")
    counter.pulse("CD")
    assert counter.outputs() == (0, False, False, False)   # B1: reaching 0 does not set E
    counter.pulse("CD")
    assert counter.outputs() == (9999, False, True, False)  # B2: the 0 -> 9999 wrap does
    counter.pulse("CD")
    assert counter.outputs() == (9998, False, False, False)  # B3: the next count down clears it


def test_full_flag_sets_on_the_up_wrap_and_counting_up_clears_empty():
    counter = CounterRun(preset=3)
    counter.pulse("CD")
    assert counter.outputs() == (9999, False, True, False)
    counter.pulse("CU")
    assert counter.outputs() == (0, False, False, True)    # C2: F sets, E clears
    counter.pulse("CU")
    assert counter.outputs() == (1, False, False, False)   # C3


def test_set_loads_the_preset_and_reset_has_priority():
    counter = CounterRun(preset=3)
    counter.pulse("R")
    counter.pulse("S")
    assert counter.outputs() == (3, True, False, False)    # C1 (on %C1)
    counter.pulse("R", "S")
    assert counter.outputs() == (0, False, False, False)   # E1 (on %C2)

    counter = CounterRun(preset=9999)
    counter.pulse("R")
    counter.pulse("S")
    assert counter.outputs()[0] == 9999                     # C1 with preset 9999


def test_count_up_and_down_in_the_same_scan_cancel():
    counter = CounterRun(preset=3)
    counter.pulse("CU", "CD")
    assert counter.outputs() == (0, False, False, False)   # D1
    counter.state["CV"] = 9999                              # G2: %C1.V written in the animation table
    counter.pulse("CU", "CD")
    assert counter.outputs() == (9999, False, False, False)


def test_counting_down_clears_full():
    counter = CounterRun(preset=3)
    counter.state["CV"] = 9999                              # G1: %C0.V written in the animation table
    counter.pulse("CU")
    assert counter.outputs() == (0, False, False, True)
    counter.pulse("CD")
    assert counter.outputs() == (9999, False, True, False)
