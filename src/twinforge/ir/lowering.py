"""Lower resolved Structured Text semantics into executable neutral IR."""

from __future__ import annotations

from collections.abc import Iterator, Mapping

from twinforge.model import AddOnInstruction
from twinforge.structured_text import (
    AccessStatus,
    AssignmentStatement,
    BinaryExpression,
    CallExpression,
    CallKind,
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
    ReferenceStatus,
    SourceSpan,
    Statement,
    StructuredTextSemantics,
    TypeStatus,
    UnaryExpression,
    UnsupportedStatement,
    WhileStatement,
)

from .model import (
    IRArrayDimension,
    IRAssignment,
    IRBinary,
    IRCall,
    IRCallStatement,
    IRDiagnostic,
    IRDirection,
    IRExit,
    IRExpression,
    IRIf,
    IRIfBranch,
    IRIndex,
    IRLifecycle,
    IRLiteral,
    IRMember,
    IRParameter,
    IRReference,
    IRReusableUnit,
    IRRoutine,
    IRStatement,
    IRUnary,
    IRUnitKind,
    IRUnsupportedExpression,
    IRUnsupportedStatement,
    IRVariable,
    IRWhile,
)


def lower_structured_text(
    semantics: StructuredTextSemantics,
    *,
    routine_name: str = "",
) -> IRRoutine:
    """Lower one resolved ST document without target-specific decisions."""

    lowerer = _StructuredTextLowerer(semantics)
    statements = tuple(
        lowerer.statement(statement)
        for statement in semantics.document.statements
    )
    diagnostics = [
        IRDiagnostic(item.code, item.message, item.span)
        for item in semantics.diagnostics
    ]
    diagnostics.extend(lowerer.diagnostics)
    return IRRoutine(
        name=routine_name,
        source_language="ST",
        source=semantics.document.source,
        statements=statements,
        diagnostics=tuple(diagnostics),
    )


def lower_add_on_instruction(
    instruction: AddOnInstruction,
    routine_semantics: Mapping[str, StructuredTextSemantics],
) -> IRReusableUnit:
    """Assemble a neutral reusable unit from captured AOI evidence."""

    diagnostics: list[IRDiagnostic] = []
    routines: list[IRRoutine] = []
    for routine in instruction.routines.values():
        semantics = routine_semantics.get(routine.name)
        if semantics is None:
            diagnostics.append(
                IRDiagnostic(
                    "missing_routine_semantics",
                    f"routine {routine.name!r} has no semantic analysis",
                    SourceSpan(0, 0),
                )
            )
            continue
        routines.append(
            lower_structured_text(
                semantics,
                routine_name=routine.name,
            )
        )
    kind = (
        IRUnitKind.FUNCTION_BLOCK
        if (
            instruction.local_tags
            or instruction.execute_prescan
            or instruction.execute_postscan
            or instruction.execute_enable_in_false
        )
        else IRUnitKind.FUNCTION
    )
    return IRReusableUnit(
        name=instruction.name,
        kind=kind,
        parameters=tuple(
            IRParameter(
                name=parameter.name,
                direction=_direction(parameter.usage),
                data_type=parameter.data_type,
                dimensions=parameter.dimensions,
                generic_dimensions=(
                    parameter.dimensions is not None
                    and (parameter.usage or "").casefold() == "inout"
                ),
                required=parameter.required,
                visible=parameter.visible,
                system_defined=parameter.name.casefold()
                in {"enablein", "enableout"},
            )
            for parameter in instruction.parameters.values()
        ),
        variables=tuple(
            IRVariable(tag.name, tag.data_type, tag.dimensions)
            for tag in instruction.local_tags.values()
        ),
        routines=tuple(routines),
        source_vendor=instruction.vendor,
        lifecycle=IRLifecycle(
            prescan_enabled=instruction.execute_prescan,
            postscan_enabled=instruction.execute_postscan,
            enable_in_false_enabled=(
                instruction.execute_enable_in_false
            ),
        ),
        diagnostics=tuple(
            diagnostics + _interface_diagnostics(instruction, routines)
        ),
    )


