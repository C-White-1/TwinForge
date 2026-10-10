"""CODESYS project planning for neutral CCW ladder models.

Each CCW program becomes an action of `PLC_PRG`, called from its main
routine. Rungs keep their neutral `LadderRung.network`, which the PLCopen
exporter emits directly as an LD graph; coverage uses the exporter's own
test of what it can emit, so the plan and the export agree.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re

from twinforge.converters import ConversionDiagnostic, DiagnosticSeverity
from twinforge.exporters.plcopen_network import unsupported_reason
from twinforge.model import (
    Controller,
    LadderInstruction,
    LadderRung,
    LadderSeries,
    Program,
    Routine,
    Task,
)


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
    text: str | None = None
    if rung.network is None:
        # Nothing to emit: kept as a marked RLL placeholder so the exporter
        # writes it as an unsupported-rung comment.
        text = f"UNSUPPORTED_CCW({_evidence_text(rung.network)});"
        status, reason = "preserved", "CCW rung has no captured executable topology"
    elif not rung.network.elements:
        text = "NOP();"
        status, reason = "empty", "empty source rung preserved as an intentional no-op"
    else:
        # CCW lowering produces no function block pins, so no instances.
        reason = unsupported_reason(rung.network)
        status = "converted" if reason is None else "preserved"
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
