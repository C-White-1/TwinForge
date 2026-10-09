"""PLCopen LD emission straight from neutral `LadderRung.network` trees.

The strongest check here is behavioural: the emitted connection graph is
evaluated as power flow and must agree with the source network for every
input combination, so a wiring mistake cannot pass on element counts alone.
"""
import itertools
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from twinforge.exporters.plcopen import PLCopenExporter
from twinforge.exporters.plcopen_validation import validate_plcopen_xml
from twinforge.model import (
    Controller, Identity, LadderInstruction, LadderOperation, LadderParallel, LadderRung, LadderSeries, Program,
    Routine,
)
from twinforge.parsers.machine_expert_basic import capture_file, parse_project

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "examples/machine_expert_basic"
# Local-only (reference/ is gitignored); validation runs where it exists.
XSD = ROOT / "reference/PLCopenXML/standard/tc6_xml_v201.xsd"

Op = LadderOperation
CONTACTS = {Op.NORMALLY_OPEN_CONTACT, Op.NORMALLY_CLOSED_CONTACT, Op.POSITIVE_TRANSITION_CONTACT,
            Op.NEGATIVE_TRANSITION_CONTACT}


def i(operation: LadderOperation, operand: str | None, mnemonic: str = "src") -> LadderInstruction:
    return LadderInstruction(operation=operation, source_mnemonic=mnemonic, operand=operand)


def series(*elements) -> LadderSeries:
    return LadderSeries(tuple(elements))


def parallel(*branches: LadderSeries) -> LadderParallel:
    return LadderParallel(tuple(branches))


def controller(*networks: LadderSeries, text: str | None = None) -> Controller:
    plc = Controller(name="PLC", identity=Identity())
    program = Program("Main")
    routine = Routine(name="Main", language="LD")
    routine.ladder_rungs = [LadderRung(number=index, network=network, text=text)
                            for index, network in enumerate(networks)]
    program.add_routine(routine)
    plc.add_program(program)
    return plc


def export(plc: Controller, profile: str = "standard_201"):
    return PLCopenExporter(profile).export(plc)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def ld_elements(xml: str) -> list[ET.Element]:
    root = ET.fromstring(xml)
    (ld,) = [element for element in root.iter() if _local(element.tag) == "LD"]
    return list(ld)


# --- the emitted PLCopen graph as power flow -------------------------------

def _graph_outputs(elements: list[ET.Element], env: dict[str, bool]) -> dict[tuple, bool]:
    """Evaluate one rung's PLCopen elements; returns coil -> energised."""
    by_id = {e.get("localId"): e for e in elements if e.get("localId")}
    memo: dict[str, bool] = {}

    def refs(element: ET.Element) -> list[str]:
        return [c.get("refLocalId") or "" for c in element.iter() if _local(c.tag) == "connection"]

    def power(local_id: str) -> bool:
        if local_id in memo:
            return memo[local_id]
        element = by_id[local_id]
        kind = _local(element.tag)
        if kind == "leftPowerRail":
            value = True
        else:
            incoming = any(power(ref) for ref in refs(element))
            variable = next(c.text for c in element if _local(c.tag) == "variable") or ""
            if kind == "contact":
                state = env[f"{element.get('edge', 'none')}:{variable}"]
                value = incoming and (not state if element.get("negated") == "true" else state)
            else:  # coil: passes power on unchanged
                value = incoming
        memo[local_id] = value
        return value

    results = {}
    for element in elements:
        if _local(element.tag) == "coil":
            variable = next(c.text for c in element if _local(c.tag) == "variable")
            key = (variable, element.get("storage", "none"), element.get("negated", "false"))
            results[key] = results.get(key, False) or power(element.get("localId") or "")
    return results


# --- the source network as power flow ---------------------------------------

_STORAGE = {Op.SET_COIL: "set", Op.RESET_COIL: "reset"}
_EDGE = {Op.POSITIVE_TRANSITION_CONTACT: "rising", Op.NEGATIVE_TRANSITION_CONTACT: "falling"}


