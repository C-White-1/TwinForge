"""CODESYS project planning for neutral CCW ladder models."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re

from twinforge.converters import ConversionDiagnostic, DiagnosticSeverity
from twinforge.model import (
    Controller,
    LadderInstruction,
    LadderOperation,
    LadderParallel,
    LadderRung,
    LadderSeries,
    Program,
    Routine,
    Task,
)


_OPCODES = {
    LadderOperation.NORMALLY_OPEN_CONTACT: "XIC",
    LadderOperation.NORMALLY_CLOSED_CONTACT: "XIO",
    LadderOperation.COIL: "OTE",
    LadderOperation.SET_COIL: "OTL",
    LadderOperation.RESET_COIL: "OTU",
}
_CONDITIONS = {
    LadderOperation.NORMALLY_OPEN_CONTACT,
    LadderOperation.NORMALLY_CLOSED_CONTACT,
}
_OUTPUTS = {
    LadderOperation.COIL,
    LadderOperation.SET_COIL,
    LadderOperation.RESET_COIL,
}
_INVALID_IDENTIFIER = re.compile(r"[^A-Za-z0-9_]")


@dataclass(frozen=True)
class CCWRungCoverage:
    """Target planning outcome for one attributable source rung."""

    program: str
    rung: int | None
    status: str
    reason: str | None = None


@dataclass(frozen=True)
class CodesysCCWProjectPlan:
    """A CODESYS-shaped controller and its auditable planning evidence."""

    controller: Controller
    coverage: tuple[CCWRungCoverage, ...]
    diagnostics: tuple[ConversionDiagnostic, ...]

    @property
    def converted_rung_count(self) -> int:
        return sum(item.status == "converted" for item in self.coverage)

    @property
    def preserved_rung_count(self) -> int:
        return sum(item.status == "preserved" for item in self.coverage)

    @property
    def empty_rung_count(self) -> int:
        """Return source rungs explicitly represented by an empty network."""

        return sum(item.status == "empty" for item in self.coverage)


def plan_ccw_codesys_project(
    source: Controller,
    *,
    task_rate_ms: int = 20,
) -> CodesysCCWProjectPlan:
    """Build a CODESYS application plan without mutating the neutral source."""

    target = Controller(
        name=source.name,
        identity=deepcopy(source.identity),
        source_extensions=deepcopy(source.source_extensions),
    )
    for tag in source.iter_tags():
        target.add_tag(deepcopy(tag))

    plc_program = Program(name="PLC_PRG")
    main = Routine(name="MainRoutine", language="RLL")
    plc_program.add_routine(main)
    coverage: list[CCWRungCoverage] = []
    diagnostics: list[ConversionDiagnostic] = []
    action_names: set[str] = set()

    for source_program in source.iter_programs():
        action_name = _unique_identifier(source_program.name, action_names)
        action_names.add(action_name)
        main.ladder_rungs.append(
            LadderRung(
                number=len(main.ladder_rungs),
                comment=f"Call CCW program {source_program.name}",
                text=f"JSR({action_name},0);",
                source_extensions=deepcopy(source_program.source_extensions),
            )
        )
        action = Routine(
            name=action_name,
            language="RLL",
            metadata={"ccw_source_program": source_program.name},
            source_extensions=deepcopy(source_program.source_extensions),
        )
        for source_routine in source_program.iter_routines():
            for rung in source_routine.ladder_rungs:
                planned, status, reason = _planned_rung(rung)
                action.ladder_rungs.append(planned)
                coverage.append(
                    CCWRungCoverage(
                        program=source_program.name,
                        rung=rung.number,
                        status=status,
                        reason=reason,
                    )
                )
                if status == "preserved":
                    assert reason is not None
                    diagnostics.append(
                        ConversionDiagnostic(
                            severity=DiagnosticSeverity.WARNING,
                            code="ccw_rung_preserved_for_codesys",
                            message=reason,
                            object_name=(f"{source_program.name}/rung/{rung.number}"),
                            raw_value=_evidence_text(rung.network),
                        )
                    )
        plc_program.add_routine(action)

    target.add_program(plc_program)
    target.add_task(
        Task(
            name="MainTask",
            task_type="Periodic",
            rate=task_rate_ms,
            priority=1,
            scheduled_program_names=[plc_program.name],
            scheduled_programs=[plc_program],
        )
    )
    return CodesysCCWProjectPlan(
        controller=target,
        coverage=tuple(coverage),
        diagnostics=tuple(diagnostics),
    )


def _planned_rung(
    rung: LadderRung,
) -> tuple[LadderRung, str, str | None]:
    if rung.network is not None and not rung.network.elements:
        text = "NOP();"
        status = "empty"
        reason = "empty source rung preserved as an intentional no-op"
    else:
        text, reason = _serialize_network(rung.network)
        status = "converted" if reason is None else "preserved"
    if status == "preserved":
        text = f"UNSUPPORTED_CCW({_evidence_text(rung.network)});"
    return (
        LadderRung(
            number=rung.number,
            rung_type=rung.rung_type,
            comment=rung.comment,
            text=text,
            position=rung.position,
            network=rung.network,
            source_sha256=rung.source_sha256,
            source_extensions=deepcopy(rung.source_extensions),
        ),
        status,
        reason,
    )


def _serialize_network(
    network: LadderSeries | None,
) -> tuple[str, str | None]:
    if network is None or not network.elements:
        return "", "CCW rung has no captured executable topology"
    split_index = next(
        (
            index
            for index, element in enumerate(network.elements)
            if isinstance(element, LadderInstruction) and element.operation in _OUTPUTS
        ),
        None,
    )
    if split_index is None:
        return "", "rung has no supported output instruction"
    condition_elements = network.elements[:split_index]
    output_elements = network.elements[split_index:]
    prefix, branches, suffix = _structural_conditions(condition_elements)
    if branches is None:
        if any(isinstance(element, LadderParallel) for element in condition_elements):
            # Any parallel topology outside the single flat-branch shape above
            # (a second parallel group in series, a non-flat prefix/suffix, an
            # empty branch, or a nested parallel) would require duplicating
            # shared conditions across the cross-product of paths, which the
            # architecture doc guarantees TwinForge does not do.
            return (
                "",
                "condition topology is not a single flat parallel section; "
                "converting it would duplicate shared conditions across paths",
            )
        paths, reason = _condition_paths(condition_elements)
        if reason is not None:
            return "", reason
        if not paths:
            condition_text = ""
        elif len(paths) == 1:
            condition_text = "".join(paths[0])
        else:
            condition_text = "[" + ",".join("".join(path) for path in paths) + "]"
    else:
        condition_text = (
            "".join(prefix)
            + "["
            + ",".join("".join(branch) for branch in branches)
            + "]"
            + "".join(suffix)
        )
    outputs: list[str] = []
    for element in output_elements:
        if not isinstance(element, LadderInstruction):
            return "", "parallel topology appears after an output instruction"
        if element.operation not in _OUTPUTS:
            return "", "condition or unsupported operation appears after an output"
        rendered, reason = _instruction_text(element)
        if reason is not None:
            return "", reason
        outputs.append(rendered)
    return condition_text + "".join(outputs) + ";", None


def _structural_conditions(
    elements: tuple[LadderInstruction | LadderParallel, ...],
) -> tuple[list[str], list[list[str]] | None, list[str]]:
    """Retain one flat parallel section with its common prefix and suffix."""

    parallel_indexes = [
        index
        for index, element in enumerate(elements)
        if isinstance(element, LadderParallel)
    ]
    if len(parallel_indexes) != 1:
        return [], None, []
    parallel_index = parallel_indexes[0]
    parallel = elements[parallel_index]
    assert isinstance(parallel, LadderParallel)
    if len(parallel.branches) < 2:
        return [], None, []
    prefix = _flat_condition_text(elements[:parallel_index])
    suffix = _flat_condition_text(elements[parallel_index + 1 :])
    if prefix is None or suffix is None:
        return [], None, []
    branches: list[list[str]] = []
    for branch in parallel.branches:
        branch_text = _flat_condition_text(branch.elements)
        if branch_text is None or not branch_text:
            return [], None, []
        branches.append(branch_text)
    return prefix, branches, suffix


def _flat_condition_text(
    elements: tuple[LadderInstruction | LadderParallel, ...],
) -> list[str] | None:
    rendered: list[str] = []
    for element in elements:
        if not isinstance(element, LadderInstruction):
            return None
        if element.operation not in _CONDITIONS:
            return None
        text, reason = _instruction_text(element)
        if reason is not None:
            return None
        rendered.append(text)
    return rendered


def _condition_paths(
    elements: tuple[LadderInstruction | LadderParallel, ...],
) -> tuple[list[list[str]], str | None]:
    """Expand recursive condition topology into equivalent parallel paths."""

    paths: list[list[str]] = [[]]
    for element in elements:
        alternatives: list[list[str]] = []
        if isinstance(element, LadderInstruction):
            if element.operation not in _CONDITIONS:
                return [], "non-condition instruction appears before an output"
            rendered, reason = _instruction_text(element)
            if reason is not None:
                return [], reason
            alternatives.append([rendered])
        else:
            if len(element.branches) < 2:
                return [], "parallel topology contains fewer than two branches"
            for branch in element.branches:
                branch_paths, reason = _condition_paths(branch.elements)
                if reason is not None:
                    return [], reason
                alternatives.extend(branch_paths)
        paths = [
            [*prefix, *alternative] for prefix in paths for alternative in alternatives
        ]
        if len(paths) > 256:
            return [], "parallel normalization exceeds the 256-path safety limit"
    return paths, None


def _instruction_text(
    instruction: LadderInstruction,
) -> tuple[str, str | None]:
    if not instruction.operand:
        return "", f"instruction {instruction.source_mnemonic} has no operand"
    try:
        opcode = _OPCODES[instruction.operation]
    except KeyError:
        return "", f"operation {instruction.operation.value} is unsupported"
    return f"{opcode}({instruction.operand})", None


def _evidence_text(network: LadderSeries | None) -> str:
    if network is None:
        return "missing-network"
    values: list[str] = []
    for element in network.elements:
        if isinstance(element, LadderInstruction):
            operand = f"({element.operand})" if element.operand else ""
            values.append(f"{element.source_mnemonic}{operand}")
        else:
            branches = ",".join(_evidence_text(branch) for branch in element.branches)
            values.append(f"[{branches}]")
    return "".join(values)


def _unique_identifier(name: str, existing: set[str]) -> str:
    candidate = _INVALID_IDENTIFIER.sub("_", name).strip("_") or "CCWProgram"
    if candidate[0].isdigit():
        candidate = f"P_{candidate}"
    base = candidate
    suffix = 2
    while candidate in existing or candidate in {"MainRoutine", "PLC_PRG"}:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate
