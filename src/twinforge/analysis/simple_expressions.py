"""Resolve a single evidenced binary operator between two independently proven operands.

Deliberately narrow (Tier 1 of the corpus survey behind this module): exactly
one recognized comparison or arithmetic operator (=, <>, <, >, <=, >=, +, -,
*, /), with both operands each classifying the same way a standalone
expression would -- a literal, a declared symbol, or a proven member path.
Nothing here evaluates a truth value, computes an arithmetic result, or
checks type compatibility; resolving a BinaryExpression is structural
evidence only, exactly like resolving a MemberPath.

Explicitly out of scope, left unresolved on purpose:
- Multiple operators in one expression (e.g. "Reset or GQC=65535") -- real
  IEC 61131-3 operator precedence (comparisons bind tighter than AND, which
  binds tighter than OR) would be needed, and is not evidenced as a single,
  simple rule the way the FBD execution order was.
- The word-form logical operators AND/OR/XOR/NOT themselves.
- Function/EF calls used inline as an expression (e.g. "RE(Sim_W505_STOP)",
  "ADDMX (IN := '...')") -- a different problem (call-site parameter
  binding), not an operator grammar.
- Any expression containing a string literal, to avoid ever splitting inside
  quoted text.
"""
from __future__ import annotations

import re
from typing import Any

from twinforge.analysis.member_paths import resolve_member_path
from twinforge.model import AddOnInstructionParameter, BinaryExpression, ExpressionOperand, Tag

# Longest first so "<=" / ">=" / "<>" are not mistaken for "<" / ">". The bare
# "=" excludes ":=" (a parameter-assignment token inside a call, not a
# comparison) via a negative lookbehind.
_OPERATORS = ("<>", "<=", ">=", "<", ">", "*", "/", "+", "-")
_OPERATOR_PATTERN = re.compile("|".join(re.escape(op) for op in _OPERATORS) + r"|(?<!:)=(?!=)")


def split_binary_expression(expression: str) -> tuple[str, str, str] | None:
    """(left, operator, right) for exactly one recognized operator, or None.

    Requires non-empty operands on both sides (so a leading sign, e.g. "-3",
    is never mistaken for an operator with an empty left side -- such a token
    is a signed literal already handled elsewhere before this is ever tried).
    Never splits an expression containing a string literal.
    """
    if "'" in expression:
        return None
    matches = list(_OPERATOR_PATTERN.finditer(expression))
    if len(matches) != 1:
        return None
    match = matches[0]
    left, right = expression[:match.start()].strip(), expression[match.end():].strip()
    if not left or not right:
        return None
    return left, match.group(0), right


def _classify_operand(
    text: str, symbols: dict[str, Tag | AddOnInstructionParameter], ambiguous: set[str],
    identifier_pattern: str, literal_patterns: tuple[str, ...], member_paths: Any,
) -> ExpressionOperand | None:
    if any(re.fullmatch(pattern, text, re.IGNORECASE) for pattern in literal_patterns):
        return ExpressionOperand(text, "literal")
    if re.fullmatch(identifier_pattern, text):
        key = text.casefold()
        if key in ambiguous or key not in symbols:
            return None
        target = symbols[key]
        if isinstance(target, Tag):
            return ExpressionOperand(text, "declared_symbol", target_tag=target)
        return ExpressionOperand(text, "declared_symbol", target_parameter=target)
    if member_paths is None:
        return None
    base_match = re.match(identifier_pattern, text)
    base_key = base_match.group(0).casefold() if base_match else ""
    base_symbol = None if base_key in ambiguous else symbols.get(base_key)
    result = resolve_member_path(
        text, base_symbol, identifier=identifier_pattern, array_pattern=member_paths.array_pattern,
        datatypes=member_paths.datatypes, function_blocks=member_paths.function_blocks,
        library_interfaces=member_paths.library_interfaces,
    )
    if result.status != "resolved":
        return None
    if isinstance(base_symbol, Tag):
        return ExpressionOperand(text, "declared_member_path", target_tag=base_symbol, member_path=result.path)
    return ExpressionOperand(
        text, "declared_member_path", target_parameter=base_symbol, member_path=result.path)


def resolve_binary_expression(
    expression: str, symbols: dict[str, Tag | AddOnInstructionParameter], ambiguous: set[str],
    identifier_pattern: str, literal_patterns: tuple[str, ...], member_paths: Any,
) -> BinaryExpression | None:
    split = split_binary_expression(expression)
    if split is None:
        return None
    left_text, operator, right_text = split
    left = _classify_operand(left_text, symbols, ambiguous, identifier_pattern, literal_patterns, member_paths)
    if left is None:
        return None
    right = _classify_operand(right_text, symbols, ambiguous, identifier_pattern, literal_patterns, member_paths)
    if right is None:
        return None
    return BinaryExpression(operator, left, right)