def _network_outputs(network: LadderSeries, env: dict[str, bool]) -> dict[tuple, bool]:
    results: dict[tuple, bool] = {}

    def walk(s: LadderSeries, flow: bool) -> bool:
        for element in s.elements:
            if isinstance(element, LadderParallel):
                flow = any([walk(branch, flow) for branch in element.branches])
            elif element.operation in CONTACTS:
                state = env[f"{_EDGE.get(element.operation, 'none')}:{element.operand}"]
                flow = flow and (not state if element.operation is Op.NORMALLY_CLOSED_CONTACT else state)
            else:
                key = (element.operand, _STORAGE.get(element.operation, "none"),
                       "true" if element.operation is Op.NEGATED_COIL else "false")
                results[key] = results.get(key, False) or flow
        return flow

    walk(network, True)
    return results


def _atoms(network: LadderSeries) -> list[str]:
    found: set[str] = set()

    def walk(s: LadderSeries) -> None:
        for element in s.elements:
            if isinstance(element, LadderParallel):
                for branch in element.branches:
                    walk(branch)
            elif element.operation in CONTACTS:
                found.add(f"{_EDGE.get(element.operation, 'none')}:{element.operand}")

    walk(network)
    return sorted(found)


def assert_equivalent(network: LadderSeries, elements: list[ET.Element]) -> None:
    atoms = _atoms(network)
    for bits in itertools.product((False, True), repeat=len(atoms)):
        env = dict(zip(atoms, bits))
        assert _graph_outputs(elements, env) == _network_outputs(network, env), env


# --- tests --------------------------------------------------------------------

NESTED_FAN_OUT = series(
    i(Op.NORMALLY_OPEN_CONTACT, "A"),
    parallel(series(i(Op.NORMALLY_CLOSED_CONTACT, "B")),
             series(i(Op.POSITIVE_TRANSITION_CONTACT, "C"),
                    parallel(series(i(Op.NORMALLY_OPEN_CONTACT, "D")), series(i(Op.NEGATIVE_TRANSITION_CONTACT, "E"))))),
    parallel(series(i(Op.COIL, "Y1")), series(i(Op.NORMALLY_OPEN_CONTACT, "F"), i(Op.SET_COIL, "Y2")),
             series(i(Op.RESET_COIL, "Y3")), series(i(Op.NEGATED_COIL, "Y4"))),
)


def test_nested_branches_and_fan_out_are_equivalent_to_the_network():
    result = export(controller(NESTED_FAN_OUT))

    assert not [d for d in result.diagnostics if d.code == "unsupported_network_rung"]
    assert_equivalent(NESTED_FAN_OUT, ld_elements(result.xml))


def test_iec_operations_use_the_tc6_attributes():
    elements = ld_elements(export(controller(NESTED_FAN_OUT)).xml)

    contacts = {next(c.text for c in e if _local(c.tag) == "variable"): dict(e.attrib)
                for e in elements if _local(e.tag) == "contact"}
    coils = {next(c.text for c in e if _local(c.tag) == "variable"): dict(e.attrib)
             for e in elements if _local(e.tag) == "coil"}
    assert contacts["B"].get("negated") == "true"
    assert contacts["C"].get("edge") == "rising"
    assert contacts["E"].get("edge") == "falling"
    assert "edge" not in contacts["A"] and "negated" not in contacts["A"]
    assert coils["Y2"].get("storage") == "set"
    assert coils["Y3"].get("storage") == "reset"
    assert coils["Y4"].get("negated") == "true"
    assert set(coils["Y1"]) == {"localId"}


