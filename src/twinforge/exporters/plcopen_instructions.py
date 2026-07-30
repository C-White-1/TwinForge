"""Typed dispatch for PLCopen ladder instruction emitters."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import xml.etree.ElementTree as ET

from .plcopen_operands import PLCopenOneShotExport


@dataclass(frozen=True)
class ConditionInstruction:
    """One condition instruction and its incoming graph connections."""

    ld: ET.Element
    opcode: str
    operand: str
    condition_ids: tuple[int, ...]
    auxiliary: object | None = None


@dataclass(frozen=True)
class OutputInstruction:
    """One output instruction and its current execution-chain state."""

    ld: ET.Element
    opcode: str
    operand: str
    execution_ids: tuple[int, ...]
    input_from_block: bool


@dataclass(frozen=True)
class OutputEmission:
    """Continuation state returned after emitting an output instruction."""

    execution_ids: tuple[int, ...]
    execution_from_block: bool


ConditionEmitter = Callable[[ConditionInstruction], int]
OutputEmitter = Callable[[OutputInstruction], OutputEmission]
ContactEmitter = Callable[[ET.Element, str, str, list[int]], int]
ComparisonEmitter = Callable[
    [ET.Element, str, str, list[int], str],
    int,
]
OneShotEmitter = Callable[
    [ET.Element, PLCopenOneShotExport, list[int]],
    int,
]
CoilEmitter = Callable[..., int]
TimerEmitter = Callable[[ET.Element, str, list[int]], int]
TimerResetEmitter = Callable[..., int]
ValueEmitter = Callable[..., int]


class PLCopenInstructionRegistry:
    """Resolve supported opcodes to focused condition and output emitters."""

    def __init__(
        self,
        *,
        condition_emitters: Mapping[str, ConditionEmitter],
        output_emitters: Mapping[str, OutputEmitter],
    ) -> None:
        self._condition_emitters = dict(condition_emitters)
        self._output_emitters = dict(output_emitters)

    def emit_condition(self, instruction: ConditionInstruction) -> int:
        """Emit a condition or raise for an unregistered opcode."""

        try:
            emitter = self._condition_emitters[instruction.opcode]
        except KeyError as error:
            raise ValueError(
                f"no PLCopen condition emitter for {instruction.opcode}"
            ) from error
        return emitter(instruction)

    def emit_output(self, instruction: OutputInstruction) -> OutputEmission:
        """Emit an output and return its graph continuation state."""

        try:
            emitter = self._output_emitters[instruction.opcode]
        except KeyError as error:
            raise ValueError(
                f"no PLCopen output emitter for {instruction.opcode}"
            ) from error
        return emitter(instruction)


def build_instruction_registry(
    *,
    comparison_opcodes: frozenset[str],
    value_opcodes: frozenset[str],
    emit_contact: ContactEmitter,
    emit_comparison: ComparisonEmitter,
    emit_oneshot: OneShotEmitter,
    emit_coil: CoilEmitter,
    emit_timer: TimerEmitter,
    emit_timer_reset: TimerResetEmitter,
    emit_value: ValueEmitter,
) -> PLCopenInstructionRegistry:
    """Adapt focused XML emitters to the common typed dispatch contract."""

    def contact(instruction: ConditionInstruction) -> int:
        return emit_contact(
            instruction.ld,
            instruction.opcode,
            instruction.operand,
            list(instruction.condition_ids),
        )

    def comparison(instruction: ConditionInstruction) -> int:
        if not isinstance(instruction.auxiliary, str):
            raise ValueError("comparison emission requires a result variable")
        return emit_comparison(
            instruction.ld,
            instruction.opcode,
            instruction.operand,
            list(instruction.condition_ids),
            instruction.auxiliary,
        )

    def oneshot(instruction: ConditionInstruction) -> int:
        if not isinstance(instruction.auxiliary, PLCopenOneShotExport):
            raise ValueError("ONS emission requires prepared one-shot state")
        return emit_oneshot(
            instruction.ld,
            instruction.auxiliary,
            list(instruction.condition_ids),
        )

    def coil(instruction: OutputInstruction) -> OutputEmission:
        emit_coil(
            instruction.ld,
            instruction.opcode,
            instruction.operand,
            list(instruction.execution_ids),
            formal_parameter=(
                "ENO" if instruction.input_from_block else None
            ),
        )
        return OutputEmission(
            instruction.execution_ids,
            instruction.input_from_block,
        )

    def timer(instruction: OutputInstruction) -> OutputEmission:
        emit_timer(
            instruction.ld,
            instruction.operand,
            list(instruction.execution_ids),
        )
        return OutputEmission(
            instruction.execution_ids,
            instruction.input_from_block,
        )

    def timer_reset(instruction: OutputInstruction) -> OutputEmission:
        local_id = emit_timer_reset(
            instruction.ld,
            instruction.operand,
            list(instruction.execution_ids),
            input_from_block=instruction.input_from_block,
        )
        return OutputEmission((local_id,), True)

    def value(instruction: OutputInstruction) -> OutputEmission:
        local_id = emit_value(
            instruction.ld,
            instruction.opcode,
            instruction.operand,
            list(instruction.execution_ids),
            input_from_block=instruction.input_from_block,
        )
        return OutputEmission((local_id,), True)

    return PLCopenInstructionRegistry(
        condition_emitters={
            "XIC": contact,
            "XIO": contact,
            "ONS": oneshot,
            **{opcode: comparison for opcode in comparison_opcodes},
        },
        output_emitters={
            "OTE": coil,
            "OTL": coil,
            "OTU": coil,
            "TON": timer,
            "RES": timer_reset,
            **{opcode: value for opcode in value_opcodes},
        },
    )
