"""TwinForge-generated IEC function blocks for vendor blocks with no IEC equal.

Some vendor library blocks behave differently from every IEC 61131-3
standard block (Machine Expert - Basic's `%C` counter wraps 0..9999 and sets
`D` on equality, which IEC `CTUD` does not). Approximating them with the
nearest IEC block would change program behaviour, so instead the exporter
writes a function block that reproduces the vendor's documented behaviour
and declares each instance of it.

A model tag selects a generated block through
`metadata["function_block_semantics"]` (an identifier naming whose
behaviour it is); its constant inputs come from
`metadata["iec_function_block_inputs"]` and the variables bound to its
in-out parameters from `metadata["iec_function_block_in_outs"]`. Most
behaviours are one fixed block (`LIBRARY`); a configured one, such as a
drum whose step pattern is part of its configuration, gets a block of its
own (`FACTORIES`). The exporter emits a definition only when an instance
uses it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import re
import xml.etree.ElementTree as ET

from twinforge.model import Tag

from .plcopen_xml import qualified_name

XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"


@dataclass(frozen=True)
class GeneratedFunctionBlock:
    name: str
    inputs: tuple[tuple[str, str], ...]
    outputs: tuple[tuple[str, str], ...]
    locals: tuple[tuple[str, str], ...]
    body: str
    # Where the behaviour comes from.
    source: str
    # Whether the body has been checked against the vendor's real behaviour.
    # An unverified block is exported only on request.
    verified: bool = False
    # VAR_IN_OUT parameters: variables the block writes in place.
    in_outs: tuple[tuple[str, str], ...] = ()

    @property
    def input_pins(self) -> frozenset[str]:
        return frozenset(name for name, _ in self.inputs)

    @property
    def output_pins(self) -> frozenset[str]:
        return frozenset(name for name, _ in self.outputs)

    @property
    def bool_outputs(self) -> frozenset[str]:
        return frozenset(name for name, data_type in self.outputs if data_type == "BOOL")


MACHINE_EXPERT_BASIC_COUNTER = GeneratedFunctionBlock(
    name="TF_MEBasic_Counter",
    inputs=(("R", "BOOL"), ("S", "BOOL"), ("CU", "BOOL"), ("CD", "BOOL"), ("PV", "INT")),
    outputs=(("E", "BOOL"), ("D", "BOOL"), ("F", "BOOL"), ("CV", "INT")),
    locals=(("CU_LAST", "BOOL"), ("CD_LAST", "BOOL")),
    body="""(* TwinForge-generated: Machine Expert - Basic Counter (%C) behaviour, from the
   Generic Functions Library Guide EIO0000003289.04, Counter (%C), checked in
   the Machine Expert - Basic 3.0 simulator
   (docs/experiments/machine-expert-basic-counter-simulator.md).
   R has priority and clears everything. S loads the preset and sets D.
   CU and CD count on rising edges; edges on both in the same scan cancel.
   Counting up wraps 9999 -> 0 and sets F; counting down wraps 0 -> 9999 and
   sets E; the next count in either direction clears the flag. D is set
   whenever the value equals the preset. *)
IF R THEN
    CV := 0;
    E := FALSE;
    D := FALSE;
    F := FALSE;
ELSIF S THEN
    CV := PV;
    D := TRUE;
ELSE
    IF (CU AND NOT CU_LAST) AND NOT (CD AND NOT CD_LAST) THEN
        IF CV >= 9999 THEN
            CV := 0;
            F := TRUE;
        ELSE
            CV := CV + 1;
            F := FALSE;
        END_IF;
        E := FALSE;
    ELSIF (CD AND NOT CD_LAST) AND NOT (CU AND NOT CU_LAST) THEN
        IF CV <= 0 THEN
            CV := 9999;
            E := TRUE;
        ELSE
            CV := CV - 1;
            E := FALSE;
        END_IF;
        F := FALSE;
    END_IF;
    D := CV = PV;
