"""Vendor-neutral syntax objects for a lossless Structured Text front end."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TokenKind(str, Enum):
    """Lexical categories retained by the Structured Text document."""

    WHITESPACE = "whitespace"
    COMMENT = "comment"
    IDENTIFIER = "identifier"
    LITERAL = "literal"
    STRING = "string"
    ASSIGN = "assign"
    OUTPUT_ASSIGN = "output_assign"
    OPERATOR = "operator"
    LEFT_PAREN = "left_paren"
    RIGHT_PAREN = "right_paren"
    LEFT_BRACKET = "left_bracket"
    RIGHT_BRACKET = "right_bracket"
    COMMA = "comma"
    DOT = "dot"
    SEMICOLON = "semicolon"
    UNKNOWN = "unknown"
    END_OF_FILE = "end_of_file"


@dataclass(frozen=True)
class SourceSpan:
    """Half-open character range in the original source."""

    start: int
    end: int


@dataclass(frozen=True)
class StructuredTextToken:
    """One token with exact source text and starting location."""

    kind: TokenKind
    text: str
    span: SourceSpan
    line: int
    column: int


@dataclass(frozen=True)
class StructuredTextDiagnostic:
    """A recoverable lexical or syntactic issue."""

    code: str
    message: str
    span: SourceSpan


@dataclass(frozen=True)
class Expression:
    """Base expression node."""

    span: SourceSpan


@dataclass(frozen=True)
class MissingExpression(Expression):
    """An intentionally empty expression, such as an omitted call argument."""


@dataclass(frozen=True)
class NameExpression(Expression):
    """Identifier reference."""

    name: str


@dataclass(frozen=True)
class LiteralExpression(Expression):
    """Numeric, typed, Boolean, or string literal."""

    value: str


@dataclass(frozen=True)
class UnaryExpression(Expression):
    """Prefix operator expression."""

    operator: str
    operand: Expression


@dataclass(frozen=True)
class BinaryExpression(Expression):
    """Binary operator expression."""

    left: Expression
    operator: str
    right: Expression


@dataclass(frozen=True)
class MemberExpression(Expression):
    """Named or numeric member selection."""

    target: Expression
    member: str


@dataclass(frozen=True)
class IndexExpression(Expression):
    """Array indexing operation."""

    target: Expression
    indices: tuple[Expression, ...]
    operator: str = "[]"


@dataclass(frozen=True)
class CallArgument:
    """Positional or named call argument."""

    span: SourceSpan
    value: Expression
    name: str | None = None
    direction: str | None = None


@dataclass(frozen=True)
class CallExpression(Expression):
    """Function, function-block, or source-instruction call."""

    callee: Expression
    arguments: tuple[CallArgument, ...]


@dataclass(frozen=True)
class ParenthesizedExpression(Expression):
    """Explicitly parenthesized expression."""

    expression: Expression


@dataclass(frozen=True)
class Statement:
    """Base statement node."""

    span: SourceSpan


@dataclass(frozen=True)
class AssignmentStatement(Statement):
    """Assignment with a source-specific assignment operator."""

    target: Expression
    operator: str
    value: Expression


@dataclass(frozen=True)
class ExpressionStatement(Statement):
    """Expression evaluated as a statement, normally a call."""

    expression: Expression


@dataclass(frozen=True)
class ExitStatement(Statement):
    """EXIT statement for terminating the innermost loop."""


@dataclass(frozen=True)
class IfBranch:
    """Condition and statements for IF or ELSIF."""

    span: SourceSpan
    condition: Expression
    statements: tuple[Statement, ...]


@dataclass(frozen=True)
class IfStatement(Statement):
    """IF/ELSIF/ELSE statement."""

    branches: tuple[IfBranch, ...]
    else_statements: tuple[Statement, ...]


@dataclass(frozen=True)
class WhileStatement(Statement):
    """WHILE/DO loop."""

    condition: Expression
    statements: tuple[Statement, ...]


@dataclass(frozen=True)
class UnsupportedStatement(Statement):
    """Source range retained after a recoverable parse failure."""

    text: str


@dataclass(frozen=True)
class StructuredTextDocument:
    """Original source, complete token stream, syntax tree, and diagnostics."""

    source: str
    tokens: tuple[StructuredTextToken, ...]
    statements: tuple[Statement, ...]
    diagnostics: tuple[StructuredTextDiagnostic, ...]

    @property
    def reconstructed_source(self) -> str:
        """Reconstruct source exactly from all non-sentinel tokens."""

        return "".join(
            token.text
            for token in self.tokens
            if token.kind is not TokenKind.END_OF_FILE
        )
