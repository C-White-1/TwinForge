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
    Routine, Tag,
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
    """Evaluate one rung's PLCopen elements; returns coil (and block IN) -> energised.

    A block's output pin is an input to the rung (`block:<instance>.<pin>`);
    what drives a block's IN pin is recorded like a coil.
    """
    by_id = {e.get("localId"): e for e in elements if e.get("localId")}
    memo: dict[tuple[str, str | None], bool] = {}

    def refs(element: ET.Element) -> list[tuple[str, str | None]]:
        return [(c.get("refLocalId") or "", c.get("formalParameter"))
                for c in element.iter() if _local(c.tag) == "connection"]

    def power(local_id: str, pin: str | None = None) -> bool:
        if (local_id, pin) in memo:
            return memo[(local_id, pin)]
        element = by_id[local_id]
        kind = _local(element.tag)
        if kind == "leftPowerRail":
            value = True
        elif kind == "block":
            value = env[f"block:{element.get('instanceName')}.{pin}"]
        else:
            incoming = any(power(ref, pin) for ref, pin in refs(element))
            variable = next(c.text for c in element if _local(c.tag) == "variable") or ""
            if kind == "contact":
                state = env[f"{element.get('edge', 'none')}:{variable}"]
                value = incoming and (not state if element.get("negated") == "true" else state)
            else:  # coil: passes power on unchanged
                value = incoming
        memo[(local_id, pin)] = value
        return value

    results = {}
    for element in elements:
        if _local(element.tag) == "coil":
            variable = next(c.text for c in element if _local(c.tag) == "variable")
            key = (variable, element.get("storage", "none"), element.get("negated", "false"))
            results[key] = results.get(key, False) or power(element.get("localId") or "")
        elif _local(element.tag) == "block":
            for variable in element.iter():
                if _local(variable.tag) == "variable" and variable.get("formalParameter") == "IN":
                    results[("PIN", element.get("instanceName"), "IN")] = any(
                        power(ref, pin) for ref, pin in refs(variable))
    return results


# --- the source network as power flow ---------------------------------------

_STORAGE = {Op.SET_COIL: "set", Op.RESET_COIL: "reset"}
_EDGE = {Op.POSITIVE_TRANSITION_CONTACT: "rising", Op.NEGATIVE_TRANSITION_CONTACT: "falling"}


def _network_outputs(network: LadderSeries, env: dict[str, bool], rename: dict[str, str]) -> dict[tuple, bool]:
    results: dict[tuple, bool] = {}

    def walk(s: LadderSeries, flow: bool) -> bool:
        for element in s.elements:
            if isinstance(element, LadderParallel):
                flow = any([walk(branch, flow) for branch in element.branches])
            elif element.operation in CONTACTS:
                operand = rename.get(element.operand or "", element.operand)
                state = env[f"{_EDGE.get(element.operation, 'none')}:{operand}"]
                flow = flow and (not state if element.operation is Op.NORMALLY_CLOSED_CONTACT else state)
            elif element.operation is Op.FUNCTION_BLOCK_INPUT:
                instance, _, pin = (element.operand or "").rpartition(".")
                results[("PIN", rename.get(instance, instance), pin)] = flow
            elif element.operation is Op.BLOCK_OUTPUT_REFERENCE:
                instance, _, pin = (element.operand or "").rpartition(".")
                flow = env[f"block:{rename.get(instance, instance)}.{pin}"]
            else:
                key = (rename.get(element.operand or "", element.operand), _STORAGE.get(element.operation, "none"),
                       "true" if element.operation is Op.NEGATED_COIL else "false")
                results[key] = results.get(key, False) or flow
        return flow

    walk(network, True)
    return results


def _atoms(network: LadderSeries, rename: dict[str, str]) -> list[str]:
    found: set[str] = set()

    def walk(s: LadderSeries) -> None:
        for element in s.elements:
            if isinstance(element, LadderParallel):
                for branch in element.branches:
                    walk(branch)
            elif element.operation in CONTACTS:
                found.add(f"{_EDGE.get(element.operation, 'none')}:{rename.get(element.operand or '', element.operand)}")
            elif element.operation is Op.BLOCK_OUTPUT_REFERENCE:
                instance, _, pin = (element.operand or "").rpartition(".")
                found.add(f"block:{rename.get(instance, instance)}.{pin}")

    walk(network)
    return sorted(found)


def assert_equivalent(network: LadderSeries, elements: list[ET.Element], rename: dict[str, str] | None = None) -> None:
    """`rename` maps a source operand to the IEC-safe surrogate the exporter declared for it."""
    rename = rename or {}
    atoms = _atoms(network, rename)
    for bits in itertools.product((False, True), repeat=len(atoms)):
        env = dict(zip(atoms, bits))
        assert _graph_outputs(elements, env) == _network_outputs(network, env, rename), env