class _StructuredTextLowerer:
    def __init__(self, semantics: StructuredTextSemantics) -> None:
        self.semantics = semantics
        self.source = semantics.document.source
        self.types = {
            (item.span.start, item.span.end): item
            for item in semantics.expression_types
        }
        self.references = {
            (item.span.start, item.span.end): item
            for item in semantics.references
        }
        self.accesses = {
            (item.span.start, item.span.end): item
            for item in semantics.accesses
        }
        self.calls = {
            (item.span.start, item.span.end): item
            for item in semantics.calls
        }
        self.diagnostics: list[IRDiagnostic] = []

    def statement(self, statement: Statement) -> IRStatement:
        if isinstance(statement, AssignmentStatement):
            return IRAssignment(
                span=statement.span,
                target=self.expression(statement.target),
                value=self.expression(statement.value),
            )
        if isinstance(statement, ExpressionStatement):
            if isinstance(statement.expression, CallExpression):
                special = self._instruction_statement(
                    statement.expression,
                )
                if special is not None:
                    return special
                call = self.expression(statement.expression)
                if isinstance(call, IRCall):
                    return IRCallStatement(span=statement.span, call=call)
            return self._unsupported_statement(
                statement,
                "expression statement did not lower to a call",
            )
        if isinstance(statement, IfStatement):
            return IRIf(
                span=statement.span,
                branches=tuple(
                    IRIfBranch(
                        span=branch.span,
                        condition=self.expression(branch.condition),
                        statements=tuple(
                            self.statement(item)
                            for item in branch.statements
                        ),
                    )
                    for branch in statement.branches
                ),
                else_statements=tuple(
                    self.statement(item)
                    for item in statement.else_statements
                ),
            )
        if isinstance(statement, WhileStatement):
            return IRWhile(
                span=statement.span,
                condition=self.expression(statement.condition),
                statements=tuple(
                    self.statement(item) for item in statement.statements
                ),
            )
        if isinstance(statement, ExitStatement):
            return IRExit(span=statement.span)
        if isinstance(statement, UnsupportedStatement):
            return self._unsupported_statement(
                statement,
                "source parser retained an unsupported statement",
            )
        return self._unsupported_statement(
            statement,
            f"unsupported statement node {type(statement).__name__}",
        )

    def expression(self, expression: Expression) -> IRExpression:
        data_type = self._data_type(expression)
        if isinstance(expression, NameExpression):
            reference = self.references.get(_key(expression))
            if (
                reference is None
                or reference.status is not ReferenceStatus.RESOLVED
            ):
                return self._unsupported_expression(
                    expression,
                    f"unresolved reference {expression.name!r}",
                )
            return IRReference(
                span=expression.span,
                data_type=data_type,
                name=expression.name,
            )
        if isinstance(expression, LiteralExpression):
            return IRLiteral(
                span=expression.span,
                data_type=data_type,
                lexical_value=expression.value,
            )
        if isinstance(expression, UnaryExpression):
            return IRUnary(
                span=expression.span,
                data_type=data_type,
                operator=expression.operator.upper(),
                operand=self.expression(expression.operand),
            )
        if isinstance(expression, BinaryExpression):
            return IRBinary(
                span=expression.span,
                data_type=data_type,
                left=self.expression(expression.left),
                operator=expression.operator.upper(),
                right=self.expression(expression.right),
            )
        if isinstance(expression, MemberExpression):
            access = self.accesses.get(_key(expression))
            if access is None or access.status is not AccessStatus.RESOLVED:
                return self._unsupported_expression(
                    expression,
                    "member access is not semantically resolved",
                )
            return IRMember(
                span=expression.span,
                data_type=data_type,
                target=self.expression(expression.target),
                member=expression.member,
            )
        if isinstance(expression, IndexExpression):
            access = self.accesses.get(_key(expression))
            if access is None or access.status is not AccessStatus.RESOLVED:
                return self._unsupported_expression(
                    expression,
                    "index access is not semantically resolved",
                )
            return IRIndex(
                span=expression.span,
                data_type=data_type,
                target=self.expression(expression.target),
                indices=tuple(
                    self.expression(item) for item in expression.indices
                ),
                source_operator=expression.operator,
            )
        if isinstance(expression, ParenthesizedExpression):
            return self.expression(expression.expression)
        if isinstance(expression, CallExpression):
            call = self.calls.get(_key(expression))
            if call is None or call.kind is CallKind.UNKNOWN:
                return self._unsupported_expression(
                    expression,
                    "call has no resolved neutral operation",
                )
            return IRCall(
                span=expression.span,
                data_type=data_type,
                operation=call.neutral_name,
                arguments=tuple(
                    self.expression(item.value)
                    for item in expression.arguments
                    if not isinstance(item.value, MissingExpression)
                ),
                adapter_required=call.vendor is not None,
                source_vendor=call.vendor,
            )
        if isinstance(expression, MissingExpression):
            return self._unsupported_expression(
                expression,
                "missing source expression",
            )
        return self._unsupported_expression(
            expression,
            f"unsupported expression node {type(expression).__name__}",
        )

    def _instruction_statement(
        self,
        expression: CallExpression,
    ) -> IRStatement | None:
        call = self.calls.get(_key(expression))
        if call is None or call.kind is not CallKind.ARRAY_DIMENSION_QUERY:
            return None
        if len(expression.arguments) != 3:
            return self._unsupported_statement(
                expression,
                "array dimension query requires array, dimension, destination",
            )
        array, dimension, destination = (
            item.value for item in expression.arguments
        )
        return IRAssignment(
            span=expression.span,
            target=self.expression(destination),
            value=IRArrayDimension(
                span=expression.span,
                data_type="DINT",
                array=self.expression(array),
                dimension=self.expression(dimension),
            ),
        )

    def _data_type(self, expression: Expression) -> str | None:
        item = self.types.get(_key(expression))
        if item is None or item.status is not TypeStatus.KNOWN:
            return None
        return item.data_type

    def _unsupported_expression(
        self,
        expression: Expression,
        reason: str,
    ) -> IRUnsupportedExpression:
        self.diagnostics.append(
            IRDiagnostic("unsupported_expression", reason, expression.span)
        )
        return IRUnsupportedExpression(
            span=expression.span,
            data_type=self._data_type(expression),
            source=self.source[expression.span.start : expression.span.end],
            reason=reason,
        )

    def _unsupported_statement(
        self,
        statement: Statement | Expression,
        reason: str,
    ) -> IRUnsupportedStatement:
        span = statement.span
        self.diagnostics.append(
            IRDiagnostic("unsupported_statement", reason, span)
        )
        return IRUnsupportedStatement(
            span=span,
            source=self.source[span.start : span.end],
            reason=reason,
        )


