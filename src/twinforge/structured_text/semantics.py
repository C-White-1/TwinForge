"""Vendor-neutral semantic facts derived from Structured Text syntax."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .syntax import (
    AssignmentStatement,
    BinaryExpression,
    CallExpression,
    ExitStatement,
    Expression,
    ExpressionStatement,
    IfStatement,
    IndexExpression,
    LiteralExpression,
    MemberExpression,
    MissingExpression,
    NameExpression,
    ParenthesizedExpression,
    SourceSpan,
    Statement,
    StructuredTextDocument,
    UnaryExpression,
    UnsupportedStatement,
    WhileStatement,
)


class SymbolKind(str, Enum):
    """Storage or declaration category of a resolved name."""

    PARAMETER = "parameter"
    LOCAL = "local"
    PROGRAM_TAG = "program_tag"
    CONTROLLER_TAG = "controller_tag"


class ReferenceStatus(str, Enum):
    """Outcome of resolving a name against the supplied scope."""

    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


class AccessStatus(str, Enum):
    """Validation outcome for a member or index access."""

    RESOLVED = "resolved"
    UNVERIFIED = "unverified"
    INVALID = "invalid"


class TypeStatus(str, Enum):
    """Confidence of an inferred expression data type."""

    KNOWN = "known"
    UNKNOWN = "unknown"
    INVALID = "invalid"


class TypeCompatibility(str, Enum):
    """Compatibility of a source value with a destination declaration."""

    EXACT = "exact"
    IMPLICIT = "implicit"
    UNKNOWN = "unknown"
    INCOMPATIBLE = "incompatible"


class CallKind(str, Enum):
    """Portable semantic classification of a call expression."""

    ARRAY_DIMENSION_QUERY = "array_dimension_query"
    ABSOLUTE_VALUE = "absolute_value"
    BYTE_SWAP = "byte_swap"
    CONTROLLER_OBJECT_READ = "controller_object_read"
    CONTROLLER_OBJECT_WRITE = "controller_object_write"
    EXPLICIT_MESSAGE = "explicit_message"
    MEMORY_COPY = "memory_copy"
    RETENTIVE_TIMER = "retentive_timer"
    USER_DEFINED_INSTRUCTION = "user_defined_instruction"
    ROUTINE = "routine"
    FUNCTION_BLOCK_INSTANCE = "function_block_instance"
    UNKNOWN = "unknown"


class NeutralOperationKind(str, Enum):
    """Target-independent operation represented by one statement."""

    ASSIGN = "assign"
    CALL = "call"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    EXIT = "exit"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class SemanticSymbol:
    """One declaration made visible to semantic analysis."""

    name: str
    kind: SymbolKind
    data_type: str | None = None
    scope: str | None = None
    dimensions: str | None = None


@dataclass(frozen=True)
class SemanticTypeMember:
    """Captured member declaration used for path validation."""

    name: str
    data_type: str | None = None
    dimensions: str | None = None


@dataclass(frozen=True)
class SemanticType:
    """Captured structured data-type definition."""

    name: str
    members: tuple[SemanticTypeMember, ...]
    vendor: str | None = None
    source: str | None = None
    complete: bool = True


@dataclass(frozen=True)
class CallParameter:
    """One positional parameter in a semantic call contract."""

    name: str
    data_type: str | None = None
    direction: str | None = None
    dimensions: str | None = None
    generic_dimensions: bool = False


@dataclass(frozen=True)
class TypeConversionPolicy:
    """Source-dialect rules for implicit assignment conversion."""

    implicit_numeric: bool = False
    bit_bool_equivalent: bool = False
    implicit_numeric_boolean: bool = False
    string_family_compatible: bool = False


@dataclass(frozen=True)
class CallRule:
    """Declarative meaning for a source-language call name."""

    source_name: str
    kind: CallKind
    neutral_name: str
    vendor: str | None = None
    opaque_argument_indices: frozenset[int] = frozenset()
    minimum_arguments: int | None = None
    maximum_arguments: int | None = None
    result_type: str | None = None
    result_from_argument: int | None = None
    instance_data_type: str | None = None
    parameters: tuple[CallParameter, ...] = ()


@dataclass(frozen=True)
class SymbolReference:
    """Resolution result for a name expression used as data."""

    name: str
    span: SourceSpan
    status: ReferenceStatus
    symbol: SemanticSymbol | None = None


@dataclass(frozen=True)
class SemanticCall:
    """Classified call with its source spelling retained."""

    source_name: str
    neutral_name: str
    kind: CallKind
    span: SourceSpan
    vendor: str | None = None
    argument_count: int = 0
    signature_valid: bool | None = None
    bindings: tuple["ArgumentBinding", ...] = ()


@dataclass(frozen=True)
class ArgumentBinding:
    """Binding and type compatibility for one call argument."""

    parameter_name: str
    direction: str | None
    expected_type: str | None
    actual_type: str | None
    compatibility: TypeCompatibility
    span: SourceSpan


@dataclass(frozen=True)
class AssignmentCheck:
    """Type compatibility result for one assignment statement."""

    span: SourceSpan
    target_type: str | None
    value_type: str | None
    compatibility: TypeCompatibility


@dataclass(frozen=True)
class SemanticAccess:
    """Validation result for a member or array access."""

    path: str
    span: SourceSpan
    status: AccessStatus
    data_type: str | None = None
    dimensions: str | None = None


@dataclass(frozen=True)
class ExpressionType:
    """Best-evidence result type for one expression node."""

    span: SourceSpan
    status: TypeStatus
    data_type: str | None = None
    dimensions: str | None = None


@dataclass(frozen=True)
class NeutralOperation:
    """Target-independent statement operation and nested operations."""

    kind: NeutralOperationKind
    span: SourceSpan
    detail: str | None = None
    children: tuple["NeutralOperation", ...] = ()


@dataclass(frozen=True)
class SemanticDiagnostic:
    """A semantic uncertainty that requires more knowledge or review."""

    code: str
    message: str
    span: SourceSpan


@dataclass(frozen=True)
class SemanticContext:
    """Symbols and call meanings visible to one routine."""

    symbols: tuple[SemanticSymbol, ...] = ()
    types: tuple[SemanticType, ...] = ()
    call_rules: tuple[CallRule, ...] = ()
    conversion_policy: TypeConversionPolicy = TypeConversionPolicy()


@dataclass(frozen=True)
class StructuredTextSemantics:
    """Read-only semantic interpretation linked to a syntax document."""

    document: StructuredTextDocument
    type_definitions: tuple[SemanticType, ...]
    references: tuple[SymbolReference, ...]
    accesses: tuple[SemanticAccess, ...]
    expression_types: tuple[ExpressionType, ...]
    calls: tuple[SemanticCall, ...]
    assignments: tuple[AssignmentCheck, ...]
    operations: tuple[NeutralOperation, ...]
    diagnostics: tuple[SemanticDiagnostic, ...]


def analyze_semantics(
    document: StructuredTextDocument,
    context: SemanticContext,
) -> StructuredTextSemantics:
    """Resolve a parsed document without changing its syntax or source."""

    analyzer = _SemanticAnalyzer(document, context)
    return analyzer.analyze()


class _SemanticAnalyzer:
    def __init__(
        self,
        document: StructuredTextDocument,
        context: SemanticContext,
    ) -> None:
        self.document = document
        self.type_definitions = context.types
        self.symbols = {
            symbol.name.casefold(): symbol for symbol in context.symbols
        }
        self.call_rules = {
            rule.source_name.casefold(): rule for rule in context.call_rules
        }
        self.types = {
            item.name.casefold(): item for item in context.types
        }
        self.conversion_policy = context.conversion_policy
        self.references: list[SymbolReference] = []
        self.accesses: list[SemanticAccess] = []
        self.expression_types: list[ExpressionType] = []
        self.calls: list[SemanticCall] = []
        self.assignments: list[AssignmentCheck] = []
        self.diagnostics: list[SemanticDiagnostic] = []

    def analyze(self) -> StructuredTextSemantics:
        operations = tuple(
            self._statement(statement)
            for statement in self.document.statements
        )
        return StructuredTextSemantics(
            document=self.document,
            type_definitions=self.type_definitions,
            references=tuple(self.references),
            accesses=tuple(self.accesses),
            expression_types=tuple(self.expression_types),
            calls=tuple(self.calls),
            assignments=tuple(self.assignments),
            operations=operations,
            diagnostics=tuple(self.diagnostics),
        )

    def _statement(self, statement: Statement) -> NeutralOperation:
        if isinstance(statement, AssignmentStatement):
            target = self._expression(statement.target)
            value = self._expression(statement.value)
            compatibility = self._compatibility(target, value)
            self.assignments.append(
                AssignmentCheck(
                    statement.span,
                    target.data_type,
                    value.data_type,
                    compatibility,
                )
            )
            if compatibility is TypeCompatibility.INCOMPATIBLE:
                self.diagnostics.append(
                    SemanticDiagnostic(
                        "incompatible_assignment",
                        f"cannot assign {value.data_type!r} to "
                        f"{target.data_type!r}",
                        statement.span,
                    )
                )
            return NeutralOperation(
                NeutralOperationKind.ASSIGN,
                statement.span,
                statement.operator,
            )
        if isinstance(statement, ExpressionStatement):
            self._expression(statement.expression)
            return NeutralOperation(
                NeutralOperationKind.CALL,
                statement.span,
                _expression_name(statement.expression),
            )
        if isinstance(statement, IfStatement):
            children: list[NeutralOperation] = []
            for branch in statement.branches:
                self._expression(branch.condition)
                children.extend(
                    self._statement(item) for item in branch.statements
                )
            children.extend(
                self._statement(item)
                for item in statement.else_statements
            )
            return NeutralOperation(
                NeutralOperationKind.CONDITIONAL,
                statement.span,
                children=tuple(children),
            )
        if isinstance(statement, WhileStatement):
            self._expression(statement.condition)
            return NeutralOperation(
                NeutralOperationKind.LOOP,
                statement.span,
                children=tuple(
                    self._statement(item) for item in statement.statements
                ),
            )
        if isinstance(statement, ExitStatement):
            return NeutralOperation(NeutralOperationKind.EXIT, statement.span)
        if isinstance(statement, UnsupportedStatement):
            return NeutralOperation(
                NeutralOperationKind.UNSUPPORTED,
                statement.span,
                statement.text,
            )
        return NeutralOperation(
            NeutralOperationKind.UNSUPPORTED,
            statement.span,
        )

    def _expression(self, expression: Expression) -> _TypeValue:
        if isinstance(expression, NameExpression):
            result = self._reference(expression)
        elif isinstance(expression, LiteralExpression):
            result = _literal_type(expression.value)
        elif isinstance(expression, MissingExpression):
            result = _TypeValue()
        elif isinstance(expression, UnaryExpression):
            result = self._expression(expression.operand)
        elif isinstance(expression, BinaryExpression):
            left = self._expression(expression.left)
            right = self._expression(expression.right)
            result = _binary_type(expression.operator, left, right)
        elif isinstance(expression, MemberExpression):
            result = self._member(expression)
        elif isinstance(expression, IndexExpression):
            result = self._index(expression)
            for index in expression.indices:
                self._expression(index)
        elif isinstance(expression, ParenthesizedExpression):
            result = self._expression(expression.expression)
        elif isinstance(expression, CallExpression):
            result = self._call(expression)
        else:
            result = _TypeValue()
        self.expression_types.append(
            ExpressionType(
                expression.span,
                result.status,
                result.data_type,
                result.dimensions,
            )
        )
        return result

    def _reference(self, expression: NameExpression) -> _TypeValue:
        symbol = self.symbols.get(expression.name.casefold())
        status = (
            ReferenceStatus.RESOLVED
            if symbol is not None
            else ReferenceStatus.UNRESOLVED
        )
        self.references.append(
            SymbolReference(
                expression.name,
                expression.span,
                status,
                symbol,
            )
        )
        if symbol is None:
            self.diagnostics.append(
                SemanticDiagnostic(
                    "unresolved_symbol",
                    f"symbol {expression.name!r} is not declared in this scope",
                    expression.span,
                )
            )
            return _TypeValue()
        return _TypeValue(
            symbol.data_type,
            symbol.dimensions,
            (
                TypeStatus.KNOWN
                if symbol.data_type is not None
                else TypeStatus.UNKNOWN
            ),
        )

    def _member(self, expression: MemberExpression) -> _TypeValue:
        target = self._expression(expression.target)
        path = _expression_name(expression)
        if (
            expression.member.isdigit()
            and _is_integer_type(target.data_type)
        ):
            status = AccessStatus.RESOLVED
            result = _TypeValue("BOOL", status=TypeStatus.KNOWN)
        elif target.data_type is None:
            status = AccessStatus.UNVERIFIED
            result = _TypeValue()
        else:
            definition = self.types.get(target.data_type.casefold())
            if definition is None:
                status = AccessStatus.UNVERIFIED
                result = _TypeValue()
            else:
                member = next(
                    (
                        item
                        for item in definition.members
                        if item.name.casefold()
                        == expression.member.casefold()
                    ),
                    None,
                )
                if member is None:
                    if definition.complete:
                        status = AccessStatus.INVALID
                        result = _TypeValue(status=TypeStatus.INVALID)
                        self.diagnostics.append(
                            SemanticDiagnostic(
                                "invalid_member",
                                f"type {definition.name!r} has no member "
                                f"{expression.member!r}",
                                expression.span,
                            )
                        )
                    else:
                        status = AccessStatus.UNVERIFIED
                        result = _TypeValue()
                else:
                    status = AccessStatus.RESOLVED
                    result = _TypeValue(
                        member.data_type,
                        member.dimensions,
                        (
                            TypeStatus.KNOWN
                            if member.data_type is not None
                            else TypeStatus.UNKNOWN
                        ),
                    )
        self.accesses.append(
            SemanticAccess(
                path,
                expression.span,
                status,
                result.data_type,
                result.dimensions,
            )
        )
        return result

    def _index(self, expression: IndexExpression) -> _TypeValue:
        target = self._expression(expression.target)
        path = _expression_name(expression)
        if (
            expression.operator == ".[]"
            and _is_integer_type(target.data_type)
        ):
            status = AccessStatus.RESOLVED
            result = _TypeValue("BOOL", status=TypeStatus.KNOWN)
        elif target.status is TypeStatus.INVALID:
            status = AccessStatus.INVALID
            result = target
        elif target.status is TypeStatus.UNKNOWN:
            status = AccessStatus.UNVERIFIED
            result = _TypeValue()
        elif target.dimensions is None:
            status = AccessStatus.INVALID
            result = _TypeValue(status=TypeStatus.INVALID)
            self.diagnostics.append(
                SemanticDiagnostic(
                    "index_on_scalar",
                    f"{path!r} indexes a declaration with no array dimensions",
                    expression.span,
                )
            )
        elif _is_array_dimension(target.dimensions):
            status = AccessStatus.RESOLVED
            result = _TypeValue(
                target.data_type,
                status=target.status,
            )
        else:
            status = AccessStatus.INVALID
            result = _TypeValue(status=TypeStatus.INVALID)
            self.diagnostics.append(
                SemanticDiagnostic(
                    "index_on_scalar",
                    f"{path!r} indexes scalar dimension "
                    f"{target.dimensions!r}",
                    expression.span,
                )
            )
        self.accesses.append(
            SemanticAccess(
                path,
                expression.span,
                status,
                result.data_type,
                result.dimensions,
            )
        )
        return result

    def _call(self, expression: CallExpression) -> _TypeValue:
        source_name = _expression_name(expression.callee)
        rule = self.call_rules.get(source_name.casefold())
        callee_symbol = (
            self.symbols.get(source_name.casefold())
            if isinstance(expression.callee, NameExpression)
            else None
        )
        if rule is not None:
            signature_valid = self._validate_signature(expression, rule)
            bindings = self._bind_arguments(expression, rule)
            call = SemanticCall(
                source_name=source_name,
                neutral_name=rule.neutral_name,
                kind=rule.kind,
                span=expression.span,
                vendor=rule.vendor,
                argument_count=len(expression.arguments),
                signature_valid=signature_valid,
                bindings=bindings,
            )
            opaque = rule.opaque_argument_indices
        elif callee_symbol is not None:
            call = SemanticCall(
                source_name=source_name,
                neutral_name=source_name,
                kind=CallKind.FUNCTION_BLOCK_INSTANCE,
                span=expression.span,
                argument_count=len(expression.arguments),
                signature_valid=None,
                bindings=(),
            )
            opaque = frozenset()
        else:
            call = SemanticCall(
                source_name=source_name,
                neutral_name=source_name,
                kind=CallKind.UNKNOWN,
                span=expression.span,
                argument_count=len(expression.arguments),
                signature_valid=None,
                bindings=(),
            )
            opaque = frozenset()
            self.diagnostics.append(
                SemanticDiagnostic(
                    "unknown_call",
                    f"call {source_name!r} has no declared semantic rule",
                    expression.callee.span,
                )
            )
        self.calls.append(call)
        if not isinstance(expression.callee, NameExpression):
            self._expression(expression.callee)
        argument_types: dict[int, _TypeValue] = {}
        for index, argument in enumerate(expression.arguments):
            if index not in opaque and index >= len(call.bindings):
                argument_types[index] = self._expression(argument.value)
        if rule is None:
            return _TypeValue()
        if rule.result_type is not None:
            return _TypeValue(rule.result_type, status=TypeStatus.KNOWN)
        if (
            rule.result_from_argument is not None
            and rule.result_from_argument in argument_types
        ):
            return argument_types[rule.result_from_argument]
        return _TypeValue()

    def _bind_arguments(
        self,
        expression: CallExpression,
        rule: CallRule,
    ) -> tuple[ArgumentBinding, ...]:
        contracts: list[CallParameter] = []
        if rule.instance_data_type is not None:
            contracts.append(
                CallParameter(
                    "@instance",
                    rule.instance_data_type,
                    "InOut",
                )
            )
        contracts.extend(rule.parameters)
        bindings: list[ArgumentBinding] = []
        for argument, parameter in zip(
            expression.arguments,
            contracts,
            strict=False,
        ):
            actual = self._expression(argument.value)
            expected = _TypeValue(
                parameter.data_type,
                parameter.dimensions,
                (
                    TypeStatus.KNOWN
                    if parameter.data_type is not None
                    else TypeStatus.UNKNOWN
                ),
                parameter.generic_dimensions,
            )
            compatibility = self._compatibility(expected, actual)
            bindings.append(
                ArgumentBinding(
                    parameter.name,
                    parameter.direction,
                    parameter.data_type,
                    actual.data_type,
                    compatibility,
                    argument.span,
                )
            )
            if (
                parameter.direction in {"Output", "InOut"}
                and not _is_assignable(argument.value)
            ):
                self.diagnostics.append(
                    SemanticDiagnostic(
                        "non_assignable_output_argument",
                        f"argument for {parameter.direction} parameter "
                        f"{parameter.name!r} is not assignable",
                        argument.span,
                    )
                )
            if compatibility is TypeCompatibility.INCOMPATIBLE:
                self.diagnostics.append(
                    SemanticDiagnostic(
                        "incompatible_argument",
                        f"argument for parameter {parameter.name!r} has "
                        f"type {actual.data_type!r}; expected "
                        f"{parameter.data_type!r}",
                        argument.span,
                    )
                )
        return tuple(bindings)

    def _compatibility(
        self,
        expected: _TypeValue,
        actual: _TypeValue,
    ) -> TypeCompatibility:
        if (
            expected.status is not TypeStatus.KNOWN
            or actual.status is not TypeStatus.KNOWN
            or expected.data_type is None
            or actual.data_type is None
        ):
            return TypeCompatibility.UNKNOWN
        if not _dimensions_compatible(
            expected.dimensions,
            actual.dimensions,
            expected.generic_dimensions,
        ):
            return TypeCompatibility.INCOMPATIBLE
        expected_name = expected.data_type.upper()
        actual_name = actual.data_type.upper()
        if expected_name == actual_name:
            return TypeCompatibility.EXACT
        if (
            self.conversion_policy.bit_bool_equivalent
            and {expected_name, actual_name} <= {"BIT", "BOOL"}
        ):
            return TypeCompatibility.IMPLICIT
        if (
            self.conversion_policy.implicit_numeric_boolean
            and expected_name in {"BIT", "BOOL"}
            and _is_integer_type(actual_name)
        ):
            return TypeCompatibility.IMPLICIT
        if (
            self.conversion_policy.string_family_compatible
            and actual_name == "STRING"
            and _is_string_type(expected_name)
        ):
            return TypeCompatibility.IMPLICIT
        if (
            self.conversion_policy.implicit_numeric
            and _is_numeric_type(expected_name)
            and _is_numeric_type(actual_name)
        ):
            return TypeCompatibility.IMPLICIT
        return TypeCompatibility.INCOMPATIBLE

    def _validate_signature(
        self,
        expression: CallExpression,
        rule: CallRule,
    ) -> bool | None:
        if (
            rule.minimum_arguments is None
            and rule.maximum_arguments is None
        ):
            return None
        count = len(expression.arguments)
        minimum = rule.minimum_arguments
        maximum = rule.maximum_arguments
        valid = (
            (minimum is None or count >= minimum)
            and (maximum is None or count <= maximum)
        )
        if not valid:
            expected = (
                str(minimum)
                if minimum == maximum
                else f"{minimum or 0}..{maximum or 'unbounded'}"
            )
            self.diagnostics.append(
                SemanticDiagnostic(
                    "invalid_argument_count",
                    f"call {rule.source_name!r} has {count} arguments; "
                    f"expected {expected}",
                    expression.span,
                )
            )
        return valid


def _expression_name(expression: Expression) -> str:
    if isinstance(expression, NameExpression):
        return expression.name
    if isinstance(expression, MemberExpression):
        return f"{_expression_name(expression.target)}.{expression.member}"
    if isinstance(expression, IndexExpression):
        return f"{_expression_name(expression.target)}{expression.operator}"
    return "<expression>"


@dataclass(frozen=True)
class _TypeValue:
    data_type: str | None = None
    dimensions: str | None = None
    status: TypeStatus = TypeStatus.UNKNOWN
    generic_dimensions: bool = False


def _literal_type(value: str) -> _TypeValue:
    upper = value.upper()
    if upper in {"TRUE", "FALSE"}:
        return _TypeValue("BOOL", status=TypeStatus.KNOWN)
    if value.startswith(("'", '"')):
        return _TypeValue("STRING", status=TypeStatus.KNOWN)
    if "#" in value:
        prefix = value.split("#", 1)[0].upper()
        if prefix.isidentifier():
            return _TypeValue(prefix, status=TypeStatus.KNOWN)
    if any(character in value for character in ".eE"):
        return _TypeValue("REAL", status=TypeStatus.KNOWN)
    return _TypeValue("DINT", status=TypeStatus.KNOWN)


def _binary_type(
    operator: str,
    left: _TypeValue,
    right: _TypeValue,
) -> _TypeValue:
    normalized = operator.upper()
    if normalized in {"=", "<>", "<", "<=", ">", ">="}:
        return _TypeValue("BOOL", status=TypeStatus.KNOWN)
    if normalized in {"AND", "OR", "XOR", "&", "|", "^"}:
        if left.data_type == right.data_type:
            return left
        return _TypeValue()
    numeric = _promote_numeric(left.data_type, right.data_type)
    return (
        _TypeValue(numeric, status=TypeStatus.KNOWN)
        if numeric is not None
        else _TypeValue()
    )


def _promote_numeric(
    left: str | None,
    right: str | None,
) -> str | None:
    order = (
        "SINT",
        "USINT",
        "INT",
        "UINT",
        "DINT",
        "UDINT",
        "LINT",
        "ULINT",
        "REAL",
        "LREAL",
    )
    normalized = {
        item.upper()
        for item in (left, right)
        if item is not None
    }
    if not normalized or not normalized.issubset(set(order)):
        return None
    return max(normalized, key=order.index)


def _is_integer_type(data_type: str | None) -> bool:
    return (data_type or "").upper() in {
        "SINT",
        "USINT",
        "INT",
        "UINT",
        "DINT",
        "UDINT",
        "LINT",
        "ULINT",
    }


def _is_numeric_type(data_type: str | None) -> bool:
    return _is_integer_type(data_type) or (data_type or "").upper() in {
        "REAL",
        "LREAL",
    }


def _is_array_dimension(value: str) -> bool:
    return any(
        item.strip().isdigit() and int(item.strip()) > 0
        for item in value.split(",")
    )


def _dimensions_compatible(
    expected: str | None,
    actual: str | None,
    expected_generic: bool = False,
) -> bool:
    expected_array = (
        expected is not None and _is_array_dimension(expected)
    )
    actual_array = actual is not None and _is_array_dimension(actual)
    if expected_array != actual_array:
        return False
    if not expected_array:
        return True
    if expected_generic:
        return _dimension_rank(expected) == _dimension_rank(actual)
    return expected == actual


def _is_assignable(expression: Expression) -> bool:
    return isinstance(
        expression,
        (NameExpression, MemberExpression, IndexExpression),
    )


def _dimension_rank(value: str | None) -> int:
    if value is None:
        return 0
    return len(value.split(","))


def _is_string_type(data_type: str) -> bool:
    return data_type == "STRING" or data_type.startswith("STR_")