def test_wired_or_lists_every_branch_output():
    network = series(parallel(series(i(Op.NORMALLY_OPEN_CONTACT, "A")), series(i(Op.NORMALLY_OPEN_CONTACT, "B"))),
                     i(Op.COIL, "Y"))
    elements = ld_elements(export(controller(network)).xml)

    contact_ids = {e.get("localId") for e in elements if _local(e.tag) == "contact"}
    (coil,) = [e for e in elements if _local(e.tag) == "coil"]
    assert {c.get("refLocalId") for c in coil.iter() if _local(c.tag) == "connection"} == contact_ids


@pytest.mark.parametrize("instruction", [
    i(Op.UNSUPPORTED, "%TM0", "Timer"),
    i(Op.BLOCK_OUTPUT_REFERENCE, "%TM0.Q", "Timer"),
    i(Op.NORMALLY_OPEN_CONTACT, None, "contact"),
])
def test_rung_without_an_ld_encoding_is_kept_as_a_comment(instruction):
    network = series(instruction, i(Op.COIL, "Y"))

    result = export(controller(network))

    assert [d.code for d in result.diagnostics if d.code == "unsupported_network_rung"] == ["unsupported_network_rung"]
    kinds = [_local(e.tag) for e in ld_elements(result.xml)]
    assert kinds == ["comment"]
    assert "Unsupported ladder network:" in result.xml


def test_rll_text_still_takes_precedence_over_a_network():
    network = series(i(Op.NORMALLY_OPEN_CONTACT, "Network"), i(Op.COIL, "Y"))

    xml = export(controller(network, text="XIC(Text)OTE(Y);")).xml

    variables = [e.text for e in ET.fromstring(xml).iter() if _local(e.tag) == "variable" and e.text]
    assert "Text" in variables and "Network" not in variables


@pytest.mark.parametrize("name", ["02_parallel", "03_nested", "04_two_outputs", "08_edges", "12_edited"])
def test_machine_expert_basic_fixtures_export_equivalently(name: str):
    plc = parse_project(capture_file(FIXTURES / f"{name}.smbp")).controller
    (program,) = plc.programs.values()
    (routine,) = program.routines.values()

    result = export(plc)

    assert not [d for d in result.diagnostics if d.code == "unsupported_network_rung"]
    rungs = _split_rungs(ld_elements(result.xml))
    networks = [rung.network for rung in routine.ladder_rungs]
    assert len(rungs) == len(networks)
    for network, elements in zip(networks, rungs):
        assert network is not None
        assert_equivalent(network, elements)


def test_fixture_with_a_block_pin_keeps_that_rung_as_a_comment():
    result = export(parse_project(capture_file(FIXTURES / "05_timer.smbp")).controller)

    assert [d.code for d in result.diagnostics if d.code == "unsupported_network_rung"] == ["unsupported_network_rung"]
    assert "Timer(%TM0)" in result.xml


@pytest.mark.skipif(not XSD.exists(), reason="TC6 XSD is local-only (reference/ is gitignored)")
@pytest.mark.parametrize("name", ["03_nested", "04_two_outputs", "08_edges"])
def test_exported_networks_validate_against_tc6(name: str):
    validate_plcopen_xml(export(parse_project(capture_file(FIXTURES / f"{name}.smbp")).controller).xml, XSD)


@pytest.mark.skipif(not XSD.exists(), reason="TC6 XSD is local-only (reference/ is gitignored)")
def test_synthetic_iec_network_validates_against_tc6():
    validate_plcopen_xml(export(controller(NESTED_FAN_OUT)).xml, XSD)


def test_codesys_profile_emits_the_same_graph():
    elements = ld_elements(export(controller(NESTED_FAN_OUT), "codesys").xml)

    assert_equivalent(NESTED_FAN_OUT, elements)


def _split_rungs(elements: list[ET.Element]) -> list[list[ET.Element]]:
    """Group LD elements into rungs: each starts at a leftPowerRail."""
    rungs: list[list[ET.Element]] = []
    for element in elements:
        if _local(element.tag) == "leftPowerRail":
            rungs.append([])
        if rungs:
            rungs[-1].append(element)
    return rungs
