"""Limited lexical classification profile, not a full IEC expression grammar.

Unsupported expressions remain unresolved. Recognition does not evaluate or
type-check literals, convert memory addresses, or infer expression dependencies.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ExpressionSpec:
    # A name may also start with digits (real corpus evidence: KKS-coded tags
    # such as "00BBA01GS001", the power-plant equipment identification
    # standard), as long as it contains at least one letter/underscore
    # somewhere -- a token that is purely digits is a numeric literal or a
    # bit-select index, never a name, and must keep failing this pattern so
    # those two stay unambiguous.
    identifier: str = r"[A-Za-z_][A-Za-z_0-9]*|[0-9]+[A-Za-z_][A-Za-z_0-9]*"
    # Lexical shape of a direct/system address such as "%S13" or "%MW200".
    direct_address: str = r"%[A-Za-z]+[0-9]+(?:\.[0-9]+)?"
    literals: tuple[str, ...] = (
        r"TRUE|FALSE",
        r"[+-]?[0-9]+",
        r"[+-]?(?:[0-9]+\.[0-9]*|[0-9]*\.[0-9]+)(?:[Ee][+-]?[0-9]+)?",
        r"(?:2#[01]+|8#[0-7]+|16#[0-9A-F]+)",
        r"'[^'\r\n$]*'",
    )


EXPRESSION_SPEC = ExpressionSpec()
