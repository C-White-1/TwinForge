"""Parse Machine Expert - Basic expression boxes into typed IEC expressions.

The editor's comparison and operation boxes (`[%MW0 > 10]`,
`[%MF1 := %MF2 * 3.0]`) use IEC 61131-3 operator spellings. Grammar, as
observed in every sample and fixture (no function calls occur):

    assignment := operand ":=" sum
    comparison := sum ("=" | "<>" | "<" | ">" | "<=" | ">=") sum
    sum        := term (("+" | "-") term)*
    term       := factor (("*" | "/") factor)*
    factor     := ["-"] number | operand | "(" sum ")"

Operands are typed by address prefix from the ladder spec (Generic Functions
Library Guide EIO0000003289.04). Integer arithmetic and floating-point
arithmetic are separate instruction families in the guide, so a node whose
operands have different types is refused; an integer literal adopts the
type of the other side (written `n.0` in a REAL context). Anything else
raises `ExpressionUnsupported` and the box stays UNSUPPORTED.

Semantic differences recorded, not modelled: on overflow or division by
zero the controller sets %S18 and the result is "not significant"; IEC has
no %S18.
"""
from __future__ import annotations

from collections.abc import Mapping
import re

from twinforge.model import Expression, LadderInstruction, LadderOperation, LadderPosition
from twinforge.model.expression import ARITHMETIC_OPERATORS, ASSIGNMENT_OPERATOR, COMPARISON_OPERATORS
from twinforge.schema.machine_expert_basic.ladder import LADDER_SPEC, LadderSpec

_TOKEN = re.compile(r"\s*(:=|<=|>=|<>|[-+*/()<>=]|\d+\.\d+|\d+|%[A-Za-z]+\d+(?:\.\d+)*(?:[.:][A-Za-z]\w*)?)")
_INTEGER_RANGES = {"INT": (-32768, 32767), "DINT": (-2147483648, 2147483647)}


class ExpressionUnsupported(Exception):
    """The expression is outside the evidenced grammar or cannot be typed."""


def parse_expression(text: str, symbols: Mapping[str, str] | None = None,
                     spec: LadderSpec = LADDER_SPEC) -> Expression:
    """Parse one box: an assignment (root `:=`) or a comparison (root BOOL)."""
    tokens = _tokenize(text)
    parser = _Parser(tokens, symbols or {}, spec)
    if len(tokens) > 1 and tokens[1] == ASSIGNMENT_OPERATOR:
        target = parser.operand()
        parser.expect(ASSIGNMENT_OPERATOR)
        value = _adopt(parser.sum(), target.data_type)
        parser.end()
        if value.data_type != target.data_type:
            raise ExpressionUnsupported(f"assigns {value.data_type} to {target.data_type} {target.text}")
        return Expression("binary", target.data_type, operator=ASSIGNMENT_OPERATOR, left=target, right=value)
    left = parser.sum()
    operator = parser.peek()
    if operator not in COMPARISON_OPERATORS:
        raise ExpressionUnsupported(f"expected a comparison or assignment, found {operator or 'end of text'!r}")
    parser.take()
    right = parser.sum()
    parser.end()
    left, right = _unify(left, right, operator)
    return Expression("binary", "BOOL", operator=operator, left=left, right=right)


def _tokenize(text: str) -> list[str]:
    tokens, position = [], 0
    text = text.strip()
    while position < len(text):
        match = _TOKEN.match(text, position)
        if match is None:
            raise ExpressionUnsupported(f"cannot read {text[position:]!r}")
        tokens.append(match.group(1))
        position = match.end()
    return tokens


def _adopt(node: Expression, data_type: str) -> Expression:
    """An untyped integer literal takes the type of its context."""
    if node.kind != "literal" or node.data_type != "ANY_INT":
        return node
    if data_type == "REAL":
        return Expression("literal", "REAL", text=f"{node.text}.0")
    bounds = _INTEGER_RANGES.get(data_type)
    if bounds is None or not bounds[0] <= int(node.text) <= bounds[1]:
        raise ExpressionUnsupported(f"literal {node.text} does not fit {data_type}")
    return Expression("literal", data_type, text=node.text)


