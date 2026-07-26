"""Extract literal assignment evidence from parsed Structured Text."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass

from twinforge.model import Routine, StructuredTextLine
from twinforge.structured_text import (
    AssignmentStatement,
    IndexExpression,
    LiteralExpression,
    parse_structured_text,
)


@dataclass(frozen=True)
class LiteralAssignmentEvidence:
    """One assignment whose right-hand side is an integer literal."""

    routine_name: str
    line_number: int | None
    target: str
    value: int
    indices: tuple[int, ...]
    source_text: str
    comment: str | None = None


def extract_literal_assignments(
    routine: Routine,
) -> tuple[LiteralAssignmentEvidence, ...]:
    """Return integer assignments while retaining exact source locations."""

    source = routine.structured_text
    if not source:
        return ()
    document = parse_structured_text(source)
    evidence: list[LiteralAssignmentEvidence] = []
    for node in _walk(document.statements):
        if not isinstance(node, AssignmentStatement):
            continue
        if not isinstance(node.value, LiteralExpression):
            continue
        value = _integer_literal(node.value.value)
        if value is None:
            continue
        captured_line = _captured_line(routine, node.span.start)
        indices: tuple[int, ...] = ()
        if isinstance(node.target, IndexExpression):
            parsed_indices = tuple(
                _integer_literal(index.value)
                if isinstance(index, LiteralExpression)
                else None
                for index in node.target.indices
            )
            if all(index is not None for index in parsed_indices):
                indices = tuple(
                    index for index in parsed_indices if index is not None
                )
        evidence.append(
            LiteralAssignmentEvidence(
                routine_name=routine.name,
                line_number=captured_line.number
                if captured_line is not None
                else None,
                target=source[node.target.span.start : node.target.span.end],
                value=value,
                indices=indices,
                source_text=source[node.span.start : node.span.end],
                comment=_line_comment(captured_line.text)
                if captured_line is not None
                else None,
            )
        )
    return tuple(evidence)


def _captured_line(
    routine: Routine,
    offset: int,
) -> StructuredTextLine | None:
    """Map a source offset even when one captured Line contains newlines."""

    start = 0
    for line in routine.structured_text_lines:
        end = start + len(line.text)
        if offset <= end:
            return line
        start = end + 1
    return None


def _line_comment(source: str) -> str | None:
    _, marker, comment = source.partition("//")
    if not marker:
        return None
    normalized = comment.strip()
    return normalized or None


def _walk(value: object):
    if isinstance(value, tuple | list):
        for item in value:
            yield from _walk(item)
        return
    if not is_dataclass(value):
        return
    yield value
    for item in fields(value):
        yield from _walk(getattr(value, item.name))


def _integer_literal(value: str) -> int | None:
    lexical = value.replace("_", "")
    try:
        if "#" in lexical:
            radix, digits = lexical.split("#", 1)
            return int(digits, int(radix))
        return int(lexical, 0)
    except ValueError:
        return None
