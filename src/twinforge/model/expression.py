"""Typed IEC 61131-3 scalar expressions, as carried by ladder instructions."""

from __future__ import annotations

from dataclasses import dataclass

# IEC 61131-3 operator spellings.
ARITHMETIC_OPERATORS = frozenset({"+", "-", "*", "/"})
COMPARISON_OPERATORS = frozenset({"=", "<>", "<", ">", "<=", ">="})
ASSIGNMENT_OPERATOR = ":="
# IEC 61131-3 bit-shift functions, as `call` nodes: shift or rotate `left`
# by the literal bit count `right`.
SHIFT_FUNCTIONS = frozenset({"SHL", "SHR", "ROL", "ROR"})


@dataclass(frozen=True)
class Expression:
    """One node of a typed scalar expression tree.

    - `kind == "literal"`: `text` is the IEC lexical value (`10`, `3.0`).
    - `kind == "variable"`: `text` is a declared variable name, or the raw
      source address when the object has no name (`%MW0`); `address` keeps
      the source address when `text` is a symbol.
    - `kind == "binary"`: `operator` applied to `left` and `right`. An
      arithmetic operator yields its operands' type, a comparison yields
      BOOL, and `:=` (the root of an assignment) has the target's type with
      the target as `left`.
    - `kind == "call"`: the IEC function `operator` (one of
      `SHIFT_FUNCTIONS`) applied to `left`, with the literal bit count as
      `right`. It has the type of `left` (INT or DINT): the shift acts on its
      bit pattern, as the source instruction does on a word or double word.

    `data_type` is the IEC elementary type (INT, DINT, REAL, BOOL). Every node
    of a tree a producer emits is typed; anything it cannot type is not
    turned into an Expression at all.
    """

    kind: str
    data_type: str
    text: str = ""
    operator: str | None = None
    left: Expression | None = None
    right: Expression | None = None
    address: str | None = None

    def iter_nodes(self):
        """This node and every node below it, depth first, left to right."""
        yield self
        for child in (self.left, self.right):
            if child is not None:
                yield from child.iter_nodes()

    def render(self) -> str:
        """IEC Structured Text for this node, fully parenthesised below the root."""
        if self.kind not in ("binary", "call"):
            return self.text
        assert self.left is not None and self.right is not None
        left, right = self.left.render(), self.right.render()
        if self.kind == "call":
            return f"{self.operator}({left}, {right})"
        if self.left.kind == "binary":
            left = f"({left})"
        if self.right.kind == "binary":
            right = f"({right})"
        return f"{left} {self.operator} {right}"
