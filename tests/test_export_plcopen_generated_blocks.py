"""TwinForge-generated function blocks in PLCopen export (Machine Expert - Basic counters).

The behaviour tests execute the generated Structured Text body and replay
the sequences recorded in the Machine Expert - Basic simulator
(docs/experiments/machine-expert-basic-counter-simulator.md); that check is
what marks the counter verified, so it exports by default.
"""
from dataclasses import replace
from typing import Any
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from twinforge.exporters.plcopen import PLCopenExporter
from twinforge.exporters.plcopen_library import (
    LIBRARY, MACHINE_EXPERT_BASIC_COUNTER, MACHINE_EXPERT_BASIC_DRUM, GeneratedFunctionBlock, array_bounds,
    generated_block_for,
)
from twinforge.exporters.plcopen_library_checks import CHECKS, DRUM_CONSTANTS, Check, Expect, Scan, Value, Write
from twinforge.exporters.plcopen_validation import validate_plcopen_xml
from twinforge.exporters.plcopen_library_package import LIBRARY_BLOCKS, TEST_PROGRAM, library_document, checks_program
from twinforge.model import (
    Controller, Identity, LadderInstruction, LadderOperation, LadderParallel, LadderRung, LadderSeries, Program,
    Routine, Tag,
)
from twinforge.parsers.machine_expert_basic import capture_file, parse_project
from twinforge.schema.machine_expert_basic import BASIC_MAPPING
from twinforge.structured_text.parser import parse_structured_text
from twinforge.structured_text.syntax import (
    AssignmentStatement, BinaryExpression, CallExpression, ExpressionStatement, IfStatement, IndexExpression,
    LiteralExpression, MemberExpression, NameExpression, ParenthesizedExpression, UnaryExpression,
)

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "examples/machine_expert_basic"
XSD = ROOT / "reference/PLCopenXML/standard/tc6_xml_v201.xsd"
Op = LadderOperation
FIXED_TIME = datetime(2026, 10, 11, tzinfo=timezone.utc)


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
    monkeypatch.setitem(LIBRARY, semantics, replace(LIBRARY[semantics], verified=False))


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
    st = next(e for e in definition.iter() if _local(e.tag) == "ST")
    body = next(e for e in st if _local(e.tag) == "xhtml").text or ""
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
    # The source's pin R drives the block's RESET (R is reserved in CODESYS).
    assert [next(c.text for c in e if _local(c.tag) == "variable") for e in feeds("RESET")] == ["Reset"]
    assert [next(c.text for c in e if _local(c.tag) == "variable") for e in feeds("CU")] == ["Pulse"]
    assert feeds("LOAD") == [] and feeds("CD") == []  # unwired pins stay unconnected
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


def initial_state(data_type: str):
    """A variable's value before anything is written: 0, FALSE, or an array of 0s."""
    bounds = array_bounds(data_type)
    if bounds is not None:
        return [0] * (bounds[1] - bounds[0] + 1)
    return False if data_type == "BOOL" else 0


def literal_value(text: str) -> bool | int:
    """An IEC literal: TRUE/FALSE, an integer, or a typed one such as WORD#16#0003."""
    value = text.upper().rsplit("#", 2)
    if value[0] in ("TRUE", "FALSE"):
        return value[0] == "TRUE"
    if len(value) == 3:  # TYPE#BASE#DIGITS
        return int(value[2], int(value[1]))
    if len(value) == 2:  # TYPE#DIGITS or BASE#DIGITS
        return int(value[1], int(value[0])) if value[0].isdigit() else int(value[1])
    return int(value[0])