END_IF;
CU_LAST := CU;
CD_LAST := CD;
""",
    source="Generic Functions Library Guide EIO0000003289.04, Counter (%C); "
           "Machine Expert - Basic 3.0 simulator checks",
    verified=True,
)

# function_block_semantics identifier -> generated block.
LIBRARY: dict[str, GeneratedFunctionBlock] = {
    "machine-expert-basic.counter": MACHINE_EXPERT_BASIC_COUNTER,
}


def machine_expert_basic_drum(tag: Tag) -> GeneratedFunctionBlock | None:
    """The block for one configured Machine Expert - Basic drum (`%DRi`).

    Behaviour from the Generic Functions Library Guide EIO0000003289.04,
    Drum (%DR), settled in the Machine Expert - Basic 3.0 simulator
    (docs/experiments/machine-expert-basic-drum-simulator.md). Each assigned
    control bit is an in-out parameter `B<n>`, written only when the step
    changes; the step pattern is the drum's configuration, so it is part of
    the body and each configured drum has its own block.
    """
    steps = tag.metadata.get("drum_steps")
    patterns = tag.metadata.get("drum_patterns")
    if not isinstance(steps, int) or steps < 1 or not isinstance(patterns, dict):
        return None
    pins = sorted(patterns, key=lambda pin: int(pin[1:]))
    conditions = {pin: " OR ".join(f"(S = {step})" for step in patterns[pin]) or "FALSE" for pin in pins}
    writes = "\n".join(f"    {pin} := {conditions[pin]};" for pin in pins)
    body = f"""(* TwinForge-generated: Machine Expert - Basic Drum (%DR) {tag.name}, {steps} steps.
   Behaviour from the Generic Functions Library Guide EIO0000003289.04, Drum
   (%DR), checked in the Machine Expert - Basic 3.0 simulator
   (docs/experiments/machine-expert-basic-drum-simulator.md). R holds the
   drum at step 0 and has priority, writing step 0's pattern every scan it
   is on; a rising edge on U advances one step, wrapping from the last step
   to step 0; F is on at the last step. Otherwise the control bits (B<n>,
   every assigned bit, 0s included) are written only when the step
   changes, and are left as other logic wrote them in between. The step
   is kept across a controller stop/run; what a restart does to outputs
   follows the target runtime and is not modelled. *)
CHANGED := FALSE;
IF R THEN
    S := 0;
    CHANGED := TRUE;
ELSIF U AND NOT U_LAST THEN
    IF S >= {steps - 1} THEN
        S := 0;
    ELSE
        S := S + 1;
    END_IF;
    CHANGED := TRUE;
END_IF;
U_LAST := U;
IF CHANGED THEN
{writes}
END_IF;
F := S = {steps - 1};
"""
    instance = re.sub(r"\W", "_", tag.name).strip("_") or "Drum"
    return GeneratedFunctionBlock(
        name=f"TF_MEBasic_Drum_{instance}",
        inputs=(("R", "BOOL"), ("U", "BOOL")),
        outputs=(("F", "BOOL"), ("S", "INT")),
        locals=(("U_LAST", "BOOL"), ("CHANGED", "BOOL")),
        body=body,
        source="Generic Functions Library Guide EIO0000003289.04, Drum (%DR); "
               "Machine Expert - Basic 3.0 simulator checks",
        in_outs=tuple((pin, "BOOL") for pin in pins),
        verified=True,
    )


# function_block_semantics identifier -> block for one configured instance.
FACTORIES: dict[str, Callable[[Tag], GeneratedFunctionBlock | None]] = {
    "machine-expert-basic.drum": machine_expert_basic_drum,
}


def generated_block_for(tag: Tag) -> GeneratedFunctionBlock | None:
    """The generated block whose behaviour `tag` names, if TwinForge has one."""
    semantics = tag.metadata.get("function_block_semantics") or ""
    if semantics in LIBRARY:
        return LIBRARY[semantics]
    factory = FACTORIES.get(semantics)
    return factory(tag) if factory is not None else None


def emit_function_block_pou(parent: ET.Element, block: GeneratedFunctionBlock, namespace: str) -> ET.Element:
    """Append one functionBlock POU: interface and Structured Text body."""
    pou = ET.SubElement(parent, qualified_name(namespace, "pou"), {"name": block.name, "pouType": "functionBlock"})
    interface = ET.SubElement(pou, qualified_name(namespace, "interface"))
    for list_name, variables in (("inputVars", block.inputs), ("outputVars", block.outputs),
                                 ("inOutVars", block.in_outs), ("localVars", block.locals)):
        if not variables:
            continue
        variable_list = ET.SubElement(interface, qualified_name(namespace, list_name))
        for name, data_type in variables:
            variable = ET.SubElement(variable_list, qualified_name(namespace, "variable"), {"name": name})
            type_element = ET.SubElement(variable, qualified_name(namespace, "type"))
            ET.SubElement(type_element, qualified_name(namespace, data_type))
    body = ET.SubElement(pou, qualified_name(namespace, "body"))
    st = ET.SubElement(body, qualified_name(namespace, "ST"))
    # Provenance is in the body's leading comment; no <documentation>, so a
    # target can still append <addData>, which TC6 orders before it.
    ET.SubElement(st, qualified_name(XHTML_NAMESPACE, "xhtml")).text = block.body
    return pou
