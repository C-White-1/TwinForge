from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from twinforge.exporters import (
    PLCOPEN_SUPPORTED_RLL_INSTRUCTIONS,
    PLCopenExporter,
    PLCopenProfile,
)
from twinforge.model import Controller


_MNEMONIC = re.compile(r"[A-Za-z_]\w*")
_BLOCKING_DIAGNOSTICS = {
    "unsupported_rll_rung",
    "unsupported_comparison_operand_type",
    "unsupported_timer_operand",
}


@dataclass(frozen=True)
class InstructionCoverage:
    mnemonic: str
    occurrences: int
    executable_occurrences: int
    supported_mnemonic: bool

    @property
    def occurrence_coverage_percent(self) -> float:
        if self.occurrences == 0:
            return 100.0
        return self.executable_occurrences / self.occurrences * 100


@dataclass(frozen=True)
class RungCoverageIssue:
    program: str
    routine: str
    rung_number: int | None
    reason: str
    text: str
    mnemonics: tuple[str, ...]


@dataclass
class RLLCoverageReport:
    total_rungs: int = 0
    executable_rungs: int = 0
    total_instruction_occurrences: int = 0
    executable_instruction_occurrences: int = 0
    instructions: dict[str, InstructionCoverage] = field(default_factory=dict)
    issues: list[RungCoverageIssue] = field(default_factory=list)

    @property
    def rung_coverage_percent(self) -> float:
        if self.total_rungs == 0:
            return 100.0
        return self.executable_rungs / self.total_rungs * 100

    @property
    def occurrence_coverage_percent(self) -> float:
        if self.total_instruction_occurrences == 0:
            return 100.0
        return (
            self.executable_instruction_occurrences
            / self.total_instruction_occurrences
            * 100
        )


def analyze_rll_coverage(controller: Controller) -> RLLCoverageReport:
    """Measure executable PLCopen coverage for one converted L5X controller."""

    export = PLCopenExporter(PLCopenProfile.CODESYS).export(controller)
    blocked_text = defaultdict(Counter)
    unresolved_targets: Counter[str] = Counter()
    for diagnostic in export.diagnostics:
        if diagnostic.code in _BLOCKING_DIAGNOSTICS and diagnostic.raw_value:
            blocked_text[diagnostic.raw_value][diagnostic.code] += 1
        elif (
            diagnostic.code == "unresolved_jsr_target"
            and diagnostic.raw_value
        ):
            unresolved_targets[diagnostic.raw_value] += 1

    total_by_mnemonic: Counter[str] = Counter()
    executable_by_mnemonic: Counter[str] = Counter()
    report = RLLCoverageReport()
    for program in controller.iter_programs():
        for routine in program.iter_routines():
            for rung in routine.ladder_rungs:
                text = rung.text or ""
                mnemonics = extract_rll_mnemonics(text)
                report.total_rungs += 1
                report.total_instruction_occurrences += len(mnemonics)
                total_by_mnemonic.update(mnemonics)

                reason = _consume_blocking_reason(
                    text, mnemonics, blocked_text, unresolved_targets
                )
                if reason is None:
                    report.executable_rungs += 1
                    report.executable_instruction_occurrences += len(
                        mnemonics
                    )
                    executable_by_mnemonic.update(mnemonics)
                else:
                    report.issues.append(
                        RungCoverageIssue(
                            program=program.name,
                            routine=routine.name,
                            rung_number=rung.number,
                            reason=reason,
                            text=text,
                            mnemonics=mnemonics,
                        )
                    )

    report.instructions = {
        mnemonic: InstructionCoverage(
            mnemonic=mnemonic,
            occurrences=count,
            executable_occurrences=executable_by_mnemonic[mnemonic],
            supported_mnemonic=(
                mnemonic in PLCOPEN_SUPPORTED_RLL_INSTRUCTIONS
            ),
        )
        for mnemonic, count in sorted(total_by_mnemonic.items())
    }
    return report


def extract_rll_mnemonics(text: str) -> tuple[str, ...]:
    """Extract top-level RLL instruction names without counting nested calls."""

    mnemonics: list[str] = []
    position = 0
    while position < len(text):
        match = _MNEMONIC.search(text, position)
        if match is None:
            break
        cursor = match.end()
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if cursor >= len(text) or text[cursor] != "(":
            position = match.end()
            continue
        closing = _closing_parenthesis(text, cursor)
        if closing is None:
            position = cursor + 1
            continue
        mnemonics.append(match.group().upper())
        position = closing + 1
    return tuple(mnemonics)


def _closing_parenthesis(text: str, opening: int) -> int | None:
    depth = 0
    for index in range(opening, len(text)):
        character = text[index]
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return index
    return None


def _consume_blocking_reason(
    text: str,
    mnemonics: tuple[str, ...],
    blocked_text: dict[str, Counter[str]],
    unresolved_targets: Counter[str],
) -> str | None:
    reasons = blocked_text.get(text)
    if reasons:
        for reason in sorted(reasons):
            if reasons[reason] > 0:
                reasons[reason] -= 1
                return reason
    if "JSR" in mnemonics:
        for target in unresolved_targets:
            if unresolved_targets[target] > 0 and target in text:
                unresolved_targets[target] -= 1
                return "unresolved_jsr_target"
    return None
