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
`metadata["iec_function_block_inputs"]`. The exporter emits a definition
only when an instance uses it.
"""

from __future__ import annotations

from dataclasses import dataclass
import xml.etree.ElementTree as ET

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


def emit_function_block_pou(parent: ET.Element, block: GeneratedFunctionBlock, namespace: str) -> ET.Element:
    """Append one functionBlock POU: interface and Structured Text body."""
    pou = ET.SubElement(parent, qualified_name(namespace, "pou"), {"name": block.name, "pouType": "functionBlock"})
    interface = ET.SubElement(pou, qualified_name(namespace, "interface"))
    for list_name, variables in (("inputVars", block.inputs), ("outputVars", block.outputs),
                                 ("localVars", block.locals)):
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