def surrogates(result) -> dict[str, str]:
    """Source operand or tag name -> IEC-safe name, from the exporter's own diagnostics."""
    return {d.raw_value: d.object_name for d in result.diagnostics
            if d.code in ("raw_operand_rewritten", "tag_name_rewritten")}


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


@pytest.mark.parametrize("name", ["02_parallel", "03_nested", "04_two_outputs", "05_timer", "05b_timer", "08_edges",
                                  "12_edited"])
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
        assert_equivalent(network, elements, surrogates(result))


def test_counter_rung_is_kept_as_a_comment():
    # Schneider %C wraps at 9999 and sets D on equality; IEC CTUD does neither.
    result = export(parse_project(capture_file(FIXTURES / "06_counter.smbp")).controller)

    assert [d.code for d in result.diagnostics if d.code == "unsupported_network_rung"] == ["unsupported_network_rung"]
    assert "Counter(%C0.R)" in result.xml


@pytest.mark.skipif(not XSD.exists(), reason="TC6 XSD is local-only (reference/ is gitignored)")
@pytest.mark.parametrize("name", ["03_nested", "04_two_outputs", "05_timer", "05b_timer", "08_edges"])
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


# --- variable declarations for network operands -----------------------------

def _declared(xml: str) -> dict[str, str]:
    """Declared variable name -> its elementary type (`<type><BOOL/></type>`)."""
    declared: dict[str, str] = {}
    for variable in ET.fromstring(xml).iter():
        if _local(variable.tag) != "variable" or not variable.get("name"):
            continue
        type_element = next((child for child in variable if _local(child.tag) == "type"), None)
        if type_element is not None and len(type_element):
            declared[variable.get("name") or ""] = _local(type_element[0].tag)
    return declared


def _used(xml: str) -> list[str]:
    return [(e.text or "").strip() for e in ET.fromstring(xml).iter()
            if _local(e.tag) == "variable" and not e.get("name") and (e.text or "").strip()]


def test_raw_network_operands_get_one_bool_surrogate_each():
    network_a = series(i(Op.NORMALLY_OPEN_CONTACT, "%I0.1"), i(Op.COIL, "%Q0.0"))
    network_b = series(i(Op.NORMALLY_CLOSED_CONTACT, "%I0.1"), i(Op.COIL, "Named"))

    result = export(controller(network_a, network_b))

    assert surrogates(result) == {"%I0.1": "TF_I0_1", "%Q0.0": "TF_Q0_0"}  # %I0.1 reused, not duplicated
    assert _used(result.xml) == ["TF_I0_1", "TF_Q0_0", "TF_I0_1", "Named"]
    declared = _declared(result.xml)
    assert declared["TF_I0_1"] == "BOOL" and declared["TF_Q0_0"] == "BOOL"


def test_unsupported_network_operands_get_no_surrogate():
    result = export(controller(series(i(Op.UNSUPPORTED, "%TM0", "Timer"), i(Op.COIL, "%Q0.0"))))

    assert surrogates(result) == {}


@pytest.mark.parametrize("name", ["02_parallel", "08_edges", "09_symbols"])
@pytest.mark.parametrize("profile", ["standard_201", "codesys"])
def test_every_fixture_operand_is_declared_as_bool(name: str, profile: str):
    result = export(parse_project(capture_file(FIXTURES / f"{name}.smbp")).controller, profile)

    declared = _declared(result.xml)
    used = _used(result.xml)
    assert used and all(declared.get(operand) == "BOOL" for operand in used), (used, declared)


def test_rung_with_neither_text_nor_network_is_reported_accurately():
    # e.g. a Machine Expert - Basic rung written only in Instruction List.
    result = export(controller(None))  # type: ignore[arg-type]

    assert [d.code for d in result.diagnostics] == ["rung_without_exportable_logic"]
    assert [_local(e.tag) for e in ld_elements(result.xml)] == ["comment"]


def test_instruction_list_fixture_exports_as_ladder():
    plc = parse_project(capture_file(FIXTURES / "10_il_only.smbp")).controller
    (program,) = plc.programs.values()
    (routine,) = program.routines.values()

    result = export(plc)

    codes = [d.code for d in result.diagnostics]
    assert not {"rung_without_exportable_logic", "instruction_list_rung_not_converted", "unsupported_rll_rung"} & set(codes)
    network = routine.ladder_rungs[0].network
    assert network is not None
    assert_equivalent(network, ld_elements(result.xml), surrogates(result))


def test_unconverted_instruction_list_is_kept_readable_in_the_comment():
    plc = controller(None)  # type: ignore[arg-type]
    rung = plc.programs["Main"].routines["Main"].ladder_rungs[0]
    rung.instruction_list = ["LD %I0.0", "RISING0", "ST %Q0.0"]

    result = export(plc)

    assert [d.code for d in result.diagnostics] == ["instruction_list_rung_not_converted"]
    assert "Instruction List: LD %I0.0; RISING0; ST %Q0.0" in result.xml


# --- elementary type element names ------------------------------------------

