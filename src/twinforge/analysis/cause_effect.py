"""Derive conservative cause-and-effect candidates from observed logic."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256

from .alarm_candidates import (
    AlarmTripCandidateKind,
    AlarmTripCandidateReport,
)
from .tag_dependencies import (
    TagDependencyGraph,
    TagReference,
    TagReferenceAccess,
    UnresolvedTagReference,
)


@dataclass(frozen=True)
class CauseEvidence:
    """One resolved tag read at the same source location as an effect write."""

    relationship_key: str
    tag_key: str
    tag_name: str
    member_path: str | None
    instruction: str
    operand: str
    review_status: str = "unreviewed"
    polarity: str | None = None
    voting: str | None = None
    delay: str | None = None
    operating_modes: str | None = None
    shutdown_action: str | None = None


@dataclass(frozen=True)
class UnresolvedCauseEvidence:
    """One unresolved operand retained at an effect's source location."""

    relationship_key: str
    identifier: str
    instruction: str
    operand: str
    review_status: str = "unreviewed"
    polarity: str | None = None
    voting: str | None = None
    delay: str | None = None
    operating_modes: str | None = None
    shutdown_action: str | None = None


@dataclass(frozen=True)
class CauseEffectReviewProvenance:
    """Attribution for a separately supplied engineering review overlay."""

    reviewed_by: str
    reviewed_at: datetime
    authority_reference: str
    source_reference: str
    applied_relationship_keys: tuple[str, ...]


@dataclass(frozen=True)
class CauseEffectCandidate:
    """Observed co-location evidence requiring engineering validation."""

    effect_tag_key: str
    effect_tag_name: str
    effect_kinds: tuple[AlarmTripCandidateKind, ...]
    program_name: str
    routine_name: str
    rung_number: int | None
    line_number: int | None
    writer_instruction: str
    causes: tuple[CauseEvidence, ...]
    unresolved_causes: tuple[UnresolvedCauseEvidence, ...]
    evidence_basis: str = "same_logic_location"
    causal_relationship_verified: bool = False


@dataclass(frozen=True)
class CauseEffectCandidateReport:
    """Deterministic candidate relationships and their evidence boundary."""

    controller_name: str
    candidates: tuple[CauseEffectCandidate, ...]
    review: CauseEffectReviewProvenance | None = None


def build_cause_effect_candidate_report(
    alarms: AlarmTripCandidateReport,
    graph: TagDependencyGraph,
) -> CauseEffectCandidateReport:
    """Join alarm/trip writes to reads observed at exactly the same location."""
    kinds_by_key = {item.tag_key: item.kinds for item in alarms.candidates}
    candidates: list[CauseEffectCandidate] = []
    for writer in graph.references:
        kinds = kinds_by_key.get(writer.tag_key)
        if kinds is None or writer.access not in {
            TagReferenceAccess.WRITE,
            TagReferenceAccess.READ_WRITE,
        }:
            continue
        causes = tuple(
            _cause(item, writer)
            for item in graph.references
            if _same_location(item, writer)
            and item.tag_key != writer.tag_key
            and item.access in {
                TagReferenceAccess.READ,
                TagReferenceAccess.READ_WRITE,
            }
        )
        unresolved = tuple(
            _unresolved_cause(item, writer)
            for item in graph.unresolved_references
            if _same_location(item, writer)
        )
        candidates.append(
            CauseEffectCandidate(
                effect_tag_key=writer.tag_key,
                effect_tag_name=writer.tag_name,
                effect_kinds=kinds,
                program_name=writer.program_name,
                routine_name=writer.routine_name,
                rung_number=writer.rung_number,
                line_number=writer.line_number,
                writer_instruction=writer.instruction,
                causes=tuple(sorted(set(causes), key=_cause_key)),
                unresolved_causes=tuple(
                    sorted(set(unresolved), key=_unresolved_key)
                ),
            )
        )
    return CauseEffectCandidateReport(
        controller_name=alarms.controller_name,
        candidates=tuple(sorted(candidates, key=_candidate_key)),
    )


def cause_effect_candidate_report_data(
    report: CauseEffectCandidateReport,
) -> dict[str, object]:
    """Return deterministic JSON-compatible candidate data."""
    return {
        "controller_name": report.controller_name,
        "review": (
            {
                **asdict(report.review),
                "reviewed_at": report.review.reviewed_at.isoformat(),
            }
            if report.review is not None
            else None
        ),
        "candidates": [
            {
                **asdict(item),
                "effect_kinds": [kind.value for kind in item.effect_kinds],
            }
            for item in report.candidates
        ],
    }


def cause_effect_candidate_report_json(
    report: CauseEffectCandidateReport,
) -> str:
    """Serialize cause-and-effect candidates deterministically."""
    return json.dumps(cause_effect_candidate_report_data(report), indent=2) + "\n"


def _same_location(
    item: TagReference | UnresolvedTagReference,
    writer: TagReference,
) -> bool:
    return (
        item.program_name,
        item.routine_name,
        item.rung_number,
        item.line_number,
    ) == (
        writer.program_name,
        writer.routine_name,
        writer.rung_number,
        writer.line_number,
    )


def _cause(item: TagReference, writer: TagReference) -> CauseEvidence:
    return CauseEvidence(
        relationship_key=_relationship_key(
            writer,
            cause_status="resolved",
            cause_operand=item.operand,
            cause_instruction=item.instruction,
            cause_identity=(item.tag_key, item.member_path),
        ),
        tag_key=item.tag_key,
        tag_name=item.tag_name,
        member_path=item.member_path,
        instruction=item.instruction,
        operand=item.operand,
    )


def _unresolved_cause(
    item: UnresolvedTagReference,
    writer: TagReference,
) -> UnresolvedCauseEvidence:
    return UnresolvedCauseEvidence(
        relationship_key=_relationship_key(
            writer,
            cause_status="unresolved",
            cause_operand=item.operand,
            cause_instruction=item.instruction,
            cause_identity=(item.identifier, None),
        ),
        identifier=item.identifier,
        instruction=item.instruction,
        operand=item.operand,
    )


def _cause_key(item: CauseEvidence) -> tuple[str, ...]:
    return (
        item.tag_key,
        item.member_path or "",
        item.instruction,
        item.operand,
    )


def _unresolved_key(item: UnresolvedCauseEvidence) -> tuple[str, ...]:
    return (item.identifier, item.instruction, item.operand)


def _candidate_key(item: CauseEffectCandidate) -> tuple[object, ...]:
    return (
        item.program_name,
        item.routine_name,
        item.rung_number if item.rung_number is not None else -1,
        item.line_number if item.line_number is not None else -1,
        item.effect_tag_key,
        item.writer_instruction,
    )


def _relationship_key(
    writer: TagReference,
    *,
    cause_status: str,
    cause_operand: str,
    cause_instruction: str,
    cause_identity: tuple[str, str | None],
) -> str:
    """Return a stable opaque identity for one exact matrix relationship."""

    identity = json.dumps(
        {
            "program": writer.program_name,
            "routine": writer.routine_name,
            "rung": writer.rung_number,
            "line": writer.line_number,
            "effect_tag_key": writer.tag_key,
            "write_instruction": writer.instruction,
            "write_operand": writer.operand,
            "cause_status": cause_status,
            "cause_operand": cause_operand,
            "cause_instruction": cause_instruction,
            "cause_identity": cause_identity,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = sha256(identity.encode("utf-8")).hexdigest()[:24]
    return f"ce:{digest}"
