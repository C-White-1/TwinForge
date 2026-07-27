"""Recover parameter-to-setpoint bindings from Structured Text branches."""

from __future__ import annotations

import re
from dataclasses import dataclass, fields, is_dataclass

from twinforge.model import AddOnInstruction
from twinforge.structured_text import (
    AssignmentStatement,
    IfBranch,
    IfStatement,
    LiteralExpression,
    parse_structured_text,
)


@dataclass(frozen=True)
class ParameterSetpointBinding:
    """One parameter number explicitly paired with an internal setpoint."""

    number: int
    member_name: str
    routine_name: str
    evidence: str


@dataclass(frozen=True)
class ParameterLiteralWriteBinding:
    """One parameter number paired with an automatic literal write."""

    number: int
    lexical_value: str
    routine_name: str
    evidence: str


def extract_parameter_setpoint_bindings(
    implementation: AddOnInstruction,
) -> dict[int, ParameterSetpointBinding]:
    """Return only parameter bindings that are unique across the AOI."""

    candidates: list[ParameterSetpointBinding] = []
    for routine in implementation.iter_routines():
        source = routine.structured_text
        if not source:
            continue
        document = parse_structured_text(source)
        for statement in _walk(document.statements):
            if not isinstance(statement, IfStatement):
                continue
            for branch in statement.branches:
                binding = _branch_binding(
                    branch,
                    source,
                    routine.name,
                )
                if binding is not None:
                    candidates.append(binding)
    result: dict[int, ParameterSetpointBinding] = {}
    for number in sorted({item.number for item in candidates}):
        matches = [item for item in candidates if item.number == number]
        member_names = {item.member_name for item in matches}
        if len(member_names) == 1:
            result[number] = matches[0]
    return result


def extract_parameter_literal_write_bindings(
    implementation: AddOnInstruction,
) -> dict[int, ParameterLiteralWriteBinding]:
    """Return literal write behaviors unique across the AOI."""

    candidates: list[ParameterLiteralWriteBinding] = []
    for routine in implementation.iter_routines():
        source = routine.structured_text
        if not source:
            continue
        document = parse_structured_text(source)
        for statement in _walk(document.statements):
            if not isinstance(statement, IfStatement):
                continue
            for branch in statement.branches:
                binding = _branch_literal_binding(
                    branch,
                    source,
                    routine.name,
                )
                if binding is not None:
                    candidates.append(binding)
    result: dict[int, ParameterLiteralWriteBinding] = {}
    for number in sorted({item.number for item in candidates}):
        matches = [item for item in candidates if item.number == number]
        values = {item.lexical_value for item in matches}
        if len(values) == 1:
            result[number] = matches[0]
    return result


def _branch_binding(
    branch: IfBranch,
    source: str,
    routine_name: str,
) -> ParameterSetpointBinding | None:
    numbers: set[int] = set()
    member_names: set[str] = set()
    for statement in _walk(branch.statements):
        if not isinstance(statement, AssignmentStatement):
            continue
        target = source[statement.target.span.start : statement.target.span.end]
        if target.casefold() == "writeinstance":
            number = _integer_literal(statement.value)
            if number is not None:
                numbers.add(number)
        if target.casefold() == "writeparam":
            value = source[
                statement.value.span.start : statement.value.span.end
            ]
            member_names.update(
                re.findall(
                    r"\bLocal\.Params\.([A-Za-z_][A-Za-z0-9_]*)\.SP\b",
                    value,
                    re.IGNORECASE,
                )
            )
    if len(numbers) != 1 or len(member_names) != 1:
        return None
    number = next(iter(numbers))
    member_name = next(iter(member_names))
    return ParameterSetpointBinding(
        number=number,
        member_name=member_name,
        routine_name=routine_name,
        evidence=source[branch.span.start : branch.span.end].strip(),
    )


def _branch_literal_binding(
    branch: IfBranch,
    source: str,
    routine_name: str,
) -> ParameterLiteralWriteBinding | None:
    numbers: set[int] = set()
    values: set[str] = set()
    for statement in _walk(branch.statements):
        if not isinstance(statement, AssignmentStatement):
            continue
        target = source[statement.target.span.start : statement.target.span.end]
        if target.casefold() == "writeinstance":
            number = _integer_literal(statement.value)
            if number is not None:
                numbers.add(number)
        if target.casefold() == "writeparam" and isinstance(
            statement.value,
            LiteralExpression,
        ):
            values.add(statement.value.value)
    if len(numbers) != 1 or len(values) != 1:
        return None
    number = next(iter(numbers))
    return ParameterLiteralWriteBinding(
        number=number,
        lexical_value=next(iter(values)),
        routine_name=routine_name,
        evidence=source[branch.span.start : branch.span.end].strip(),
    )


def _integer_literal(expression: object) -> int | None:
    if not isinstance(expression, LiteralExpression):
        return None
    lexical = expression.value.replace("_", "")
    try:
        if "#" in lexical:
            radix, digits = lexical.split("#", 1)
            return int(digits, int(radix))
        return int(lexical, 0)
    except ValueError:
        return None


def _walk(value: object):
    if isinstance(value, tuple | list):
        for item in value:
            yield from _walk(item)
        return
    if not is_dataclass(value):
        return
    yield value
    for item in fields(value):
        yield from _walk(getattr(value, item.name))