class BlockRun:
    """Executes a generated block's body one controller scan at a time."""

    BINARY = {
        "AND": lambda a, b: a and b if isinstance(a, bool) else a & b, "OR": lambda a, b: a or b, "=": lambda a, b: a == b, "<>": lambda a, b: a != b,
        ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, "+": lambda a, b: a + b, "-": lambda a, b: a - b,
    }

    def __init__(self, block: GeneratedFunctionBlock, **constants):
        document = parse_structured_text(block.body)
        assert not document.diagnostics
        self.statements = document.statements
        self.inputs = [name for name, data_type in block.inputs if data_type == "BOOL"]
        self.state: dict = {name: initial_state(data_type)
                            for name, data_type in (*block.inputs, *block.outputs, *block.in_outs, *block.locals)}
        self.state.update({pin: list(value) if isinstance(value, tuple) else value for pin, value in constants.items()})

    def scan(self, **inputs: Value) -> None:
        """One call: BOOL inputs not given are FALSE, others keep their value."""
        for pin in self.inputs:
            self.state[pin] = inputs.get(pin, False)
        self.state.update({pin: value for pin, value in inputs.items() if pin not in self.inputs})
        self._run(self.statements)

    def pulse(self, *pins: str) -> None:
        """Pins on together for one scan, then off (an input forced to 1, then 0)."""
        self.scan(**dict.fromkeys(pins, True))
        self.scan()


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

    def _value(self, expression) -> Any:
        if isinstance(expression, NameExpression):
            return self.state[expression.name]
        if isinstance(expression, LiteralExpression):
            return literal_value(expression.value)
        if isinstance(expression, ParenthesizedExpression):
            return self._value(expression.expression)
        if isinstance(expression, UnaryExpression):
            assert expression.operator.upper() == "NOT"
            return not self._value(expression.operand)
        if isinstance(expression, BinaryExpression):
            return self.BINARY[expression.operator.upper()](self._value(expression.left), self._value(expression.right))
        if isinstance(expression, IndexExpression):
            (index,) = expression.indices
            return self._value(expression.target)[self._value(index)]
        raise AssertionError(f"unexpected expression {expression!r}")


def replay(check: Check) -> None:
    """Run a recorded check on the block's Structured Text."""
    run = BlockRun(check.block, **check.constants)
    for step in check.steps:
        if isinstance(step, Scan):
            run.scan(**step.inputs)
        elif isinstance(step, Write):
            run.state[step.variable] = step.value
        else:
            assert {name: run.state[name] for name in step.values} == dict(step.values), step.label


@pytest.mark.parametrize("check", CHECKS, ids=lambda check: check.name)
def test_block_reproduces_the_recorded_simulator_sequence(check: Check):
    replay(check)


# --- drums (%DR) ------------------------------------------------------------

class ProgramRun(BlockRun):
    """Executes a generated test program: its calls run the blocks' own bodies."""

    def __init__(self, body: str, variables, blocks: dict[str, GeneratedFunctionBlock]):
        document = parse_structured_text(body)
        assert not document.diagnostics
        self.statements = document.statements
        self.inputs = []
        self.instances = {v.name: BlockRun(blocks[v.data_type]) for v in variables if v.instance}
        self.in_outs = {v.name: {pin for pin, _ in blocks[v.data_type].in_outs} for v in variables if v.instance}
        self.state = {v.name: [literal_value(value) for value in v.initial] if v.initial else initial_state(v.data_type)
                      for v in variables if not v.instance}

    def _run(self, statements) -> None:
        for statement in statements:
            if isinstance(statement, ExpressionStatement):
                call = statement.expression
                assert isinstance(call, CallExpression) and isinstance(call.callee, NameExpression)
                instance = self.instances[call.callee.name]
                in_outs = {}
                for argument in call.arguments:
                    assert argument.name is not None
                    if argument.name in self.in_outs[call.callee.name]:
                        assert isinstance(argument.value, NameExpression)
                        in_outs[argument.name] = argument.value.name  # passed by reference
                        instance.state[argument.name] = self.state[argument.value.name]
                    else:
                        instance.state[argument.name] = self._value(argument.value)
                instance._run(instance.statements)
                for pin, variable in in_outs.items():
                    self.state[variable] = instance.state[pin]
            else:
                super()._run([statement])

    def _value(self, expression):
        if isinstance(expression, MemberExpression):
            assert isinstance(expression.target, NameExpression)
            return self.instances[expression.target.name].state[expression.member]
        return super()._value(expression)


def run_test_program(blocks: dict[str, GeneratedFunctionBlock] | None = None) -> dict:
    program = checks_program()
    run = ProgramRun(program.body, program.variables, blocks or {block.name: block for block in LIBRARY_BLOCKS})
    run._run(run.statements)
    return run.state