def _unify(left: Expression, right: Expression, operator: str) -> tuple[Expression, Expression]:
    if left.data_type == "ANY_INT" and right.data_type == "ANY_INT":
        left, right = _adopt(left, "INT"), _adopt(right, "INT")
    elif left.data_type == "ANY_INT":
        left = _adopt(left, right.data_type)
    elif right.data_type == "ANY_INT":
        right = _adopt(right, left.data_type)
    if left.data_type != right.data_type:
        raise ExpressionUnsupported(f"{left.data_type} {operator} {right.data_type} mixes types")
    return left, right


class _Parser:
    def __init__(self, tokens: list[str], symbols: Mapping[str, str], spec: LadderSpec):
        self.tokens, self.position, self.symbols, self.spec = tokens, 0, symbols, spec

    def peek(self) -> str | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def take(self) -> str:
        token = self.peek()
        if token is None:
            raise ExpressionUnsupported("expression ends early")
        self.position += 1
        return token

    def expect(self, token: str) -> None:
        if self.take() != token:
            raise ExpressionUnsupported(f"expected {token!r}")

    def end(self) -> None:
        if self.peek() is not None:
            raise ExpressionUnsupported(f"unexpected {self.peek()!r}")

    def sum(self) -> Expression:
        node = self.term()
        while self.peek() in ("+", "-"):
            node = self.binary(self.take(), node, self.term())
        return node

    def term(self) -> Expression:
        node = self.factor()
        while self.peek() in ("*", "/"):
            node = self.binary(self.take(), node, self.factor())
        return node

    def binary(self, operator: str, left: Expression, right: Expression) -> Expression:
        assert operator in ARITHMETIC_OPERATORS
        left, right = _unify(left, right, operator)
        return Expression("binary", left.data_type, operator=operator, left=left, right=right)

    def factor(self) -> Expression:
        token = self.peek()
        if token == "(":
            self.take()
            node = self.sum()
            self.expect(")")
            return node
        if token == "-":
            self.take()
            number = self.take()
            if not re.fullmatch(r"\d+(\.\d+)?", number):
                raise ExpressionUnsupported("unary minus is only supported on a literal")
            return self.literal("-" + number)
        if token is not None and re.fullmatch(r"\d+(\.\d+)?", token):
            return self.literal(self.take())
        return self.operand()

    @staticmethod
    def literal(text: str) -> Expression:
        # An integer literal stays ANY_INT until its context types it.
        return Expression("literal", "REAL" if "." in text else "ANY_INT", text=text)

    def operand(self) -> Expression:
        token = self.take()
        if not token.startswith("%"):
            raise ExpressionUnsupported(f"expected an operand, found {token!r}")
        address = token.upper()
        if re.search(r"[.:][A-Z]", address):
            raise ExpressionUnsupported(f"{token} reads a member or bit, which is not converted")
        types = self.spec.expression_operand_types
        prefix = re.match(r"%[A-Z]+", address)
        assert prefix is not None
        data_type = types.get(prefix.group(0))
        if data_type is None:
            raise ExpressionUnsupported(f"{token} has no documented numeric type")
        symbol = self.symbols.get(address)
        return Expression("variable", data_type, text=symbol or address, address=address if symbol else None)


def expression_instruction(text: str, mnemonic: str, symbols: Mapping[str, str] | None = None,
                           position: LadderPosition | None = None, spec: LadderSpec = LADDER_SPEC) -> LadderInstruction:
    """The ladder instruction for one expression box.

    COMPARISON (a condition) or ASSIGNMENT (passes power on) when the text
    parses and types; otherwise UNSUPPORTED with the reason. The original
    text is kept as a `source_expression=` annotation either way.
    """
    source = ("source_expression=" + re.sub(r"\s+", " ", text.strip()),)
    try:
        expression = parse_expression(text, symbols, spec)
    except ExpressionUnsupported as error:
        return LadderInstruction(operation=LadderOperation.UNSUPPORTED, source_mnemonic=mnemonic,
                                 operand=re.sub(r"\s+", " ", text.strip()), annotations=source + (f"reason={error}",),
                                 position=position)
    if expression.operator == ASSIGNMENT_OPERATOR:
        assert expression.left is not None
        target = expression.left
        address = (f"address={target.address}",) if target.address else ()
        return LadderInstruction(operation=LadderOperation.ASSIGNMENT, source_mnemonic=mnemonic,
                                 operand=target.text, annotations=source + address, position=position,
                                 expression=expression)
    return LadderInstruction(operation=LadderOperation.COMPARISON, source_mnemonic=mnemonic,
                             operand=expression.render(), annotations=source, position=position,
                             expression=expression)