def _key(expression: Expression) -> tuple[int, int]:
    return expression.span.start, expression.span.end


def _direction(value: str | None) -> IRDirection:
    normalized = (value or "").casefold()
    if normalized == "input":
        return IRDirection.INPUT
    if normalized == "output":
        return IRDirection.OUTPUT
    if normalized == "inout":
        return IRDirection.INOUT
    return IRDirection.UNKNOWN


def _interface_diagnostics(
    instruction: AddOnInstruction,
    routines: list[IRRoutine],
) -> list[IRDiagnostic]:
    inputs = {
        parameter.name.casefold(): parameter.name
        for parameter in instruction.parameters.values()
        if (parameter.usage or "").casefold() == "input"
    }
    diagnostics: list[IRDiagnostic] = []
    reported: set[str] = set()
    for routine in routines:
        for statement in _walk_statements(routine.statements):
            if not isinstance(statement, IRAssignment):
                continue
            root = _root_reference(statement.target)
            if root is None or root.name.casefold() not in inputs:
                continue
            name = inputs[root.name.casefold()]
            if name.casefold() in reported:
                continue
            reported.add(name.casefold())
            diagnostics.append(
                IRDiagnostic(
                    "write_to_input_parameter",
                    f"captured logic writes input parameter {name!r}; "
                    "a target interface must preserve or redesign this effect",
                    statement.span,
                )
            )
    return diagnostics


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