def test_generated_test_program_passes_on_the_blocks():
    results = run_test_program()

    assert results["xDone"]
    assert (results["iChecks"], results["iFailures"], results["iFirstFailure"]) == (len(checks_program().labels), 0, 0)
    assert results["iChecks"] == sum(isinstance(step, Expect) for check in CHECKS for step in check.steps)


def test_generated_test_program_reports_the_first_failure_of_a_broken_block():
    # The old counter body: counting up did not clear E.
    broken = replace(MACHINE_EXPERT_BASIC_COUNTER, body=MACHINE_EXPERT_BASIC_COUNTER.body.replace(
        "        END_IF;\n        E := FALSE;\n", "        END_IF;\n", 1))
    assert broken.body != MACHINE_EXPERT_BASIC_COUNTER.body
    results = run_test_program({broken.name: broken, MACHINE_EXPERT_BASIC_DRUM.name: MACHINE_EXPERT_BASIC_DRUM})

    assert results["iFailures"] > 0
    first_failure = checks_program().labels[results["iFirstFailure"] - 1]
    assert first_failure == "Counter_Full: C2 the 9999 -> 0 wrap sets F and clears E"


@pytest.mark.parametrize("include_tests", [False, True])
def test_library_document_holds_the_blocks_and_optionally_the_tests(include_tests: bool):
    xml = library_document(creation_time=FIXED_TIME, include_tests=include_tests)

    names = [(pou.get("name"), pou.get("pouType")) for pou in pous(xml)]
    assert names == [("TF_MEBasic_Counter", "functionBlock"), ("TF_MEBasic_Drum", "functionBlock"),
                     *([(TEST_PROGRAM, "program")] if include_tests else [])]
    header = next(e for e in ET.fromstring(xml).iter() if _local(e.tag) == "contentHeader")
    assert header.get("version") == "0.2.1"


@pytest.mark.skipif(not XSD.exists(), reason="TC6 XSD is local-only (reference/ is gitignored)")
def test_library_document_validates_against_tc6():
    validate_plcopen_xml(library_document(profile="standard_201", creation_time=FIXED_TIME, include_tests=True), XSD)


def drum_tag() -> Tag:
    return parse_project(capture_file(FIXTURES / "14_drum_simulation.smbp")).controller.tags["%DR0"]


def test_drum_configuration_is_parsed_from_the_fixture():
    tag = drum_tag()

    assert tag.data_type == "Drum"
    assert tag.metadata["drum_steps"] == 4
    assert tag.metadata["iec_function_block_in_outs"] == {"B0": "%Q0.0", "B1": "%Q0.1", "B2": "%Q0.2", "B3": "%Q0.3"}
    assert tag.metadata["drum_patterns"] == {"B0": [1], "B1": [1], "B2": [2], "B3": [3]}
    assert tag.metadata["iec_function_block_inputs"] == {"NSTEPS": "4"}
    assert tag.metadata["iec_function_block_tables"] == {"PATTERN": [
        "WORD#16#0000", "WORD#16#0003", "WORD#16#0004", "WORD#16#0008", *["WORD#16#0000"] * 4]}
    assert generated_block_for(tag) is MACHINE_EXPERT_BASIC_DRUM
    # The recorded drum checks run with exactly these constants and table.
    parsed: dict[str, Value] = {pin: literal_value(text)
                                for pin, text in tag.metadata["iec_function_block_inputs"].items()}
    parsed["PATTERN"] = tuple(literal_value(word) for word in tag.metadata["iec_function_block_tables"]["PATTERN"])
    assert parsed == dict(DRUM_CONSTANTS)


