"""The generated function blocks as a library package, with a test program.

`library_document` writes the blocks of `plcopen_library` as a PLCopen XML
project holding only POUs, ready to import into a CODESYS library project
(Project > Import PLCopenXML) and save or install as a library.
`library_document(..., include_tests=True)` adds `TF_MEBasic_Tests`, a
program that replays the recorded vendor checks (`plcopen_library_checks`)
once on its first cycle and counts failures, so a target can confirm it
compiles and runs the blocks as TwinForge's own tests do.

Results, readable in a watch list: `xDone` (the checks have run), `iChecks`,
`iFailures`, and `iFirstFailure` (the number of the first failed check,
listed in the body's leading comment; 0 when none failed).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import xml.etree.ElementTree as ET

from .plcopen_library import (
    MACHINE_EXPERT_BASIC_COUNTER, MACHINE_EXPERT_BASIC_DRUM, XHTML_NAMESPACE, GeneratedFunctionBlock,
    emit_function_block_pou,
)
from .plcopen_library_checks import CHECKS, Check, Expect, Scan, Value, Write
from .plcopen_types import PLCopenProfile
from .plcopen_xml import qualified_name as q

LIBRARY_NAME = "TwinForge_MEBasic"
LIBRARY_VERSION = "0.1.0"
LIBRARY_BLOCKS: tuple[GeneratedFunctionBlock, ...] = (MACHINE_EXPERT_BASIC_COUNTER, MACHINE_EXPERT_BASIC_DRUM)
TEST_PROGRAM = "TF_MEBasic_Tests"
RESULTS = (("xDone", "BOOL"), ("iChecks", "INT"), ("iFailures", "INT"), ("iFirstFailure", "INT"))


@dataclass(frozen=True)
class ChecksProgram:
    """A program replaying checks: its local variables (name, type, and the
    function block type for an instance) and its Structured Text body."""

    variables: tuple[tuple[str, str, bool], ...]
    body: str
    labels: tuple[str, ...]


def checks_program(checks: Sequence[Check] = CHECKS) -> ChecksProgram:
    """Structured Text replaying `checks`, one block instance per check."""
    variables: list[tuple[str, str, bool]] = []
    statements: list[str] = []
    labels: list[str] = []
    for check in checks:
        block = check.block
        types = dict((*block.inputs, *block.outputs, *block.in_outs))
        variables.append((check.name, block.name, True))
        bound = {pin: f"{check.name}_{pin}" for pin, _ in block.in_outs}
        variables.extend((name, "BOOL", False) for name in bound.values())
        current: dict[str, Value] = dict(check.constants)
        statements.append(f"    (* {check.name} *)")
        for step in check.steps:
            if isinstance(step, Scan):
                current.update(step.inputs)
                arguments = [f"{pin} := {_literal(step.inputs.get(pin, False), 'BOOL')}"
                             for pin, data_type in block.inputs if data_type == "BOOL"]
                arguments += [f"{pin} := {_literal(current[pin], data_type)}"
                              for pin, data_type in block.inputs if data_type != "BOOL"]
                arguments += [f"{pin} := {name}" for pin, name in bound.items()]
                statements.append(f"    {check.name}({', '.join(arguments)});")
            elif isinstance(step, Write):
                statements.append(f"    {bound[step.variable]} := {_literal(step.value, types[step.variable])};")
            else:
                labels.append(f"{check.name}: {step.label}")
                statements.extend(_expect(step, check.name, bound, types, len(labels)))
    legend = "\n".join(f"   {number}: {label}" for number, label in enumerate(labels, 1))
    body = (
        f"(* TwinForge-generated: replays the recorded Machine Expert - Basic simulator\n"
        f"   checks of {', '.join(dict.fromkeys(check.block.name for check in checks))} once, on the first cycle.\n"
        f"   iFailures counts failed checks; iFirstFailure is the number of the first:\n{legend} *)\n"
        "IF NOT xDone THEN\n" + "\n".join(statements) + "\n    xDone := TRUE;\nEND_IF;\n"
    )
    return ChecksProgram(tuple(variables) + tuple((name, data_type, False) for name, data_type in RESULTS),
                       body, tuple(labels))


def _expect(step: Expect, instance: str, bound: Mapping[str, str], types: Mapping[str, str],
            number: int) -> list[str]:
    terms = []
    for name, value in step.values.items():
        reference = bound.get(name, f"{instance}.{name}")
        if isinstance(value, bool):
            terms.append(reference if value else f"NOT {reference}")
        else:
            terms.append(f"({reference} = {_literal(value, types[name])})")
    return [
        "    iChecks := iChecks + 1;",
        f"    IF NOT ({' AND '.join(terms)}) THEN",
        "        iFailures := iFailures + 1;",
        "        IF iFirstFailure = 0 THEN",
        f"            iFirstFailure := {number};",
        "        END_IF;",
        "    END_IF;",
    ]


def _literal(value: Value, data_type: str) -> str:
    if data_type == "BOOL":
        return "TRUE" if value else "FALSE"
    if data_type == "WORD":
        return f"WORD#16#{int(value):04X}"
    return str(int(value))


def library_document(
    *,
    profile: PLCopenProfile | str = PLCopenProfile.CODESYS,
    creation_time: datetime,
    include_tests: bool = False,
    blocks: Sequence[GeneratedFunctionBlock] = LIBRARY_BLOCKS,
    checks: Sequence[Check] = CHECKS,
) -> str:
    """The blocks (and optionally the test program) as a PLCopen XML project."""
    ns = PLCopenProfile(profile).namespace
    ET.register_namespace("", ns)
    root = ET.Element(q(ns, "project"))
    ET.SubElement(root, q(ns, "fileHeader"), {
        "companyName": "TwinForge", "productName": "TwinForge", "productVersion": "0.1.0",
        "creationDateTime": creation_time.isoformat(),
    })
    header = ET.SubElement(root, q(ns, "contentHeader"), {
        "name": f"{LIBRARY_NAME} tests" if include_tests else LIBRARY_NAME, "version": LIBRARY_VERSION,
    })
    ET.SubElement(header, q(ns, "Comment")).text = (
        "TwinForge-generated IEC 61131-3 function blocks reproducing Machine Expert - Basic counter (%C) "
        "and drum (%DR) behaviour, checked in the Machine Expert - Basic 3.0 simulator. Provided as-is, "
        "without warranty: test on your own equipment."
    )
    coordinates = ET.SubElement(header, q(ns, "coordinateInfo"))
    for language in ("fbd", "ld", "sfc"):
        ET.SubElement(ET.SubElement(coordinates, q(ns, language)), q(ns, "scaling"), {"x": "1", "y": "1"})
    types = ET.SubElement(root, q(ns, "types"))
    ET.SubElement(types, q(ns, "dataTypes"))
    pous = ET.SubElement(types, q(ns, "pous"))
    for block in blocks:
        emit_function_block_pou(pous, block, ns)
    if include_tests:
        _emit_test_program(pous, checks_program(checks), ns)
    ET.SubElement(ET.SubElement(root, q(ns, "instances")), q(ns, "configurations"))
    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _emit_test_program(pous: ET.Element, program: ChecksProgram, ns: str) -> None:
    pou = ET.SubElement(pous, q(ns, "pou"), {"name": TEST_PROGRAM, "pouType": "program"})
    local_variables = ET.SubElement(ET.SubElement(pou, q(ns, "interface")), q(ns, "localVars"))
    for name, data_type, instance in program.variables:
        type_element = ET.SubElement(ET.SubElement(local_variables, q(ns, "variable"), {"name": name}), q(ns, "type"))
        if instance:
            ET.SubElement(type_element, q(ns, "derived"), {"name": data_type})
        else:
            ET.SubElement(type_element, q(ns, data_type))
    st = ET.SubElement(ET.SubElement(pou, q(ns, "body")), q(ns, "ST"))
    ET.SubElement(st, q(XHTML_NAMESPACE, "xhtml")).text = program.body
