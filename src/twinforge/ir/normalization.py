"""Explicit, auditable interface normalization for executable IR."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, replace
from enum import Enum

from .model import (
    IRAssignment,
    IRDiagnostic,
    IRDirection,
    IRExpression,
    IRIf,
    IRIndex,
    IRMember,
    IRReference,
    IRReusableUnit,
    IRStatement,
    IRUnitKind,
    IRRoutineRole,
    IRWhile,
)


class IRNormalizationPolicy(str, Enum):
    """Permitted transformations of a captured reusable interface."""

    PRESERVE = "preserve"
    PROMOTE_WRITTEN_INPUTS = "promote_written_inputs"


@dataclass(frozen=True)
class IRNormalizationResult:
    """Normalized unit and an audit trail of intentional changes."""

    unit: IRReusableUnit
    changes: tuple[IRDiagnostic, ...]


def normalize_reusable_unit(
    unit: IRReusableUnit,
    policy: IRNormalizationPolicy = IRNormalizationPolicy.PRESERVE,
) -> IRNormalizationResult:
    """Apply one named policy without mutating or losing the captured IR."""

    if policy is IRNormalizationPolicy.PRESERVE:
        return IRNormalizationResult(unit, ())

    written_inputs = _written_inputs(unit)
    if not written_inputs:
        return IRNormalizationResult(unit, ())

    changes: list[IRDiagnostic] = []
    parameters = []
    for parameter in unit.parameters:
        span = written_inputs.get(parameter.name.casefold())
        if parameter.direction is not IRDirection.INPUT or span is None:
            parameters.append(parameter)
            continue
        parameters.append(replace(parameter, direction=IRDirection.OUTPUT))
        changes.append(
            IRDiagnostic(
                "input_promoted_to_output",
                f"promoted written input parameter {parameter.name!r} "
                "to an IEC output",
                span,
            )
        )

    kind = unit.kind
    if kind is not IRUnitKind.FUNCTION_BLOCK:
        kind = IRUnitKind.FUNCTION_BLOCK
        first_span = next(iter(written_inputs.values()))
        changes.append(
            IRDiagnostic(
                "unit_promoted_to_function_block",
                "promoted function candidate to function block to preserve "
                "the normalized multi-direction interface",
                first_span,
            )
        )

    diagnostics = tuple(
        item
        for item in unit.diagnostics
        if item.code != "write_to_input_parameter"
    )
    normalized = replace(
        unit,
        kind=kind,
        parameters=tuple(parameters),
        diagnostics=diagnostics + tuple(changes),
    )
    return IRNormalizationResult(normalized, tuple(changes))


def _written_inputs(unit: IRReusableUnit):
    inputs = {
        parameter.name.casefold()
        for parameter in unit.parameters
        if parameter.direction is IRDirection.INPUT
    }
    written = {}
    for routine in unit.routines:
        if routine.role in {
            IRRoutineRole.PRESCAN,
            IRRoutineRole.POSTSCAN,
            IRRoutineRole.ENABLE_IN_FALSE,
            IRRoutineRole.UNKNOWN_LIFECYCLE,
        }:
            continue
        for statement in _walk_statements(routine.statements):
            if not isinstance(statement, IRAssignment):
                continue
            reference = _root_reference(statement.target)
            if reference is None:
                continue
            name = reference.name.casefold()
            if name in inputs and name not in written:
                written[name] = statement.span
    return written


def _walk_statements(
    statements: tuple[IRStatement, ...],
) -> Iterator[IRStatement]:
    for statement in statements:
        yield statement
        if isinstance(statement, IRIf):
            for branch in statement.branches:
                yield from _walk_statements(branch.statements)
            yield from _walk_statements(statement.else_statements)
        elif isinstance(statement, IRWhile):
            yield from _walk_statements(statement.statements)


def _root_reference(
    expression: IRExpression,
) -> IRReference | None:
    if isinstance(expression, IRReference):
        return expression
    if isinstance(expression, (IRMember, IRIndex)):
        return _root_reference(expression.target)
    return None