def test_drum_pattern_is_fed_from_a_declared_table():
    result = export(parse_project(capture_file(FIXTURES / "14_drum_simulation.smbp")).controller)
    root = ET.fromstring(result.xml)
    elements = {e.get("localId"): e for e in root.iter() if e.get("localId")}

    (block,) = [e for e in elements.values() if _local(e.tag) == "block" and e.get("typeName") == "TF_MEBasic_Drum"]
    pattern = next(v for v in block.iter() if v.get("formalParameter") == "PATTERN")
    (connection,) = [c for c in pattern.iter() if _local(c.tag) == "connection"]
    source = elements[connection.get("refLocalId")]
    assert next(c.text for c in source if _local(c.tag) == "expression") == "TF_DR0_Pattern"
    (table,) = [v for v in root.iter() if _local(v.tag) == "variable" and v.get("name") == "TF_DR0_Pattern"]
    assert [d.get("upper") for d in table.iter() if _local(d.tag) == "dimension"] == ["7"]
    assert [s.get("value") for s in table.iter() if _local(s.tag) == "simpleValue"] == [
        "WORD#16#0000", "WORD#16#0003", "WORD#16#0004", "WORD#16#0008", *["WORD#16#0000"] * 4]


def test_drum_is_verified_and_exports_by_default():
    result = export(parse_project(capture_file(FIXTURES / "14_drum_simulation.smbp")).controller)

    assert "generated_block_unverified" not in [d.code for d in result.diagnostics]
    assert not [d for d in result.diagnostics if d.code == "unsupported_network_rung"]
    assert [p.get("name") for p in pous(result.xml)][0] == "TF_MEBasic_Drum"


def test_drum_exports_with_its_outputs_bound_in_place():
    result = export(parse_project(capture_file(FIXTURES / "14_drum_simulation.smbp")).controller)
    root = ET.fromstring(result.xml)

    (definition,) = [p for p in pous(result.xml) if p.get("name") == "TF_MEBasic_Drum"]
    in_out_vars = [v.get("name") for section in definition.iter() if _local(section.tag) == "inOutVars"
                   for v in section if _local(v.tag) == "variable"]
    assert in_out_vars == [f"B{bit}" for bit in range(16)]
    elements = {e.get("localId"): e for e in root.iter() if e.get("localId")}
    (block,) = [e for e in elements.values() if _local(e.tag) == "block" and e.get("typeName") == "TF_MEBasic_Drum"]
    assert block.get("instanceName") == "TF_DR0"
    bound = {}
    for section in block:
        if _local(section.tag) != "inOutVariables":
            continue
        for variable in section:
            (connection,) = [c for c in variable.iter() if _local(c.tag) == "connection"]
            source = elements[connection.get("refLocalId")]
            bound[variable.get("formalParameter")] = next(c.text for c in source if _local(c.tag) == "expression")
    surrogates = {d.raw_value: d.object_name for d in result.diagnostics if d.code == "raw_operand_rewritten"}
    assert bound == {**{pin: surrogates[address] for pin, address in
                        {"B0": "%Q0.0", "B1": "%Q0.1", "B2": "%Q0.2", "B3": "%Q0.3"}.items()},
                     **{f"B{bit}": "TF_DR0_Unused" for bit in range(4, 16)}}  # unassigned bits share a spare


@pytest.mark.skipif(not XSD.exists(), reason="TC6 XSD is local-only (reference/ is gitignored)")
@pytest.mark.parametrize("profile", ["standard_201", "codesys"])
def test_drum_export_validates_against_tc6(profile: str):
    plc = parse_project(capture_file(FIXTURES / "14_drum_simulation.smbp")).controller
    xml = export(plc, profile).xml
    if profile == "standard_201":
        validate_plcopen_xml(xml, XSD)
    else:
        assert 'Object Name="TF_MEBasic_Drum"' in xml


# IEC 61131-3 keywords and Instruction List operators, plus CODESYS's own
# (S= and R= set/reset assignments make S and R reserved there; D, E, F
# were accepted by CODESYS): none may
# name a parameter or variable of a generated block.
RESERVED = frozenset("""
    ABS ACTION AND ANDN ANY ARRAY AT BOOL BY BYTE CAL CALC CALCN CASE CONFIGURATION CONSTANT DATE DINT DIV DO DT
    DWORD ELSE ELSIF END_ACTION END_CASE END_CONFIGURATION END_FOR END_FUNCTION END_FUNCTION_BLOCK END_IF
    END_PROGRAM END_REPEAT END_RESOURCE END_STEP END_STRUCT END_TRANSITION END_TYPE END_VAR END_WHILE EQ EXIT
    FALSE FOR FROM FUNCTION FUNCTION_BLOCK GE GT IF INITIAL_STEP INT JMP JMPC JMPCN LD LDN LE LINT LREAL LT LWORD
    MOD MUL NE NOT OF ON OR ORN PROGRAM R REAL REPEAT RESOURCE RET RETAIN RETC RETCN RETURN S SINT ST STEP STN
    STRING STRUCT SUB TASK THEN TIME TO TOD TRANSITION TRUE TYPE UDINT UINT ULINT UNTIL USINT VAR VAR_ACCESS
    VAR_CONFIG VAR_EXTERNAL VAR_GLOBAL VAR_IN_OUT VAR_INPUT VAR_OUTPUT VAR_TEMP WHILE WITH WORD XOR XORN
""".split())


