"""Typed, vendor-neutral executable intermediate representation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from twinforge.structured_text import SourceSpan


class IRUnitKind(str, Enum):
    """Portable implementation shape for a reusable logic unit."""

    FUNCTION = "function"
    FUNCTION_BLOCK = "function_block"


class IRDirection(str, Enum):
    """Data-flow direction of a reusable-unit parameter."""

    INPUT = "input"
    OUTPUT = "output"
    INOUT = "inout"
    UNKNOWN = "unknown"


class IRRoutineRole(str, Enum):
    """Execution role of one reusable-unit routine."""

    PRIMARY = "primary"
    AUXILIARY = "auxiliary"
    PRESCAN = "prescan"
    POSTSCAN = "postscan"
    ENABLE_IN_FALSE = "enable_in_false"
    UNKNOWN_LIFECYCLE = "unknown_lifecycle"
    UNKNOWN = "unknown"


class IRControllerObjectIntent(str, Enum):
    """Vendor-neutral meaning of a controller-managed object operation."""

    INSTANCE_IDENTITY = "instance_identity"
    CONNECTION_STATUS = "connection_status"
    FAULT_CODE = "fault_code"
    FAULT_INFORMATION = "fault_information"
    OPERATING_MODE = "operating_mode"
    SET_INHIBITED = "set_inhibited"
    SOURCE_SPECIFIC = "source_specific"


@dataclass(frozen=True)
class IRLifecycle:
    """Captured reusable-unit lifecycle activation evidence."""

    prescan_enabled: bool | None = None
    postscan_enabled: bool | None = None
    enable_in_false_enabled: bool | None = None


@dataclass(frozen=True, kw_only=True)
class IRExpression:
    """Base typed expression."""

    span: SourceSpan
    data_type: str | None = None


@dataclass(frozen=True, kw_only=True)
class IRUnsupportedExpression(IRExpression):
    """Expression retained when safe lowering is unavailable."""

    source: str
    reason: str


@dataclass(frozen=True, kw_only=True)
class IRReference(IRExpression):
    """Resolved data reference."""

    name: str


@dataclass(frozen=True, kw_only=True)
class IRLiteral(IRExpression):
    """Source literal retained in lexical form."""

    lexical_value: str


@dataclass(frozen=True, kw_only=True)
class IRUnary(IRExpression):
    """Portable unary expression."""

    operator: str
    operand: IRExpression


@dataclass(frozen=True, kw_only=True)
class IRBinary(IRExpression):
    """Portable binary expression."""

    left: IRExpression
    operator: str
    right: IRExpression


@dataclass(frozen=True, kw_only=True)
class IRMember(IRExpression):
    """Validated structure-member access."""

    target: IRExpression
    member: str


@dataclass(frozen=True, kw_only=True)
class IRIndex(IRExpression):
    """Validated array or dynamic-bit access."""

    target: IRExpression
    indices: tuple[IRExpression, ...]
    source_operator: str = "[]"


@dataclass(frozen=True, kw_only=True)
class IRCall(IRExpression):
    """Classified call that remains an expression in the neutral IR."""

    operation: str
    arguments: tuple[IRExpression, ...]
    adapter_required: bool = False
    source_vendor: str | None = None


@dataclass(frozen=True, kw_only=True)
class IRArrayDimension(IRExpression):
    """Query one zero-based dimension of an array."""

    array: IRExpression
    dimension: IRExpression


@dataclass(frozen=True, kw_only=True)
class IRStatement:
    """Base executable statement."""

    span: SourceSpan


@dataclass(frozen=True, kw_only=True)
class IRAssignment(IRStatement):
    """Assignment between lowered expressions."""

    target: IRExpression
    value: IRExpression


@dataclass(frozen=True, kw_only=True)
class IRCallStatement(IRStatement):
    """Call executed for effects."""

    call: IRCall


@dataclass(frozen=True, kw_only=True)
class IRWallClockRead(IRStatement):
    """Read a wall-clock timestamp into a destination in a declared unit."""

    destination: IRExpression
    timestamp_unit: str = "microseconds"


@dataclass(frozen=True, kw_only=True)
class IRControllerObjectRead(IRStatement):
    """Read a named attribute from a controller-managed object."""

    object_class: str
    instance: str
    attribute: str
    destination: IRExpression
    intent: IRControllerObjectIntent = (
        IRControllerObjectIntent.SOURCE_SPECIFIC
    )
    source_vendor: str | None = None


@dataclass(frozen=True, kw_only=True)
class IRControllerObjectWrite(IRStatement):
    """Write a named attribute on a controller-managed object."""

    object_class: str
    instance: str
    attribute: str
    value: IRExpression
    intent: IRControllerObjectIntent = (
        IRControllerObjectIntent.SOURCE_SPECIFIC
    )
    source_vendor: str | None = None


@dataclass(frozen=True, kw_only=True)
class IRIfBranch:
    """Condition and body of one IF or ELSIF branch."""

    span: SourceSpan
    condition: IRExpression
    statements: tuple[IRStatement, ...]


@dataclass(frozen=True, kw_only=True)
class IRIf(IRStatement):
    """Conditional statement."""

    branches: tuple[IRIfBranch, ...]
    else_statements: tuple[IRStatement, ...]


@dataclass(frozen=True, kw_only=True)
class IRWhile(IRStatement):
    """Pre-tested loop."""

    condition: IRExpression
    statements: tuple[IRStatement, ...]


@dataclass(frozen=True, kw_only=True)
class IRExit(IRStatement):
    """Exit from the innermost loop."""


@dataclass(frozen=True, kw_only=True)
class IRUnsupportedStatement(IRStatement):
    """Statement retained when safe lowering is unavailable."""

    source: str
    reason: str


@dataclass(frozen=True)
class IRDiagnostic:
    """Lowering issue linked to the original source span."""

    code: str
    message: str
    span: SourceSpan


@dataclass(frozen=True)
class IRParameter:
    """Reusable-unit parameter with its captured interface evidence."""

    name: str
    direction: IRDirection
    data_type: str | None = None
    dimensions: str | None = None
    generic_dimensions: bool = False
    required: bool | None = None
    visible: bool | None = None
    system_defined: bool = False
    default_value: bool | int | float | str | None = None
    default_lexical_value: str | None = None


@dataclass(frozen=True)
class IRVariable:
    """Retained instance variable."""

    name: str
    data_type: str | None = None
    dimensions: str | None = None


@dataclass(frozen=True)
class IRRoutine:
    """One lowered routine and its untouched source."""

    name: str
    source_language: str | None
    source: str
    statements: tuple[IRStatement, ...]
    diagnostics: tuple[IRDiagnostic, ...] = ()
    role: IRRoutineRole = IRRoutineRole.UNKNOWN


@dataclass(frozen=True)
class IRReusableUnit:
    """Vendor-neutral executable form of a reusable instruction."""

    name: str
    kind: IRUnitKind
    parameters: tuple[IRParameter, ...]
    variables: tuple[IRVariable, ...]
    routines: tuple[IRRoutine, ...]
    source_vendor: str | None = None
    lifecycle: IRLifecycle = IRLifecycle()
    diagnostics: tuple[IRDiagnostic, ...] = ()
