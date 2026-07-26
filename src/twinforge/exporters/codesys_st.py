"""CODESYS-specific rendering of executable IR as IEC Structured Text."""

from __future__ import annotations

from dataclasses import dataclass, replace

from twinforge.ir import (
    IRAssignment,
    IRBinary,
    IRDiagnostic,
    IRDirection,
    IRIf,
    IRIfBranch,
    IRLiteral,
    IRParameter,
    IRReference,
    IRReusableUnit,
    IRRoutine,
    IRStatement,
    IRVariable,
    IRWallClockRead,
    IRWhile,
)
from twinforge.structured_text import SourceSpan

from .iec_st import IECSTEmission, emit_iec_st_routine, emit_iec_st_unit


@dataclass(frozen=True)
class CodesysSTDialect:
    """Map neutral IEC requirements to supported CODESYS constructs."""

    def render_array_dimension(
        self,
        array: str,
        dimension: str,
    ) -> str:
        """Render zero-based SIZE semantics using one-based CODESYS bounds."""

        target_dimension = f"({dimension} + 1)"
        return (
            f"((UPPER_BOUND({array}, {target_dimension}) - "
            f"LOWER_BOUND({array}, {target_dimension})) + 1)"
        )

    def supports_generic_array_interface(
        self,
        direction: IRDirection,
    ) -> bool:
        """CODESYS supports variable arrays in ``VAR_IN_OUT``."""

        return direction is IRDirection.INOUT

    def render_wall_clock_read(
        self,
        destination: str,
        timestamp_unit: str,
    ) -> list[str] | None:
        """Read CODESYS milliseconds while preserving the neutral unit."""

        if timestamp_unit != "microseconds":
            return None
        return [
            "tfWallClockResult := "
            "SysTimeRtcHighResGet(tfWallClockMilliseconds);",
            "IF tfWallClockResult = 0 THEN",
            f"    {destination} := "
            "ULINT_TO_LINT(tfWallClockMilliseconds * ULINT#1000);",
            "END_IF;",
        ]


_CODESYS_DIALECT = CodesysSTDialect()


def emit_codesys_st_unit(unit: IRReusableUnit) -> IECSTEmission:
    """Emit a reusable unit with known CODESYS requirements resolved."""

    return emit_iec_st_unit(adapt_codesys_runtime(unit), _CODESYS_DIALECT)


def emit_codesys_st_routine(routine: IRRoutine) -> IECSTEmission:
    """Emit one routine with known CODESYS requirements resolved."""

    return emit_iec_st_routine(routine, _CODESYS_DIALECT)


def adapt_codesys_runtime(unit: IRReusableUnit) -> IRReusableUnit:
    """Add target-only state required by mapped CODESYS runtime services."""

    if any(
        item.code == "codesys_wall_clock_adapter_applied"
        for item in unit.diagnostics
    ):
        return unit
    if not any(
        _has_wall_clock_read(routine.statements)
        for routine in unit.routines
    ):
        return unit
    names = {item.name.casefold() for item in unit.variables}
    additions = (
        IRVariable("tfWallClockMilliseconds", "SysTime"),
        IRVariable("tfWallClockResult", "SysTypes.RTS_IEC_RESULT"),
    )
    failure = _clock_failure_assignments(unit.parameters)
    return replace(
        unit,
        variables=(
            *unit.variables,
            *(item for item in additions if item.name.casefold() not in names),
        ),
        routines=tuple(
            replace(
                routine,
                statements=_guard_clock_reads(routine.statements, failure),
            )
            for routine in unit.routines
        ),
        diagnostics=(
            *unit.diagnostics,
            IRDiagnostic(
                "codesys_wall_clock_adapter_applied",
                "mapped wall-clock reads to SysTimeRtcHighResGet, converted "
                "milliseconds to source microseconds, and guarded subsequent "
                "logic against a failed read",
                SourceSpan(0, 0),
            ),
        ),
    )


def _has_wall_clock_read(statements: tuple[IRStatement, ...]) -> bool:
    for statement in statements:
        if isinstance(statement, IRWallClockRead):
            return True
        if isinstance(statement, IRIf):
            if any(
                _has_wall_clock_read(branch.statements)
                for branch in statement.branches
            ) or _has_wall_clock_read(statement.else_statements):
                return True
        elif isinstance(statement, IRWhile) and _has_wall_clock_read(
            statement.statements
        ):
            return True
    return False


def _guard_clock_reads(
    statements: tuple[IRStatement, ...],
    failure: tuple[IRStatement, ...],
) -> tuple[IRStatement, ...]:
    """Guard statements following a clock read with its target status."""

    transformed: list[IRStatement] = []
    for index, statement in enumerate(statements):
        if isinstance(statement, IRWallClockRead):
            remaining = _guard_clock_reads(
                statements[index + 1 :],
                failure,
            )
            transformed.append(statement)
            transformed.append(
                IRIf(
                    span=statement.span,
                    branches=(
                        IRIfBranch(
                            span=statement.span,
                            condition=IRBinary(
                                span=statement.span,
                                data_type="BOOL",
                                left=IRReference(
                                    span=statement.span,
                                    data_type="SysTypes.RTS_IEC_RESULT",
                                    name="tfWallClockResult",
                                ),
                                operator="=",
                                right=IRLiteral(
                                    span=statement.span,
                                    data_type="DINT",
                                    lexical_value="0",
                                ),
                            ),
                            statements=remaining,
                        ),
                    ),
                    else_statements=failure,
                )
            )
            return tuple(transformed)
        if isinstance(statement, IRIf):
            statement = replace(
                statement,
                branches=tuple(
                    replace(
                        branch,
                        statements=_guard_clock_reads(
                            branch.statements,
                            failure,
                        ),
                    )
                    for branch in statement.branches
                ),
                else_statements=_guard_clock_reads(
                    statement.else_statements,
                    failure,
                ),
            )
        elif isinstance(statement, IRWhile):
            statement = replace(
                statement,
                statements=_guard_clock_reads(statement.statements, failure),
            )
        transformed.append(statement)
    return tuple(transformed)


def _clock_failure_assignments(
    parameters: tuple[IRParameter, ...],
) -> tuple[IRStatement, ...]:
    span = SourceSpan(0, 0)
    return tuple(
        IRAssignment(
            span=span,
            target=IRReference(
                span=span,
                data_type="BOOL",
                name=parameter.name,
            ),
            value=IRLiteral(
                span=span,
                data_type="BOOL",
                lexical_value="FALSE",
            ),
        )
        for parameter in parameters
        if (
            parameter.direction is IRDirection.OUTPUT
            and parameter.data_type == "BOOL"
            and not parameter.system_defined
        )
    )
