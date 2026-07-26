"""Canonical target-neutral IEC Structured Text emission from executable IR."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from twinforge.ir import (
    IRArrayDimension,
    IRAssignment,
    IRBinary,
    IRCall,
    IRCallStatement,
    IRControllerObjectRead,
    IRControllerObjectWrite,
    IRDirection,
    IRExit,
    IRExpression,
    IRIf,
    IRIndex,
    IRLiteral,
    IRMember,
    IRParameter,
    IRReference,
    IRReusableUnit,
    IRRoutine,
    IRRoutineRole,
    IRStatement,
    IRUnary,
    IRUnsupportedExpression,
    IRUnsupportedStatement,
    IRWallClockRead,
    IRWhile,
)
from twinforge.structured_text import SourceSpan


class IECRequirement(str, Enum):
    """Neutral operation that a target adapter must implement."""

    ARRAY_DIMENSION = "array_dimension"
    DYNAMIC_BIT_ACCESS = "dynamic_bit_access"
    GENERIC_ARRAY_INTERFACE = "generic_array_interface"
    SOURCE_OPERATION_ADAPTER = "source_operation_adapter"
    WALL_CLOCK_READ = "wall_clock_read"
    CONTROLLER_OBJECT_ACCESS = "controller_object_access"


class IECSTDialect(Protocol):
    """Target capabilities used while rendering otherwise neutral IEC ST."""

    def render_array_dimension(
        self,
        array: str,
        dimension: str,
    ) -> str | None:
        """Render an array-length query, or return ``None`` if unsupported."""

    def supports_generic_array_interface(
        self,
        direction: IRDirection,
    ) -> bool:
        """Return whether ``ARRAY[*]`` is valid for this direction."""

        ...

    def render_wall_clock_read(
        self,
        destination: str,
        timestamp_unit: str,
    ) -> list[str] | None:
        """Render a wall-clock read, or return ``None`` if unsupported."""

        ...


@dataclass(frozen=True)
class IECSTDiagnostic:
    """IEC emission caveat linked to a source location."""

    code: str
    message: str
    span: SourceSpan


@dataclass(frozen=True)
class IECSTEmission:
    """Canonical text plus explicit completeness and target requirements."""

    text: str
    diagnostics: tuple[IECSTDiagnostic, ...]
    requirements: tuple[IECRequirement, ...]

    @property
    def complete(self) -> bool:
        """Return whether no unresolved or unsupported issue remains."""

        blocking = {
            "unsupported_expression",
            "unsupported_statement",
            "write_to_input_parameter",
            "unknown_data_type",
            "multiple_routines_require_lifecycle_mapping",
            "prescan_mapping_required",
            "postscan_mapping_required",
            "enable_in_false_mapping_required",
            "aoi_enable_interface_unavailable",
            "unknown_scan_mode_routine",
        }
        return not any(item.code in blocking for item in self.diagnostics)


def emit_iec_st_routine(
    routine: IRRoutine,
    dialect: IECSTDialect | None = None,
) -> IECSTEmission:
    """Emit the body of one neutral IR routine."""

    emitter = _IECEmitter(dialect)
    lines = emitter.statements(routine.statements, indent=0)
    diagnostics = [
        IECSTDiagnostic(item.code, item.message, item.span)
        for item in routine.diagnostics
    ]
    diagnostics.extend(emitter.diagnostics)
    return IECSTEmission(
        text="\n".join(lines) + ("\n" if lines else ""),
        diagnostics=tuple(diagnostics),
        requirements=_sorted_requirements(emitter.requirements),
    )


def emit_iec_st_unit(
    unit: IRReusableUnit,
    dialect: IECSTDialect | None = None,
) -> IECSTEmission:
    """Emit a conservative IEC function block preserving the IR interface."""

    emitter = _IECEmitter(dialect)
    lines = [f"FUNCTION_BLOCK {unit.name}"]
    lines.extend(emitter.interface(unit.parameters))
    if unit.variables:
        lines.append("VAR")
    for variable in unit.variables:
        lines.append(
            f"    {variable.name} : "
            f"{emitter.data_type(variable.data_type, variable.dimensions)};"
        )
    if unit.variables:
        lines.append("END_VAR")

    executable_routines = tuple(
        routine
        for routine in unit.routines
        if routine.role
        not in {
            IRRoutineRole.PRESCAN,
            IRRoutineRole.POSTSCAN,
            IRRoutineRole.ENABLE_IN_FALSE,
            IRRoutineRole.UNKNOWN_LIFECYCLE,
        }
    )
    for index, routine in enumerate(executable_routines):
        if len(executable_routines) > 1:
            lines.append(f"(* Routine: {routine.name} *)")
        lines.extend(emitter.statements(routine.statements, indent=0))
        if index < len(executable_routines) - 1:
            lines.append("")
    lines.append("END_FUNCTION_BLOCK")

    diagnostics = [
        IECSTDiagnostic(item.code, item.message, item.span)
        for item in unit.diagnostics
    ]
    if unit.kind.value != "function_block":
        diagnostics.append(
            IECSTDiagnostic(
                "implementation_shape_adjusted",
                "neutral IEC text uses FUNCTION_BLOCK to preserve the "
                "captured multi-direction interface",
                SourceSpan(0, 0),
            )
        )
    if len(executable_routines) > 1:
        diagnostics.append(
            IECSTDiagnostic(
                "multiple_routines_require_lifecycle_mapping",
                "multiple source routines require explicit execution-role "
                "and lifecycle mapping before target emission",
                SourceSpan(0, 0),
            )
        )
    diagnostics.extend(
        IECSTDiagnostic(item.code, item.message, item.span)
        for routine in unit.routines
        for item in routine.diagnostics
    )
    diagnostics.extend(emitter.diagnostics)
    return IECSTEmission(
        text="\n".join(lines) + "\n",
        diagnostics=tuple(diagnostics),
        requirements=_sorted_requirements(emitter.requirements),
    )


class _IECEmitter:
    def __init__(self, dialect: IECSTDialect | None = None) -> None:
        self.diagnostics: list[IECSTDiagnostic] = []
        self.requirements: set[IECRequirement] = set()
        self.dialect = dialect

    def interface(
        self,
        parameters: tuple[IRParameter, ...],
    ) -> list[str]:
        lines: list[str] = []
        groups = (
            (IRDirection.INPUT, "VAR_INPUT"),
            (IRDirection.OUTPUT, "VAR_OUTPUT"),
            (IRDirection.INOUT, "VAR_IN_OUT"),
            (IRDirection.UNKNOWN, "VAR"),
        )
        for direction, keyword in groups:
            members = [
                item for item in parameters if item.direction is direction
            ]
            if not members:
                continue
            lines.append(keyword)
            for parameter in members:
                lines.append(
                    f"    {parameter.name} : "
                    f"{self.parameter_type(parameter)};"
                )
            lines.append("END_VAR")
        return lines

    def parameter_type(self, parameter: IRParameter) -> str:
        """Render scalar, fixed-array, or generic-array parameter type."""

        if parameter.dimensions is None:
            return self.data_type(parameter.data_type)
        element = self.data_type(parameter.data_type)
        if parameter.generic_dimensions:
            if (
                self.dialect is None
                or not self.dialect.supports_generic_array_interface(
                    parameter.direction
                )
            ):
                self.requirements.add(
                    IECRequirement.GENERIC_ARRAY_INTERFACE
                )
            dimensions = ", ".join(
                "*" for _ in parameter.dimensions.split(",")
            )
            return f"ARRAY[{dimensions}] OF {element}"
        return self.data_type(parameter.data_type, parameter.dimensions)

    def data_type(
        self,
        data_type: str | None,
        dimensions: str | None = None,
    ) -> str:
        if data_type is None:
            self.diagnostics.append(
                IECSTDiagnostic(
                    "unknown_data_type",
                    "declaration has no resolved data type",
                    SourceSpan(0, 0),
                )
            )
            base = "TF_UNRESOLVED_TYPE"
        else:
            base = data_type
        if dimensions is None:
            return base
        bounds = []
        for dimension in dimensions.split(","):
            try:
                length = int(dimension)
            except ValueError:
                bounds.append("0..0")
            else:
                bounds.append(f"0..{max(length - 1, 0)}")
        return f"ARRAY[{', '.join(bounds)}] OF {base}"

    def statements(
        self,
        statements: tuple[IRStatement, ...],
        *,
        indent: int,
    ) -> list[str]:
        lines: list[str] = []
        for statement in statements:
            lines.extend(self.statement(statement, indent=indent))
        return lines

    def statement(
        self,
        statement: IRStatement,
        *,
        indent: int,
    ) -> list[str]:
        prefix = "    " * indent
        if isinstance(statement, IRAssignment):
            return [
                f"{prefix}{self.expression(statement.target)} := "
                f"{self.expression(statement.value)};"
            ]
        if isinstance(statement, IRCallStatement):
            return [f"{prefix}{self.expression(statement.call)};"]
        if isinstance(statement, IRWallClockRead):
            destination = self.expression(statement.destination)
            rendered = (
                self.dialect.render_wall_clock_read(
                    destination,
                    statement.timestamp_unit,
                )
                if self.dialect is not None
                else None
            )
            if rendered is None:
                self.requirements.add(IECRequirement.WALL_CLOCK_READ)
                return [f"{prefix}TF_WallClockRead({destination});"]
            return [f"{prefix}{line}" for line in rendered]
        if isinstance(statement, IRControllerObjectRead):
            self.requirements.add(IECRequirement.CONTROLLER_OBJECT_ACCESS)
            destination = self.expression(statement.destination)
            return [
                f"{prefix}(* TwinForge target adapter required: read "
                f"{_comment_text(statement.object_class)}/"
                f"{_comment_text(statement.instance)}/"
                f"{_comment_text(statement.attribute)} -> "
                f"{_comment_text(destination)} *)"
            ]
        if isinstance(statement, IRControllerObjectWrite):
            self.requirements.add(IECRequirement.CONTROLLER_OBJECT_ACCESS)
            value = self.expression(statement.value)
            return [
                f"{prefix}(* TwinForge target adapter required: write "
                f"{_comment_text(statement.object_class)}/"
                f"{_comment_text(statement.instance)}/"
                f"{_comment_text(statement.attribute)} <- "
                f"{_comment_text(value)} *)"
            ]
        if isinstance(statement, IRIf):
            lines: list[str] = []
            for index, branch in enumerate(statement.branches):
                keyword = "IF" if index == 0 else "ELSIF"
                lines.append(
                    f"{prefix}{keyword} "
                    f"{self.expression(branch.condition)} THEN"
                )
                lines.extend(
                    self.statements(
                        branch.statements,
                        indent=indent + 1,
                    )
                )
            if statement.else_statements:
                lines.append(f"{prefix}ELSE")
                lines.extend(
                    self.statements(
                        statement.else_statements,
                        indent=indent + 1,
                    )
                )
            lines.append(f"{prefix}END_IF;")
            return lines
        if isinstance(statement, IRWhile):
            lines = [
                f"{prefix}WHILE {self.expression(statement.condition)} DO"
            ]
            lines.extend(
                self.statements(statement.statements, indent=indent + 1)
            )
            lines.append(f"{prefix}END_WHILE;")
            return lines
        if isinstance(statement, IRExit):
            return [f"{prefix}EXIT;"]
        if isinstance(statement, IRUnsupportedStatement):
            self.diagnostics.append(
                IECSTDiagnostic(
                    "unsupported_statement",
                    statement.reason,
                    statement.span,
                )
            )
            return [
                f"{prefix}(* TwinForge unsupported: "
                f"{_comment_text(statement.source)} *)"
            ]
        self.diagnostics.append(
            IECSTDiagnostic(
                "unsupported_statement",
                f"unsupported IR statement {type(statement).__name__}",
                statement.span,
            )
        )
        return [f"{prefix}(* TwinForge unsupported IR statement *)"]

    def expression(self, expression: IRExpression) -> str:
        if isinstance(expression, IRReference):
            return expression.name
        if isinstance(expression, IRLiteral):
            return expression.lexical_value
        if isinstance(expression, IRUnary):
            return (
                f"{expression.operator} "
                f"({self.expression(expression.operand)})"
            )
        if isinstance(expression, IRBinary):
            return (
                f"({self.expression(expression.left)} "
                f"{_operator(expression.operator)} "
                f"{self.expression(expression.right)})"
            )
        if isinstance(expression, IRMember):
            return f"{self.expression(expression.target)}.{expression.member}"
        if isinstance(expression, IRIndex):
            indices = ", ".join(
                self.expression(item) for item in expression.indices
            )
            if expression.source_operator == ".[]":
                self.requirements.add(IECRequirement.DYNAMIC_BIT_ACCESS)
                return (
                    f"TF_BitAt({self.expression(expression.target)}, "
                    f"{indices})"
                )
            return f"{self.expression(expression.target)}[{indices}]"
        if isinstance(expression, IRArrayDimension):
            array = self.expression(expression.array)
            dimension = self.expression(expression.dimension)
            rendered = (
                self.dialect.render_array_dimension(array, dimension)
                if self.dialect is not None
                else None
            )
            if rendered is not None:
                return rendered
            self.requirements.add(IECRequirement.ARRAY_DIMENSION)
            return f"TF_ArrayDimension({array}, {dimension})"
        if isinstance(expression, IRCall):
            name = expression.operation
            if expression.adapter_required:
                self.requirements.add(
                    IECRequirement.SOURCE_OPERATION_ADAPTER
                )
                name = f"TF_{_identifier(name)}"
            elif name == "absolute_value":
                name = "ABS"
            arguments = ", ".join(
                self.expression(item) for item in expression.arguments
            )
            return f"{name}({arguments})"
        if isinstance(expression, IRUnsupportedExpression):
            self.diagnostics.append(
                IECSTDiagnostic(
                    "unsupported_expression",
                    expression.reason,
                    expression.span,
                )
            )
            return "TF_UNSUPPORTED()"
        self.diagnostics.append(
            IECSTDiagnostic(
                "unsupported_expression",
                f"unsupported IR expression {type(expression).__name__}",
                expression.span,
            )
        )
        return "TF_UNSUPPORTED()"


def _operator(value: str) -> str:
    return {
        "&": "AND",
        "|": "OR",
        "^": "XOR",
    }.get(value.upper(), value.upper())


def _identifier(value: str) -> str:
    cleaned = re.sub(r"\W+", "_", value).strip("_")
    return cleaned or "Operation"


def _comment_text(value: str) -> str:
    return " ".join(value.replace("*)", "* )").split())


def _sorted_requirements(
    requirements: set[IECRequirement],
) -> tuple[IECRequirement, ...]:
    return tuple(sorted(requirements, key=lambda item: item.value))
