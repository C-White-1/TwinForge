"""Lossless lexer for IEC Structured Text and observed Logix extensions."""

from __future__ import annotations

from collections.abc import Callable

from .syntax import (
    SourceSpan,
    StructuredTextDiagnostic,
    StructuredTextToken,
    TokenKind,
)


_SINGLE_TOKENS = {
    "(": TokenKind.LEFT_PAREN,
    ")": TokenKind.RIGHT_PAREN,
    "[": TokenKind.LEFT_BRACKET,
    "]": TokenKind.RIGHT_BRACKET,
    ",": TokenKind.COMMA,
    ".": TokenKind.DOT,
    ";": TokenKind.SEMICOLON,
}
_OPERATOR_CHARACTERS = set("+-*/=<>&|^")


def lex_structured_text(
    source: str,
) -> tuple[
    tuple[StructuredTextToken, ...],
    tuple[StructuredTextDiagnostic, ...],
]:
    """Tokenize every character, retaining trivia and unknown input."""

    lexer = _Lexer(source)
    return lexer.lex()


class _Lexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens: list[StructuredTextToken] = []
        self.diagnostics: list[StructuredTextDiagnostic] = []

    def lex(
        self,
    ) -> tuple[
        tuple[StructuredTextToken, ...],
        tuple[StructuredTextDiagnostic, ...],
    ]:
        while self.position < len(self.source):
            self._next_token()
        self.tokens.append(
            StructuredTextToken(
                kind=TokenKind.END_OF_FILE,
                text="",
                span=SourceSpan(self.position, self.position),
                line=self.line,
                column=self.column,
            )
        )
        return tuple(self.tokens), tuple(self.diagnostics)

    def _next_token(self) -> None:
        character = self.source[self.position]
        if character.isspace():
            self._consume_while(str.isspace, TokenKind.WHITESPACE)
        elif self._starts_with("//"):
            self._line_comment()
        elif self._starts_with("/*"):
            self._block_comment("/*", "*/")
        elif self._starts_with("(*"):
            self._block_comment("(*", "*)")
        elif character == "'":
            self._string()
        elif character.isalpha() or character == "_":
            self._word_or_typed_literal()
        elif character.isdigit():
            self._numeric_literal()
        elif self._starts_with(":="):
            self._fixed(2, TokenKind.ASSIGN)
        elif self._starts_with("=>"):
            self._fixed(2, TokenKind.OUTPUT_ASSIGN)
        elif character in _SINGLE_TOKENS:
            self._fixed(1, _SINGLE_TOKENS[character])
        elif character in _OPERATOR_CHARACTERS:
            self._operator()
        else:
            start = self.position
            self._fixed(1, TokenKind.UNKNOWN)
            self.diagnostics.append(
                StructuredTextDiagnostic(
                    code="unknown_character",
                    message=f"unknown character {character!r}",
                    span=SourceSpan(start, self.position),
                )
            )

    def _consume_while(
        self,
        predicate: Callable[[str], bool],
        kind: TokenKind,
    ) -> None:
        start, line, column = self.position, self.line, self.column
        while self.position < len(self.source) and predicate(
            self.source[self.position]
        ):
            self._advance()
        self._append(kind, start, line, column)

    def _line_comment(self) -> None:
        start, line, column = self.position, self.line, self.column
        while self.position < len(self.source):
            character = self.source[self.position]
            self._advance()
            if character == "\n":
                break
        self._append(TokenKind.COMMENT, start, line, column)

    def _block_comment(self, opening: str, closing: str) -> None:
        start, line, column = self.position, self.line, self.column
        for _ in opening:
            self._advance()
        while self.position < len(self.source) and not self._starts_with(
            closing
        ):
            self._advance()
        if self._starts_with(closing):
            for _ in closing:
                self._advance()
        else:
            self.diagnostics.append(
                StructuredTextDiagnostic(
                    code="unterminated_comment",
                    message="unterminated block comment",
                    span=SourceSpan(start, self.position),
                )
            )
        self._append(TokenKind.COMMENT, start, line, column)

    def _string(self) -> None:
        start, line, column = self.position, self.line, self.column
        self._advance()
        terminated = False
        while self.position < len(self.source):
            if self._starts_with("''"):
                self._advance()
                self._advance()
            elif self.source[self.position] == "'":
                self._advance()
                terminated = True
                break
            else:
                self._advance()
        if not terminated:
            self.diagnostics.append(
                StructuredTextDiagnostic(
                    code="unterminated_string",
                    message="unterminated string literal",
                    span=SourceSpan(start, self.position),
                )
            )
        self._append(TokenKind.STRING, start, line, column)

    def _word_or_typed_literal(self) -> None:
        start, line, column = self.position, self.line, self.column
        while self.position < len(self.source) and (
            self.source[self.position].isalnum()
            or self.source[self.position] == "_"
        ):
            self._advance()
        kind = TokenKind.IDENTIFIER
        if self.position < len(self.source) and self.source[self.position] == "#":
            kind = TokenKind.LITERAL
            self._advance()
            self._consume_literal_tail()
        self._append(kind, start, line, column)

    def _numeric_literal(self) -> None:
        start, line, column = self.position, self.line, self.column
        self._consume_literal_tail()
        self._append(TokenKind.LITERAL, start, line, column)

    def _consume_literal_tail(self) -> None:
        while self.position < len(self.source):
            character = self.source[self.position]
            if character.isalnum() or character in "_#:":
                self._advance()
            elif (
                character in "+-."
                and self.position + 1 < len(self.source)
                and self.source[self.position + 1].isdigit()
            ):
                self._advance()
            else:
                break

    def _operator(self) -> None:
        start, line, column = self.position, self.line, self.column
        first = self.source[self.position]
        self._advance()
        if (
            self.position < len(self.source)
            and self.source[self.position] == "="
            and first in "<>="
        ):
            self._advance()
        elif (
            first == "<"
            and self.position < len(self.source)
            and self.source[self.position] == ">"
        ):
            self._advance()
        self._append(TokenKind.OPERATOR, start, line, column)

    def _fixed(self, length: int, kind: TokenKind) -> None:
        start, line, column = self.position, self.line, self.column
        for _ in range(length):
            self._advance()
        self._append(kind, start, line, column)

    def _append(
        self,
        kind: TokenKind,
        start: int,
        line: int,
        column: int,
    ) -> None:
        self.tokens.append(
            StructuredTextToken(
                kind=kind,
                text=self.source[start : self.position],
                span=SourceSpan(start, self.position),
                line=line,
                column=column,
            )
        )

    def _starts_with(self, value: str) -> bool:
        return self.source.startswith(value, self.position)

    def _advance(self) -> None:
        character = self.source[self.position]
        self.position += 1
        if character == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
