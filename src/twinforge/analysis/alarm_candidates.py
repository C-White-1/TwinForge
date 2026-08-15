"""Identify explicitly labelled alarm and trip tag candidates."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum

from twinforge.model import Controller, SoftwareTagScope, Tag

from .tag_dependencies import (
    TagDependencyGraph,
    TagReference,
    TagReferenceAccess,
    build_tag_dependency_graph,
)


class AlarmTripCandidateKind(str, Enum):
    """Classification directly supported by a tag name or description."""

    ALARM = "alarm"
    TRIP = "trip"


@dataclass(frozen=True)
class AlarmTripCandidate:
    """One explicitly labelled candidate with software-reference evidence."""

    tag_key: str
    tag_name: str
    tag_scope: SoftwareTagScope
    program_name: str | None
    description: str | None
    kinds: tuple[AlarmTripCandidateKind, ...]
    classification_evidence: tuple[str, ...]
    reader_locations: tuple[str, ...]
    writer_locations: tuple[str, ...]
    alias_source_keys: tuple[str, ...]
    priority: str | None = None
    setpoint: str | None = None
    engineering_unit: str | None = None
    delay: str | None = None
    latching: str | None = None
    acknowledgement: str | None = None
    suppression: str | None = None
    shutdown_action: str | None = None
    applicability: str | None = None


@dataclass(frozen=True)
class AlarmTripReviewProvenance:
    """Authority and scope for explicitly reviewed candidate fields."""

    reviewed_by: str
    reviewed_at: datetime
    authority_reference: str
    source_reference: str
    applied_tag_keys: tuple[str, ...]


@dataclass(frozen=True)
class AlarmTripCandidateReport:
    """Deterministic candidates; absence is not proof of no alarms."""

    controller_name: str
    candidates: tuple[AlarmTripCandidate, ...]
    review: AlarmTripReviewProvenance | None = None


_ALARM_TOKENS = frozenset({"alarm", "alarms", "alm"})
_TRIP_TOKENS = frozenset({"trip", "trips"})


def build_alarm_trip_candidate_report(
    controller: Controller,
    graph: TagDependencyGraph | None = None,
) -> AlarmTripCandidateReport:
    """Select only tags with explicit alarm/trip lexical evidence."""
    dependencies = graph or build_tag_dependency_graph(controller)
    candidates: list[AlarmTripCandidate] = []
    for key, tag, scope, program_name in _tags(controller):
        kinds, evidence = _classification(tag)
        if not kinds:
            continue
        references = tuple(
            item for item in dependencies.references if item.tag_key == key
        )
        candidates.append(
            AlarmTripCandidate(
                tag_key=key,
                tag_name=tag.name,
                tag_scope=scope,
                program_name=program_name,
                description=tag.description,
                kinds=kinds,
                classification_evidence=evidence,
                reader_locations=_locations(
                    references,
                    {TagReferenceAccess.READ, TagReferenceAccess.READ_WRITE},
                ),
                writer_locations=_locations(
                    references,
                    {TagReferenceAccess.WRITE, TagReferenceAccess.READ_WRITE},
                ),
                alias_source_keys=tuple(
                    sorted(
                        {
                            item.source_tag_key
                            for item in references
                            if item.access is TagReferenceAccess.ALIAS
                            and item.source_tag_key is not None
                        }
                    )
                ),
            )
        )
    return AlarmTripCandidateReport(
        controller_name=controller.name,
        candidates=tuple(sorted(candidates, key=lambda item: item.tag_key)),
    )


def _tags(
    controller: Controller,
) -> tuple[tuple[str, Tag, SoftwareTagScope, str | None], ...]:
    items: list[tuple[str, Tag, SoftwareTagScope, str | None]] = [
        (f"controller:{name}", tag, SoftwareTagScope.CONTROLLER, None)
        for name, tag in controller.tags.items()
    ]
    for program in controller.iter_programs():
        items.extend(
            (
                f"program:{program.name}:{name}",
                tag,
                SoftwareTagScope.PROGRAM,
                program.name,
            )
            for name, tag in program.tags.items()
        )
    return tuple(items)


def _classification(
    tag: Tag,
) -> tuple[tuple[AlarmTripCandidateKind, ...], tuple[str, ...]]:
    found: set[AlarmTripCandidateKind] = set()
    evidence: list[str] = []
    for field, value in (("name", tag.name), ("description", tag.description)):
        if not value:
            continue
        tokens = _tokens(value)
        if tokens & _ALARM_TOKENS:
            found.add(AlarmTripCandidateKind.ALARM)
            evidence.append(f"{field} explicitly contains an alarm token")
        if tokens & _TRIP_TOKENS:
            found.add(AlarmTripCandidateKind.TRIP)
            evidence.append(f"{field} explicitly contains a trip token")
    return (
        tuple(sorted(found, key=lambda item: item.value)),
        tuple(evidence),
    )


def _tokens(value: str) -> set[str]:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return {
        token.casefold() for token in re.split(r"[^A-Za-z0-9]+", separated) if token
    }


def _locations(
    references: tuple[TagReference, ...],
    access: set[TagReferenceAccess],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                _location(
                    item.program_name,
                    item.routine_name,
                    item.rung_number,
                    item.line_number,
                )
                for item in references
                if item.access in access
            }
        )
    )


def _location(
    program: str,
    routine: str,
    rung: int | None,
    line: int | None,
) -> str:
    if rung is not None:
        suffix = f"rung {rung}"
    elif line is not None:
        suffix = f"line {line}"
    else:
        suffix = "location unavailable"
    return f"{program}.{routine}: {suffix}"


def alarm_trip_candidate_report_data(
    report: AlarmTripCandidateReport,
) -> dict[str, object]:
    """Return deterministic JSON-compatible candidate report data."""
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
                **item.__dict__,
                "tag_scope": item.tag_scope.value,
                "kinds": [kind.value for kind in item.kinds],
            }
            for item in report.candidates
        ],
    }


def alarm_trip_candidate_report_json(
    report: AlarmTripCandidateReport,
) -> str:
    """Serialize an alarm/trip candidate report deterministically."""
    return json.dumps(alarm_trip_candidate_report_data(report), indent=2) + "\n"