@pytest.mark.parametrize(("data_type", "element"), [
    ("STRING", "string"), ("WSTRING", "wstring"), ("DATE_AND_TIME", "DT"), ("TIME_OF_DAY", "TOD"),
    ("BOOL", "BOOL"), ("TIME", "TIME"),
])
def test_type_elements_use_the_tc6_names(data_type: str, element: str):
    plc = controller(series(i(Op.NORMALLY_OPEN_CONTACT, "A"), i(Op.COIL, "Y")))
    plc.add_tag(Tag(name="Value", data_type=data_type))

    assert _declared(export(plc).xml)["Value"] == element


@pytest.mark.skipif(not XSD.exists(), reason="TC6 XSD is local-only (reference/ is gitignored)")
def test_string_and_date_time_variables_validate_against_tc6():
    plc = controller(series(i(Op.NORMALLY_OPEN_CONTACT, "A"), i(Op.COIL, "Y")))
    for name, data_type in (("Text", "STRING"), ("Wide", "WSTRING"), ("Stamp", "DATE_AND_TIME"), ("Clock", "TIME_OF_DAY")):
        plc.add_tag(Tag(name=name, data_type=data_type))

    validate_plcopen_xml(export(plc).xml, XSD)


# --- IEC timers -----------------------------------------------------------------

def _blocks(xml: str) -> list[ET.Element]:
    return [e for e in ET.fromstring(xml).iter() if _local(e.tag) == "block"]


def _declared_types(xml: str) -> dict[str, str]:
    """Variable name -> its type, elementary or derived (`<derived name=...>`)."""
    declared: dict[str, str] = {}
    for variable in ET.fromstring(xml).iter():
        if _local(variable.tag) != "variable" or not variable.get("name"):
            continue
        type_element = next((child for child in variable if _local(child.tag) == "type"), None)
        if type_element is not None and len(type_element):
            inner = type_element[0]
            declared[variable.get("name") or ""] = inner.get("name") or _local(inner.tag)
    return declared


@pytest.mark.parametrize(("name", "block_type"), [("05_timer", "TON"), ("05b_timer", "TOF")])
def test_timer_becomes_an_iec_block_wired_into_the_rung(name: str, block_type: str):
    result = export(parse_project(capture_file(FIXTURES / f"{name}.smbp")).controller)

    (block,) = _blocks(result.xml)
    assert (block.get("typeName"), block.get("instanceName")) == (block_type, "TF_TM0")
    elements = {e.get("localId"): e for e in ld_elements(result.xml)}
    preset_ref = next(c.get("refLocalId") for v in block.iter() if v.get("formalParameter") == "PT"
                      for c in v.iter() if _local(c.tag) == "connection")
    preset = elements[preset_ref]
    assert _local(preset.tag) == "inVariable"
    assert next(c.text for c in preset if _local(c.tag) == "expression") == "TIME#5000ms"
    # The coil reads the block's Q output directly.
    (coil,) = [e for e in elements.values() if _local(e.tag) == "coil"]
    assert [(c.get("refLocalId"), c.get("formalParameter")) for c in coil.iter() if _local(c.tag) == "connection"]         == [(block.get("localId"), "Q")]
    assert _declared_types(result.xml)["TF_TM0"] == block_type


def test_codesys_profile_declares_standard_library_timers():
    result = export(parse_project(capture_file(FIXTURES / "05_timer.smbp")).controller, "codesys")

    assert _declared_types(result.xml)["TF_TM0"] == "Standard.TON"
    assert '<Library Name="#Standard" Namespace="Standard"' in result.xml
    # Only when something needs it.
    plain = export(parse_project(capture_file(FIXTURES / "02_parallel.smbp")).controller, "codesys")
    assert '<Library Name="#Standard"' not in plain.xml


def test_retentive_timer_rung_stays_a_comment():
    result = export(parse_project(capture_file(FIXTURES / "05c_timer.smbp")).controller)

    assert _blocks(result.xml) == []
    assert [d.code for d in result.diagnostics if d.code == "unsupported_network_rung"] == ["unsupported_network_rung"]


def test_timer_output_read_as_a_contact_reads_the_instance_member():
    plc = controller(series(i(Op.NORMALLY_CLOSED_CONTACT, "%TM2.Q"), i(Op.COIL, "Y")))
    timer = Tag(name="%TM2", data_type="TON", metadata={"iec_function_block_inputs": {"PT": "TIME#3000ms"}})
    plc.add_tag(timer)

    result = export(plc)

    assert _used(result.xml) == ["TF_TM2.Q", "Y"]
    assert _declared_types(result.xml)["TF_TM2"] == "TON"


def test_member_read_of_an_unconverted_object_is_not_given_a_surrogate():
    result = export(controller(series(i(Op.NORMALLY_OPEN_CONTACT, "%C0.D"), i(Op.COIL, "Y"))))

    assert surrogates(result) == {}
    assert [d.code for d in result.diagnostics] == ["unsupported_network_rung"]