@pytest.mark.parametrize("block", LIBRARY_BLOCKS, ids=lambda block: block.name)
def test_generated_block_names_avoid_reserved_words(block: GeneratedFunctionBlock):
    names = [name for name, _ in (*block.inputs, *block.outputs, *block.in_outs, *block.locals)]
    assert [name for name in names if name.upper() in RESERVED] == []


@pytest.mark.parametrize("block", LIBRARY_BLOCKS, ids=lambda block: block.name)
def test_every_parameter_is_documented_for_the_library_manager(block: GeneratedFunctionBlock):
    names = [name for name, _ in (*block.inputs, *block.outputs, *block.in_outs, *block.locals)]
    assert block.summary
    assert sorted(dict(block.descriptions)) == sorted(names)


def test_library_document_carries_the_documentation():
    root = ET.fromstring(library_document(creation_time=FIXED_TIME))

    for pou in [e for e in root.iter() if _local(e.tag) == "pou"]:
        assert _local(list(pou)[-1].tag) == "documentation"  # TC6: last in a POU
        documented = [v.get("name") for v in pou.iter() if _local(v.tag) == "variable"
                      and any(_local(c.tag) == "documentation" for c in v)]
        (block,) = [b for b in LIBRARY_BLOCKS if b.name == pou.get("name")]
        assert len(documented) == len(block.descriptions)


def _tree(xml: str) -> list[tuple]:
    return [(e.tag, sorted(e.attrib.items()), (e.text or "").strip()) for e in ET.fromstring(xml).iter()]


def test_xhtml_is_written_as_codesys_writes_it_without_changing_the_document():
    # CODESYS keeps a variable's documentation only in the form its own export
    # uses: <xhtml xmlns="http://www.w3.org/1999/xhtml">, not a root prefix.
    raw = library_document(creation_time=FIXED_TIME, include_tests=True)
    assert "html:" not in raw and 'xmlns:html=' not in raw
    assert raw.count('<xhtml xmlns="http://www.w3.org/1999/xhtml"') >= 3
    prefixed = raw.replace('<project xmlns="http://www.plcopen.org/xml/tc6_0200"',
                           '<project xmlns="http://www.plcopen.org/xml/tc6_0200" xmlns:h="http://www.w3.org/1999/xhtml"', 1)
    prefixed = prefixed.replace('<xhtml xmlns="http://www.w3.org/1999/xhtml"', "<h:xhtml").replace("</xhtml>", "</h:xhtml>")
    assert _tree(prefixed) == _tree(raw)  # the same document either way


def test_exports_write_xhtml_without_a_prefix():
    xml = export(parse_project(capture_file(FIXTURES / "14_drum_simulation.smbp")).controller, "codesys").xml
    assert "html:" not in xml


def test_library_readme_matches_the_blocks():
    from twinforge.exporters.plcopen_library_package import LIBRARY_VERSION

    readme = (ROOT / "docs/codesys-library/README.md").read_text(encoding="utf-8")
    assert f"version {LIBRARY_VERSION}," in readme and f"| {LIBRARY_VERSION} |" in readme
    for block in LIBRARY_BLOCKS:
        section = readme.split(f"## {block.name}", 1)[1].split("\n## ", 1)[0]
        for name, _ in (*block.inputs, *block.outputs):
            assert f"| `{name}` |" in section, (block.name, name)
        if block.in_outs:
            assert "| `B0`..`B15` |" in section
