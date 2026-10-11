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
in-out parameters from `metadata["iec_function_block_in_outs"]` (an in-out
the instance does not bind is given a spare variable). Each block is fixed,
so the set can be packaged as a CODESYS library. The exporter emits a
definition only when an instance uses it.
"""

from __future__ import annotations

from dataclasses import dataclass
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


_DRUM_BODY = """\n(* TwinForge-generated: Machine Expert - Basic Drum (%DR) behaviour, from the
   Generic Functions Library Guide EIO0000003289.04, Drum (%DR), checked in
   the Machine Expert - Basic 3.0 simulator
   (docs/experiments/machine-expert-basic-drum-simulator.md).
   NSTEPS steps (1-8); P<k> is step k's pattern, bit n = control bit n.
   R holds the drum at step 0 and has priority, writing step 0's pattern
   every scan it is on; a rising edge on U advances one step, wrapping from
   the last step to step 0; F is on at the last step. Otherwise the control
   bits (B<n>, all 16, 0s included) are written only when the step changes,
   and are left as other logic wrote them in between. The step is kept
   across a controller stop/run; what a restart does to outputs follows
   the target runtime and is not modelled. *)
WRITE := FALSE;
IF R THEN
    S := 0;
    WRITE := TRUE;
ELSIF U AND NOT U_LAST THEN
    IF S >= NSTEPS - 1 THEN
        S := 0;
    ELSE
        S := S + 1;
    END_IF;
    WRITE := TRUE;
END_IF;
U_LAST := U;
IF WRITE THEN
    IF S = 0 THEN
        PATTERN := P0;
    ELSIF S = 1 THEN
        PATTERN := P1;
    ELSIF S = 2 THEN
        PATTERN := P2;
    ELSIF S = 3 THEN
        PATTERN := P3;
    ELSIF S = 4 THEN
        PATTERN := P4;
    ELSIF S = 5 THEN
        PATTERN := P5;
    ELSIF S = 6 THEN
        PATTERN := P6;
    ELSE
        PATTERN := P7;
    END_IF;
    B0 := (PATTERN AND WORD#16#0001) <> WORD#0;
    B1 := (PATTERN AND WORD#16#0002) <> WORD#0;
    B2 := (PATTERN AND WORD#16#0004) <> WORD#0;
    B3 := (PATTERN AND WORD#16#0008) <> WORD#0;
    B4 := (PATTERN AND WORD#16#0010) <> WORD#0;
    B5 := (PATTERN AND WORD#16#0020) <> WORD#0;
    B6 := (PATTERN AND WORD#16#0040) <> WORD#0;
    B7 := (PATTERN AND WORD#16#0080) <> WORD#0;
    B8 := (PATTERN AND WORD#16#0100) <> WORD#0;
    B9 := (PATTERN AND WORD#16#0200) <> WORD#0;
    B10 := (PATTERN AND WORD#16#0400) <> WORD#0;
    B11 := (PATTERN AND WORD#16#0800) <> WORD#0;
    B12 := (PATTERN AND WORD#16#1000) <> WORD#0;
    B13 := (PATTERN AND WORD#16#2000) <> WORD#0;
    B14 := (PATTERN AND WORD#16#4000) <> WORD#0;
    B15 := (PATTERN AND WORD#16#8000) <> WORD#0;
END_IF;
F := S = NSTEPS - 1;
"""

MACHINE_EXPERT_BASIC_DRUM = GeneratedFunctionBlock(
    name="TF_MEBasic_Drum",
    inputs=(("R", "BOOL"), ("U", "BOOL"), ("NSTEPS", "INT"),
            *((f"P{step}", "WORD") for step in range(8))),
    outputs=(("F", "BOOL"), ("S", "INT")),
    locals=(("U_LAST", "BOOL"), ("WRITE", "BOOL"), ("PATTERN", "WORD")),
    body=_DRUM_BODY,
    source="Generic Functions Library Guide EIO0000003289.04, Drum (%DR); "
           "Machine Expert - Basic 3.0 simulator checks",
    verified=True,
    # Written in place, and only when the step changes: a VAR_IN_OUT, not an
    # output pin, so other logic's writes stand in between (as on the M221).
    in_outs=tuple((f"B{bit}", "BOOL") for bit in range(16)),
)

LIBRARY["machine-expert-basic.drum"] = MACHINE_EXPERT_BASIC_DRUM


def generated_block_for(tag: Tag) -> GeneratedFunctionBlock | None:
    """The generated block whose behaviour `tag` names, if TwinForge has one."""
    return LIBRARY.get(tag.metadata.get("function_block_semantics") or "")


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
