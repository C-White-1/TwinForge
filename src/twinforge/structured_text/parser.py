"""Recovering parser for the initial TwinForge Structured Text subset."""

from __future__ import annotations

from .lexer import lex_structured_text
from .syntax import (
    AssignmentStatement,
    BinaryExpression,
    CallArgument,
    CallExpression,
    Expression,
    ExpressionStatement,
    ExitStatement,
    IfBranch,
    IfStatement,
    IndexExpression,
    LiteralExpression,
    MemberExpression,
    MissingExpression,
    NameExpression,
    ParenthesizedExpression,
    SourceSpan,
    Statement,
    StructuredTextDiagnostic,
    StructuredTextDocument,
    StructuredTextToken,
    TokenKind,
    UnaryExpression,
    UnsupportedStatement,
    WhileStatement,
)


_TRIVIA = {TokenKind.WHITESPACE, TokenKind.COMMENT}
_UNARY = {"NOT", "+", "-"}
_PRECEDENCE = {
    "OR": 1,
    "|": 1,
    "XOR": 2,
    "^": 2,
    "AND": 3,
    "&": 3,
    "=": 4,
    "<>": 4,
    "<": 4,
    "<=": 4,
    ">": 4,
    ">=": 4,
    "+": 5,
    "-": 5,
    "*": 6,
    "/": 6,
    "MOD": 6,
}


def parse_structured_text(source: str) -> StructuredTextDocument:
    """Parse supported syntax while retaining every source character."""

    tokens, lexical_diagnostics = lex_structured_text(source)
    parser = _Parser(source, tokens, lexical_diagnostics)
    return parser.parse()


