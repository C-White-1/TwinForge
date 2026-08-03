"""Parse the currently supported, target-neutral Rockwell RLL subset."""

from __future__ import annotations

import re
from dataclasses import dataclass


COMPARISON_TYPES = {
    "EQU": "EQ",
    "NEQ": "NE",
    "GRT": "GT",
    "GEQ": "GE",
    "LES": "LT",
    "LEQ": "LE",
}
VALUE_BLOCK_TYPES = {
    "MOV": "MOVE",
    "ADD": "ADD",
    "SUB": "SUB",
    "MUL": "MUL",
    "DIV": "DIV",
}
SUPPORTED_RLL_INSTRUCTIONS = frozenset(
    {
        "XIC",
        "XIO",
        "OTE",
        "OTL",
        "OTU",
        *COMPARISON_TYPES,
        "TON",
        "RES",
        *VALUE_BLOCK_TYPES,
        "ONS",
        "JSR",
        "NOP",
    }
)

_RLL_INSTRUCTION = re.compile(
    r"\s*(XIC|XIO|OTE|OTL|OTU|EQU|NEQ|GRT|GEQ|LES|LEQ|TON|TOF|RTO|CTU|CTD|RES|"
    r"MOV|ADD|SUB|MUL|DIV|ONS)\s*\(([^()]*)\)"
)
_JSR_INSTRUCTION = re.compile(r"\s*JSR\s*\(\s*([^,()]+)\s*,\s*0\s*\)\s*;\s*")


@dataclass(frozen=True)
class ParsedBooleanRung:
    """A normalized serial/parallel rung supported by the current emitter."""

    branches: tuple[tuple[tuple[str, str], ...], ...]
    tail_conditions: tuple[tuple[str, str], ...]
    outputs: tuple[tuple[str, str], ...]

    @property
    def instructions(self) -> tuple[tuple[str, str], ...]:
        """Return all instructions in deterministic evaluation order."""

        branch_instructions = tuple(
            instruction for branch in self.branches for instruction in branch
        )
        return branch_instructions + self.tail_conditions + self.outputs


def parse_supported_rung(text: str | None) -> ParsedBooleanRung | None:
    """Parse a rung only when its complete structure is currently supported."""

    if not text:
        return None
    source = text.strip()
    if not source.endswith(";"):
        return None
    source = source[:-1].strip()
    branches: tuple[tuple[tuple[str, str], ...], ...] = ()
    if source.startswith("["):
        closing = _branch_closing_index(source)
        if closing is None:
            return None
        branch_parts = _split_branch_paths(source[1:closing])
        if len(branch_parts) < 2:
            return None
        parsed_branches: list[tuple[tuple[str, str], ...]] = []
        for part in branch_parts:
            branch = _parse_instruction_sequence(part)
            if not branch or any(opcode not in {"XIC", "XIO"} for opcode, _ in branch):
                return None
            parsed_branches.append(tuple(branch))
        branches = tuple(parsed_branches)
        source = source[closing + 1 :].strip()

    instructions = _parse_instruction_sequence(source)
    if not instructions:
        return None
    tail_conditions: list[tuple[str, str]] = []
    outputs: list[tuple[str, str]] = []
    output_seen = False
    output_opcodes = {
        "OTE",
        "OTL",
        "OTU",
        "TON",
        "TOF",
        "RTO",
        "CTU",
        "CTD",
        "RES",
        *VALUE_BLOCK_TYPES,
    }
    for opcode, operand in instructions:
        if opcode in {"XIC", "XIO"} and output_seen:
            return None
        if opcode in output_opcodes:
            output_seen = True
            outputs.append((opcode, operand))
        else:
            tail_conditions.append((opcode, operand))
    if not outputs:
        return None
    return ParsedBooleanRung(
        branches=branches,
        tail_conditions=tuple(tail_conditions),
        outputs=tuple(outputs),
    )


def split_arguments(text: str) -> list[str]:
    """Split the flat argument forms accepted by the supported instruction set."""

    arguments = [argument.strip() for argument in text.split(",")]
    return arguments if all(arguments) else []


def parse_jsr(text: str | None) -> str | None:
    """Return the target routine for the supported ``JSR(routine,0)`` form."""

    if not text:
        return None
    match = _JSR_INSTRUCTION.fullmatch(text)
    return match.group(1).strip() if match is not None else None


def _parse_instruction_sequence(text: str) -> list[tuple[str, str]] | None:
    position = 0
    instructions: list[tuple[str, str]] = []
    while position < len(text):
        match = _RLL_INSTRUCTION.match(text, position)
        if match is None:
            return None
        operand = match.group(2).strip()
        if not operand:
            return None
        opcode = match.group(1)
        if opcode in COMPARISON_TYPES and len(split_arguments(operand)) != 2:
            return None
        if opcode in {"TON", "TOF", "RTO", "CTU", "CTD"} and len(
            split_arguments(operand)
        ) != 3:
            return None
        if opcode in {"RES", "ONS"} and "," in operand:
            return None
        if opcode == "MOV" and len(split_arguments(operand)) != 2:
            return None
        if (
            opcode in {"ADD", "SUB", "MUL", "DIV"}
            and len(split_arguments(operand)) != 3
        ):
            return None
        instructions.append((opcode, operand))
        position = match.end()
    return instructions


def _branch_closing_index(text: str) -> int | None:
    parenthesis_depth = 0
    for index, character in enumerate(text[1:], start=1):
        if character == "(":
            parenthesis_depth += 1
        elif character == ")":
            parenthesis_depth -= 1
        elif character == "[" and parenthesis_depth == 0:
            return None
        elif character == "]" and parenthesis_depth == 0:
            return index
    return None


def _split_branch_paths(text: str) -> list[str]:
    paths: list[str] = []
    start = 0
    parenthesis_depth = 0
    for index, character in enumerate(text):
        if character == "(":
            parenthesis_depth += 1
        elif character == ")":
            parenthesis_depth -= 1
        elif character == "," and parenthesis_depth == 0:
            paths.append(text[start:index].strip())
            start = index + 1
    paths.append(text[start:].strip())
    return paths
