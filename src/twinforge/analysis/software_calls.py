"""Extract source-neutral software call evidence from controller routines."""

from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from pathlib import Path

from twinforge.model import (
    Program,
    Routine,
    SoftwareCallArgument,
    SoftwareCallLanguage,
    SoftwareCallSite,
)
from twinforge.structured_text import CallExpression, parse_structured_text


def extract_program_calls(
    program: Program,
    *,
    source_path: Path | None = None,
) -> tuple[SoftwareCallSite, ...]:
    """Extract calls from all supported routine bodies without resolving them."""

    calls: list[SoftwareCallSite] = []
    for routine in program.iter_routines():
        calls.extend(_structured_text_calls(program, routine))
        calls.extend(_ladder_calls(program, routine))
    if source_path is not None:
        calls = [replace(call, source_path=source_path) for call in calls]
    return tuple(calls)


def _structured_text_calls(
    program: Program,
    routine: Routine,
) -> list[SoftwareCallSite]:
    source = routine.structured_text
    if not source:
        return []
    document = parse_structured_text(source)
    calls: list[SoftwareCallSite] = []
    for node in _walk(document.statements):
        if not isinstance(node, CallExpression):
            continue
        callee = source[node.callee.span.start : node.callee.span.end]
        arguments = tuple(
            SoftwareCallArgument(
                position=index,
                source=source[argument.value.span.start : argument.value.span.end],
                name=argument.name,
                direction=argument.direction,
            )
            for index, argument in enumerate(node.arguments)
        )
        physical_line = source.count("\n", 0, node.span.start)
        captured_line = routine.structured_text_lines[physical_line]
        calls.append(
            SoftwareCallSite(
                callee=callee,
                arguments=arguments,
                program_name=program.name,
                routine_name=routine.name,
                language=SoftwareCallLanguage.STRUCTURED_TEXT,
                source_text=source[node.span.start : node.span.end],
                line_number=captured_line.number,
            )
        )
    return calls


def _walk(value: object):
    """Yield dataclass syntax nodes recursively while ignoring scalar fields."""

    if isinstance(value, tuple | list):
        for item in value:
            yield from _walk(item)
        return
    if not is_dataclass(value):
        return
    yield value
    for item in fields(value):
        yield from _walk(getattr(value, item.name))


def _ladder_calls(
    program: Program,
    routine: Routine,
) -> list[SoftwareCallSite]:
    calls: list[SoftwareCallSite] = []
    for rung in routine.ladder_rungs:
        if not rung.text:
            continue
        for callee, arguments, source_text in _scan_calls(rung.text):
            calls.append(
                SoftwareCallSite(
                    callee=callee,
                    arguments=tuple(
                        SoftwareCallArgument(index, argument)
                        for index, argument in enumerate(arguments)
                    ),
                    program_name=program.name,
                    routine_name=routine.name,
                    language=SoftwareCallLanguage.LADDER,
                    source_text=source_text,
                    rung_number=rung.number,
                )
            )
    return calls


def _scan_calls(source: str) -> list[tuple[str, tuple[str, ...], str]]:
    """Find identifier calls with balanced operands in Logix rung text."""

    calls: list[tuple[str, tuple[str, ...], str]] = []
    index = 0
    while index < len(source):
        if not (source[index].isalpha() or source[index] == "_"):
            index += 1
            continue
        start = index
        while index < len(source) and (
            source[index].isalnum() or source[index] in "_.$:"
        ):
            index += 1
        callee = source[start:index]
        open_index = index
        while open_index < len(source) and source[open_index].isspace():
            open_index += 1
        if open_index >= len(source) or source[open_index] != "(":
            continue
        close_index = _matching_parenthesis(source, open_index)
        if close_index is None:
            index = open_index + 1
            continue
        operand_source = source[open_index + 1 : close_index]
        calls.append(
            (
                callee,
                _split_operands(operand_source),
                source[start : close_index + 1],
            )
        )
        index = close_index + 1
    return calls


def _matching_parenthesis(source: str, start: int) -> int | None:
    depth = 0
    quote: str | None = None
    for index in range(start, len(source)):
        character = source[index]
        if quote is not None:
            if character == quote:
                quote = None
            continue
        if character in "\"'":
            quote = character
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return index
    return None


def _split_operands(source: str) -> tuple[str, ...]:
    if not source.strip():
        return ()
    operands: list[str] = []
    start = 0
    depths = {"(": 0, "[": 0, "{": 0}
    closing = {")": "(", "]": "[", "}": "{"}
    quote: str | None = None
    for index, character in enumerate(source):
        if quote is not None:
            if character == quote:
                quote = None
            continue
        if character in "\"'":
            quote = character
        elif character in depths:
            depths[character] += 1
        elif character in closing:
            opener = closing[character]
            depths[opener] = max(0, depths[opener] - 1)
        elif character == "," and not any(depths.values()):
            operands.append(source[start:index].strip())
            start = index + 1
    operands.append(source[start:].strip())
    return tuple(operands)
