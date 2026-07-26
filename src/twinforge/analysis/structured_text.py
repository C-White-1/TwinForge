"""Read-only Structured Text parse coverage over the neutral controller model."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from twinforge.model import Controller, Routine
from twinforge.structured_text import (
    IfStatement,
    Statement,
    StructuredTextDiagnostic,
    StructuredTextDocument,
    UnsupportedStatement,
    WhileStatement,
    parse_structured_text,
)


@dataclass(frozen=True)
class StructuredTextRoutineFinding:
    """Parse result and preservation evidence for one ST routine."""

    owner: str
    routine: str
    document: StructuredTextDocument
    statement_count: int
    unsupported_statement_count: int

    @property
    def source_preserved(self) -> bool:
        """Return whether the token stream reconstructs the captured source."""

        return (
            self.document.reconstructed_source == self.document.source
        )

    @property
    def diagnostics(self) -> tuple[StructuredTextDiagnostic, ...]:
        """Return lexical and syntactic diagnostics."""

        return self.document.diagnostics


@dataclass(frozen=True)
class StructuredTextAnalysisReport:
    """Controller-wide ST parse coverage."""

    controller_name: str
    routines: tuple[StructuredTextRoutineFinding, ...]

    @property
    def total_statements(self) -> int:
        return sum(item.statement_count for item in self.routines)

    @property
    def unsupported_statements(self) -> int:
        return sum(
            item.unsupported_statement_count for item in self.routines
        )

    @property
    def all_source_preserved(self) -> bool:
        return all(item.source_preserved for item in self.routines)

    def render_text(self) -> str:
        """Render deterministic parse coverage and diagnostics."""

        lines = [
            f"Structured Text analysis: {self.controller_name}",
            f"Routines: {len(self.routines)}",
            f"Statements: {self.total_statements}",
            f"Unsupported statements: {self.unsupported_statements}",
            "All source preserved: "
            f"{'yes' if self.all_source_preserved else 'no'}",
        ]
        for finding in self.routines:
            lines.extend(
                [
                    "",
                    f"Routine: {finding.owner}/{finding.routine}",
                    f"  Statements: {finding.statement_count}",
                    "  Unsupported statements: "
                    f"{finding.unsupported_statement_count}",
                    "  Source preserved: "
                    f"{'yes' if finding.source_preserved else 'no'}",
                    f"  Diagnostics: {len(finding.diagnostics)}",
                ]
            )
            for diagnostic in finding.diagnostics:
                lines.append(
                    f"    - {diagnostic.code} "
                    f"[{diagnostic.span.start}:{diagnostic.span.end}]: "
                    f"{diagnostic.message}"
                )
        return "\n".join(lines) + "\n"


def analyze_structured_text(
    controller: Controller,
) -> StructuredTextAnalysisReport:
    """Parse every captured ST routine without mutating model source."""

    findings: list[StructuredTextRoutineFinding] = []
    for instruction in sorted(
        controller.add_on_instructions.values(),
        key=lambda item: item.name.casefold(),
    ):
        findings.extend(
            _routine_findings(
                f"AOI:{instruction.name}",
                instruction.iter_routines(),
            )
        )
    for program in sorted(
        controller.iter_programs(),
        key=lambda item: item.name.casefold(),
    ):
        findings.extend(
            _routine_findings(
                f"Program:{program.name}",
                program.iter_routines(),
            )
        )
    return StructuredTextAnalysisReport(
        controller_name=controller.name,
        routines=tuple(findings),
    )


def _routine_findings(
    owner: str,
    routines: Iterable[Routine],
) -> list[StructuredTextRoutineFinding]:
    findings: list[StructuredTextRoutineFinding] = []
    for routine in sorted(
        routines,
        key=lambda item: item.name.casefold(),
    ):
        if not _is_structured_text(routine):
            continue
        document = parse_structured_text(routine.structured_text)
        statement_count, unsupported_count = _statement_counts(
            document.statements
        )
        findings.append(
            StructuredTextRoutineFinding(
                owner=owner,
                routine=routine.name,
                document=document,
                statement_count=statement_count,
                unsupported_statement_count=unsupported_count,
            )
        )
    return findings


def _is_structured_text(routine: Routine) -> bool:
    return (routine.language or "").casefold() in {
        "st",
        "structuredtext",
    }


def _statement_counts(
    statements: tuple[Statement, ...],
) -> tuple[int, int]:
    total = 0
    unsupported = 0
    for statement in statements:
        total += 1
        unsupported += isinstance(statement, UnsupportedStatement)
        if isinstance(statement, IfStatement):
            for branch in statement.branches:
                branch_total, branch_unsupported = _statement_counts(
                    branch.statements
                )
                total += branch_total
                unsupported += branch_unsupported
            else_total, else_unsupported = _statement_counts(
                statement.else_statements
            )
            total += else_total
            unsupported += else_unsupported
        elif isinstance(statement, WhileStatement):
            body_total, body_unsupported = _statement_counts(
                statement.statements
            )
            total += body_total
            unsupported += body_unsupported
    return total, unsupported
