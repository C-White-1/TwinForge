"""Resolve Logix MSG instruction calls to captured MESSAGE tag evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from twinforge.model import Controller, Program, SoftwareCallSite, Tag

from .software_calls import extract_program_calls


@dataclass(frozen=True)
class MessageInstructionEvidence:
    """One MSG call tied to its captured control tag and configuration."""

    call: SoftwareCallSite
    control_operand: str
    control_tag: Tag
    owner: str
    is_cip_generic: bool


@dataclass(frozen=True)
class UnresolvedMessageInstruction:
    """One MSG-shaped call that cannot be bound without inventing evidence."""

    call: SoftwareCallSite
    control_operand: str | None
    reason: str


@dataclass(frozen=True)
class MessageInstructionAnalysis:
    """Resolved and unresolved MSG execution evidence for one controller."""

    resolved: tuple[MessageInstructionEvidence, ...]
    unresolved: tuple[UnresolvedMessageInstruction, ...]


def message_instruction_analysis_data(
    analysis: MessageInstructionAnalysis,
) -> dict[str, Any]:
    """Return deterministic, JSON-compatible MSG execution evidence."""

    return {
        "schema_version": "1.0",
        "resolved": [
            {
                "program": item.call.program_name,
                "routine": item.call.routine_name,
                "language": item.call.language.value,
                "line_number": item.call.line_number,
                "rung_number": item.call.rung_number,
                "source_text": item.call.source_text,
                "control_operand": item.control_operand,
                "control_tag": item.control_tag.name,
                "owner": item.owner,
                "message_type": (
                    item.control_tag.message_configuration.message_type
                    if item.control_tag.message_configuration is not None
                    else None
                ),
                "is_cip_generic": item.is_cip_generic,
            }
            for item in analysis.resolved
        ],
        "unresolved": [
            {
                "program": item.call.program_name,
                "routine": item.call.routine_name,
                "language": item.call.language.value,
                "line_number": item.call.line_number,
                "rung_number": item.call.rung_number,
                "source_text": item.call.source_text,
                "control_operand": item.control_operand,
                "reason": item.reason,
            }
            for item in analysis.unresolved
        ],
    }


def message_instruction_analysis_json(
    analysis: MessageInstructionAnalysis,
) -> str:
    """Serialize the versioned MSG analysis with a final newline."""

    return json.dumps(
        message_instruction_analysis_data(analysis),
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def analyze_message_instructions(
    controller: Controller,
) -> MessageInstructionAnalysis:
    """Resolve MSG operands using Logix program-before-controller scope."""

    resolved: list[MessageInstructionEvidence] = []
    unresolved: list[UnresolvedMessageInstruction] = []
    for program in controller.iter_programs():
        for call in extract_program_calls(program):
            if call.callee.casefold() != "msg":
                continue
            if len(call.arguments) != 1:
                unresolved.append(
                    UnresolvedMessageInstruction(
                        call=call,
                        control_operand=(
                            call.arguments[0].source
                            if call.arguments
                            else None
                        ),
                        reason=(
                            "MSG requires exactly one control-tag operand; "
                            f"captured {len(call.arguments)}"
                        ),
                    )
                )
                continue
            operand = call.arguments[0].source.strip()
            tag, owner = _resolve_tag(controller, program, operand)
            if tag is None:
                unresolved.append(
                    UnresolvedMessageInstruction(
                        call=call,
                        control_operand=operand,
                        reason="control tag is not present in program or controller scope",
                    )
                )
                continue
            if tag.message_configuration is None:
                unresolved.append(
                    UnresolvedMessageInstruction(
                        call=call,
                        control_operand=operand,
                        reason="resolved control tag has no captured MESSAGE configuration",
                    )
                )
                continue
            configuration = tag.message_configuration
            resolved.append(
                MessageInstructionEvidence(
                    call=call,
                    control_operand=operand,
                    control_tag=tag,
                    owner=owner,
                    is_cip_generic=(
                        configuration.service_code is not None
                        or configuration.object_type is not None
                        or (configuration.message_type or "").casefold()
                        == "cip generic"
                    ),
                )
            )
    return MessageInstructionAnalysis(
        resolved=tuple(resolved),
        unresolved=tuple(unresolved),
    )


def _resolve_tag(
    controller: Controller,
    program: Program,
    operand: str,
) -> tuple[Tag | None, str]:
    """Resolve only a simple tag name; member expressions remain unresolved."""

    if not operand or any(character in operand for character in ".[]"):
        return None, ""
    program_tag = program.tags.get(operand)
    if program_tag is not None:
        return program_tag, f"program:{program.name}"
    controller_tag = controller.tags.get(operand)
    if controller_tag is not None:
        return controller_tag, "controller"
    return None, ""
