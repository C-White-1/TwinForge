import xml.etree.ElementTree as ET

import pytest

from twinforge.exporters.plcopen_instructions import (
    ConditionInstruction,
    OutputEmission,
    OutputInstruction,
    PLCopenInstructionRegistry,
)


def test_condition_registry_dispatches_complete_instruction_context() -> None:
    received: list[ConditionInstruction] = []

    def emit(instruction: ConditionInstruction) -> int:
        received.append(instruction)
        return 42

    registry = PLCopenInstructionRegistry(
        condition_emitters={"XIC": emit},
        output_emitters={},
    )
    instruction = ConditionInstruction(
        ld=ET.Element("LD"),
        opcode="XIC",
        operand="Enable",
        condition_ids=(1, 2),
        auxiliary="evidence",
    )

    assert registry.emit_condition(instruction) == 42
    assert received == [instruction]


def test_output_registry_preserves_explicit_continuation_state() -> None:
    received: list[OutputInstruction] = []

    def emit(instruction: OutputInstruction) -> OutputEmission:
        received.append(instruction)
        return OutputEmission((99,), True)

    registry = PLCopenInstructionRegistry(
        condition_emitters={},
        output_emitters={"ADD": emit},
    )
    instruction = OutputInstruction(
        ld=ET.Element("LD"),
        opcode="ADD",
        operand="Source,1,Destination",
        execution_ids=(7,),
        input_from_block=False,
    )

    assert registry.emit_output(instruction) == OutputEmission((99,), True)
    assert received == [instruction]


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("condition", "no PLCopen condition emitter for UNKNOWN"),
        ("output", "no PLCopen output emitter for UNKNOWN"),
    ],
)
def test_unregistered_opcode_fails_explicitly(
    kind: str,
    expected: str,
) -> None:
    registry = PLCopenInstructionRegistry(
        condition_emitters={},
        output_emitters={},
    )

    with pytest.raises(ValueError, match=expected):
        if kind == "condition":
            registry.emit_condition(
                ConditionInstruction(
                    ld=ET.Element("LD"),
                    opcode="UNKNOWN",
                    operand="Value",
                    condition_ids=(1,),
                )
            )
        else:
            registry.emit_output(
                OutputInstruction(
                    ld=ET.Element("LD"),
                    opcode="UNKNOWN",
                    operand="Value",
                    execution_ids=(1,),
                    input_from_block=False,
                )
            )