class _Parser:
    def __init__(
        self,
        source: str,
        tokens: tuple[StructuredTextToken, ...],
        lexical_diagnostics: tuple[StructuredTextDiagnostic, ...],
    ) -> None:
        self.source = source
        self.tokens = tokens
        self.position = 0
        self.diagnostics = list(lexical_diagnostics)

    def parse(self) -> StructuredTextDocument:
        statements = self._statement_list(set())
        return StructuredTextDocument(
            source=self.source,
            tokens=self.tokens,
            statements=statements,
            diagnostics=tuple(self.diagnostics),
        )

    def _statement_list(
        self,
        terminators: set[str],
    ) -> tuple[Statement, ...]:
        statements: list[Statement] = []
        while not self._at(TokenKind.END_OF_FILE):
            if self._keyword_in(terminators):
                break
            if self._at(TokenKind.END_OF_FILE):
                break
            start_position = self.position
            statement = self._statement()
            if statement is not None:
                statements.append(statement)
            if self.position == start_position:
                statements.append(self._recover_statement("unsupported_statement"))
        return tuple(statements)

    def _statement(self) -> Statement | None:
        self._skip_trivia()
        if self._at(TokenKind.END_OF_FILE):
            return None
        if self._keyword("IF"):
            return self._if_statement()
        if self._keyword("WHILE"):
            return self._while_statement()
        if self._keyword("EXIT"):
            start = self._take(skip_trivia=True).span.start
            return ExitStatement(
                SourceSpan(start, self._statement_end(start))
            )

        start = self._current().span.start
        expression = self._expression()
        if expression is None:
            return self._recover_statement("expected_statement")
        if self._at(TokenKind.ASSIGN, skip_trivia=True):
            operator = self._take(skip_trivia=True)
            value = self._expression()
            if value is None:
                return self._recover_statement("expected_assignment_value")
            end = self._statement_end(value.span.end)
            return AssignmentStatement(
                span=SourceSpan(start, end),
                target=expression,
                operator=operator.text,
                value=value,
            )
        end = self._statement_end(expression.span.end)
        if isinstance(expression, CallExpression):
            return ExpressionStatement(
                span=SourceSpan(start, end),
                expression=expression,
            )
        self._diagnostic(
            "unsupported_expression_statement",
            "only call expressions are supported as expression statements",
            SourceSpan(start, end),
        )
        return UnsupportedStatement(
            span=SourceSpan(start, end),
            text=self.source[start:end],
        )

    def _if_statement(self) -> IfStatement:
        start = self._take(skip_trivia=True).span.start
        branches = [self._if_branch(start, keyword_taken=True)]
        while self._keyword("ELSIF", skip_trivia=True):
            branch_start = self._take(skip_trivia=True).span.start
            branches.append(self._if_branch(branch_start, keyword_taken=True))

        else_statements: tuple[Statement, ...] = ()
        if self._keyword("ELSE", skip_trivia=True):
            self._take(skip_trivia=True)
            else_statements = self._statement_list({"END_IF"})

        if self._keyword("END_IF", skip_trivia=True):
            end = self._take(skip_trivia=True).span.end
            end = self._statement_end(end)
        else:
            end = self._current().span.start
            self._diagnostic(
                "missing_end_if",
                "IF statement is missing END_IF",
                SourceSpan(start, end),
            )
        return IfStatement(
            span=SourceSpan(start, end),
            branches=tuple(branches),
            else_statements=else_statements,
        )

    def _if_branch(
        self,
        start: int,
        *,
        keyword_taken: bool = False,
    ) -> IfBranch:
        if not keyword_taken:
            self._take(skip_trivia=True)
        condition = self._expression()
        if condition is None:
            condition = MissingExpression(SourceSpan(start, start))
            self._diagnostic(
                "missing_if_condition",
                "IF branch is missing a condition",
                condition.span,
            )
        if self._keyword("THEN", skip_trivia=True):
            self._take(skip_trivia=True)
        else:
            self._diagnostic(
                "missing_then",
                "IF branch is missing THEN",
                condition.span,
            )
        statements = self._statement_list({"ELSIF", "ELSE", "END_IF"})
        end = (
            statements[-1].span.end
            if statements
            else condition.span.end
        )
        return IfBranch(
            span=SourceSpan(start, end),
            condition=condition,
            statements=statements,
        )

    def _while_statement(self) -> WhileStatement:
        start = self._take(skip_trivia=True).span.start
        condition = self._expression()
        if condition is None:
            condition = MissingExpression(SourceSpan(start, start))
            self._diagnostic(
                "missing_while_condition",
                "WHILE statement is missing a condition",
                condition.span,
            )
        if self._keyword("DO", skip_trivia=True):
            self._take(skip_trivia=True)
        else:
            self._diagnostic(
                "missing_do",
                "WHILE statement is missing DO",
                condition.span,
            )
        statements = self._statement_list({"END_WHILE"})
        if self._keyword("END_WHILE", skip_trivia=True):
            end = self._take(skip_trivia=True).span.end
            end = self._statement_end(end)
        else:
            end = self._current().span.start
            self._diagnostic(
                "missing_end_while",
                "WHILE statement is missing END_WHILE",
                SourceSpan(start, end),
            )
        return WhileStatement(
            span=SourceSpan(start, end),
            condition=condition,
            statements=statements,
        )

    def _expression(
        self,
        minimum_precedence: int = 1,
    ) -> Expression | None:
        left = self._unary()
        if left is None:
            return None
        while True:
            operator = self._binary_operator()
            if operator is None:
                break
            precedence = _PRECEDENCE[operator.upper()]
            if precedence < minimum_precedence:
                break
            operator_token = self._take(skip_trivia=True)
            right = self._expression(precedence + 1)
            if right is None:
                self._diagnostic(
                    "missing_binary_operand",
                    f"operator {operator_token.text!r} has no right operand",
                    operator_token.span,
                )
                break
            left = BinaryExpression(
                span=SourceSpan(left.span.start, right.span.end),
                left=left,
                operator=operator_token.text,
                right=right,
            )
        return left

    def _unary(self) -> Expression | None:
        token = self._peek(skip_trivia=True)
        if self._operator_text(token) in _UNARY:
            operator = self._take(skip_trivia=True)
            operand = self._unary()
            if operand is None:
                self._diagnostic(
                    "missing_unary_operand",
                    f"operator {operator.text!r} has no operand",
                    operator.span,
                )
                return MissingExpression(
                    SourceSpan(operator.span.end, operator.span.end)
                )
            return UnaryExpression(
                span=SourceSpan(operator.span.start, operand.span.end),
                operator=operator.text,
                operand=operand,
            )
        return self._postfix()

    def _postfix(self) -> Expression | None:
        expression = self._primary()
        if expression is None:
            return None
        while True:
            if self._at(TokenKind.DOT, skip_trivia=True):
                dot = self._take(skip_trivia=True)
                if self._at(TokenKind.LEFT_BRACKET, skip_trivia=True):
                    expression = self._index_expression(
                        expression,
                        operator=".[]",
                    )
                    continue
                member = self._peek(skip_trivia=True)
                if member.kind not in {
                    TokenKind.IDENTIFIER,
                    TokenKind.LITERAL,
                }:
                    self._diagnostic(
                        "missing_member",
                        "member selector is missing its member name",
                        SourceSpan(dot.span.start, member.span.end),
                    )
                    break
                member = self._take(skip_trivia=True)
                expression = MemberExpression(
                    span=SourceSpan(expression.span.start, member.span.end),
                    target=expression,
                    member=member.text,
                )
            elif self._at(TokenKind.LEFT_BRACKET, skip_trivia=True):
                expression = self._index_expression(expression)
            elif self._at(TokenKind.LEFT_PAREN, skip_trivia=True):
                expression = self._call_expression(expression)
            else:
                break
        return expression

    def _primary(self) -> Expression | None:
        token = self._peek(skip_trivia=True)
        if token.kind is TokenKind.IDENTIFIER:
            token = self._take(skip_trivia=True)
            if token.text.upper() in {"TRUE", "FALSE"}:
                return LiteralExpression(token.span, token.text)
            return NameExpression(token.span, token.text)
        if token.kind in {TokenKind.LITERAL, TokenKind.STRING}:
            token = self._take(skip_trivia=True)
            return LiteralExpression(token.span, token.text)
        if token.kind is TokenKind.LEFT_PAREN:
            opening = self._take(skip_trivia=True)
            expression = self._expression()
            if expression is None:
                expression = MissingExpression(
                    SourceSpan(opening.span.end, opening.span.end)
                )
            if self._at(TokenKind.RIGHT_PAREN, skip_trivia=True):
                closing = self._take(skip_trivia=True)
                end = closing.span.end
            else:
                end = expression.span.end
                self._diagnostic(
                    "missing_right_parenthesis",
                    "parenthesized expression is missing ')'",
                    SourceSpan(opening.span.start, end),
                )
            return ParenthesizedExpression(
                span=SourceSpan(opening.span.start, end),
                expression=expression,
            )
        return None

    def _index_expression(
        self,
        target: Expression,
        *,
        operator: str = "[]",
    ) -> IndexExpression:
        self._take(skip_trivia=True)
        indices: list[Expression] = []
        while not self._at(TokenKind.RIGHT_BRACKET, skip_trivia=True):
            expression = self._expression()
            if expression is None:
                expression = MissingExpression(
                    SourceSpan(
                        self._peek(skip_trivia=True).span.start,
                        self._peek(skip_trivia=True).span.start,
                    )
                )
            indices.append(expression)
            if self._at(TokenKind.COMMA, skip_trivia=True):
                self._take(skip_trivia=True)
            else:
                break
        if self._at(TokenKind.RIGHT_BRACKET, skip_trivia=True):
            end = self._take(skip_trivia=True).span.end
        else:
            end = indices[-1].span.end if indices else target.span.end
            self._diagnostic(
                "missing_right_bracket",
                "index expression is missing ']'",
                SourceSpan(target.span.start, end),
            )
        return IndexExpression(
            span=SourceSpan(target.span.start, end),
            target=target,
            indices=tuple(indices),
            operator=operator,
        )

    def _call_expression(self, callee: Expression) -> CallExpression:
        self._take(skip_trivia=True)
        arguments: list[CallArgument] = []
        while not self._at(TokenKind.RIGHT_PAREN, skip_trivia=True):
            argument_start = self._peek(skip_trivia=True).span.start
            if self._at(TokenKind.COMMA, skip_trivia=True):
                missing = MissingExpression(
                    SourceSpan(argument_start, argument_start)
                )
                arguments.append(
                    CallArgument(missing.span, missing)
                )
                self._take(skip_trivia=True)
                continue

            name: str | None = None
            direction: str | None = None
            first = self._peek(skip_trivia=True)
            second = self._peek(skip_trivia=True, offset=1)
            if (
                first.kind is TokenKind.IDENTIFIER
                and second.kind
                in {TokenKind.ASSIGN, TokenKind.OUTPUT_ASSIGN}
            ):
                name = self._take(skip_trivia=True).text
                direction = self._take(skip_trivia=True).text

            value = self._expression()
            if value is None:
                value = MissingExpression(
                    SourceSpan(argument_start, argument_start)
                )
                self._diagnostic(
                    "missing_call_argument",
                    "call argument is missing",
                    value.span,
                )
            arguments.append(
                CallArgument(
                    span=SourceSpan(argument_start, value.span.end),
                    value=value,
                    name=name,
                    direction=direction,
                )
            )
            if self._at(TokenKind.COMMA, skip_trivia=True):
                self._take(skip_trivia=True)
            else:
                break

        if self._at(TokenKind.RIGHT_PAREN, skip_trivia=True):
            end = self._take(skip_trivia=True).span.end
        else:
            end = arguments[-1].span.end if arguments else callee.span.end
            self._diagnostic(
                "missing_call_parenthesis",
                "call expression is missing ')'",
                SourceSpan(callee.span.start, end),
            )
        return CallExpression(
            span=SourceSpan(callee.span.start, end),
            callee=callee,
            arguments=tuple(arguments),
        )

    def _binary_operator(self) -> str | None:
        token = self._peek(skip_trivia=True)
        value = self._operator_text(token)
        return value if value in _PRECEDENCE else None

    @staticmethod
    def _operator_text(token: StructuredTextToken) -> str:
        if token.kind is TokenKind.OPERATOR:
            return token.text.upper()
        if (
            token.kind is TokenKind.IDENTIFIER
            and token.text.upper() in set(_PRECEDENCE) | _UNARY
        ):
            return token.text.upper()
        return ""

    def _statement_end(self, fallback: int) -> int:
        if self._at(TokenKind.SEMICOLON, skip_trivia=True):
            return self._take(skip_trivia=True).span.end
        self._diagnostic(
            "missing_semicolon",
            "statement is missing ';'",
            SourceSpan(fallback, fallback),
        )
        return fallback

    def _recover_statement(self, code: str) -> UnsupportedStatement:
        self._skip_trivia()
        start = self._current().span.start
        while not self._at(TokenKind.END_OF_FILE):
            if self._at(TokenKind.SEMICOLON):
                end = self._take().span.end
                break
            if self._keyword_in({"ELSIF", "ELSE", "END_IF"}):
                end = self._current().span.start
                break
            self.position += 1
        else:
            end = self._current().span.end
        span = SourceSpan(start, end)
        self._diagnostic(
            code,
            "statement was retained without a structured interpretation",
            span,
        )
        return UnsupportedStatement(span, self.source[start:end])

    def _keyword(
        self,
        value: str,
        *,
        skip_trivia: bool = False,
    ) -> bool:
        token = self._peek(skip_trivia=skip_trivia)
        return (
            token.kind is TokenKind.IDENTIFIER
            and token.text.upper() == value
        )

    def _keyword_in(self, values: set[str]) -> bool:
        self._skip_trivia()
        token = self._current()
        return (
            token.kind is TokenKind.IDENTIFIER
            and token.text.upper() in values
        )

    def _at(
        self,
        kind: TokenKind,
        *,
        skip_trivia: bool = False,
    ) -> bool:
        return self._peek(skip_trivia=skip_trivia).kind is kind

    def _peek(
        self,
        *,
        skip_trivia: bool = False,
        offset: int = 0,
    ) -> StructuredTextToken:
        position = self.position
        if skip_trivia:
            while (
                position < len(self.tokens)
                and self.tokens[position].kind in _TRIVIA
            ):
                position += 1
        while offset > 0:
            position += 1
            if skip_trivia:
                while (
                    position < len(self.tokens)
                    and self.tokens[position].kind in _TRIVIA
                ):
                    position += 1
            offset -= 1
        return self.tokens[min(position, len(self.tokens) - 1)]

    def _take(
        self,
        *,
        skip_trivia: bool = False,
    ) -> StructuredTextToken:
        if skip_trivia:
            self._skip_trivia()
        token = self._current()
        self.position += 1
        return token

    def _skip_trivia(self) -> None:
        while self._current().kind in _TRIVIA:
            self.position += 1

    def _current(self) -> StructuredTextToken:
        return self.tokens[min(self.position, len(self.tokens) - 1)]

    def _diagnostic(
        self,
        code: str,
        message: str,
        span: SourceSpan,
    ) -> None:
        self.diagnostics.append(
            StructuredTextDiagnostic(code=code, message=message, span=span)
        )
