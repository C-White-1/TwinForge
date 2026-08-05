"""Lower observed ENTITY-MIB rows into reviewable physical candidates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .contracts import DiscoverySnapshot, SnmpPhysicalEntityObservation
from .snmp_entity import validate_entity_containment
from .topology import TopologyConfidence, TopologyEvidenceReference


@dataclass(frozen=True)
class SnmpPhysicalAssetCandidate:
    """A physical asset suggested by one retained ENTITY-MIB row.

    This is deliberately not a core-model asset. Acceptance and reconciliation
    must occur at a later boundary where corroborating evidence can be applied.
    """

    key: str
    observation_target: str
    entity_index: int
    physical_class: int | None
    name: str | None
    description: str | None
    manufacturer_name: str | None
    model_name: str | None
    serial_number: str | None
    asset_id: str | None
    uuid: str | None
    confidence: TopologyConfidence
    evidence: tuple[TopologyEvidenceReference, ...]


@dataclass(frozen=True)
class SnmpPhysicalContainmentCandidate:
    """A valid, protocol-reported parent relationship awaiting acceptance."""

    key: str
    observation_target: str
    parent_asset_key: str
    child_asset_key: str
    parent_relative_position: int | None
    confidence: TopologyConfidence
    evidence: tuple[TopologyEvidenceReference, ...]


@dataclass(frozen=True)
class SnmpPhysicalCandidateIssue:
    """Target-qualified structural finding retained beside candidates."""

    observation_target: str
    code: str
    entity_index: int
    parent_index: int | None
    message: str


@dataclass(frozen=True)
class SnmpPhysicalCandidateResult:
    """Deterministically ordered physical candidates and rejected edges."""

    assets: tuple[SnmpPhysicalAssetCandidate, ...]
    containments: tuple[SnmpPhysicalContainmentCandidate, ...]
    issues: tuple[SnmpPhysicalCandidateIssue, ...]


def _asset_key(target_key: str, entity_index: int) -> str:
    return f"target:{target_key}|entity:{entity_index}"


def _evidence(
    target_key: str,
    entity: SnmpPhysicalEntityObservation,
    *,
    identifiers: set[str] | None = None,
) -> tuple[TopologyEvidenceReference, ...]:
    selected = sorted(identifiers if identifiers is not None else entity.raw_oids)
    return tuple(
        TopologyEvidenceReference(
            protocol="snmp_entity_mib",
            observation_target=target_key,
            identifier=oid,
            description="RFC 6933 entPhysicalTable evidence",
        )
        for oid in selected
    )


def _containment_evidence_oids(
    entity: SnmpPhysicalEntityObservation,
) -> set[str]:
    """Select parent and relative-position columns without guessing values."""
    suffixes = (
        f".4.{entity.index}",
        f".6.{entity.index}",
    )
    return {
        oid for oid in entity.raw_oids if any(oid.endswith(suffix) for suffix in suffixes)
    }


def correlate_physical_entities(
    snapshot: DiscoverySnapshot,
) -> SnmpPhysicalCandidateResult:
    """Create candidates without promoting observations into core assets."""
    assets: list[SnmpPhysicalAssetCandidate] = []
    containments: list[SnmpPhysicalContainmentCandidate] = []
    findings: list[SnmpPhysicalCandidateIssue] = []

    for node in snapshot.snmp_nodes:
        target_key = node.target.key
        entities = {entity.index: entity for entity in node.physical_entities}
        issues = validate_entity_containment(node.physical_entities)
        invalid_children = {issue.entity_index for issue in issues}
        findings.extend(
            SnmpPhysicalCandidateIssue(
                observation_target=target_key,
                code=issue.code,
                entity_index=issue.entity_index,
                parent_index=issue.parent_index,
                message=issue.message,
            )
            for issue in issues
        )

        for entity in node.physical_entities:
            asset_key = _asset_key(target_key, entity.index)
            assets.append(
                SnmpPhysicalAssetCandidate(
                    key=asset_key,
                    observation_target=target_key,
                    entity_index=entity.index,
                    physical_class=entity.physical_class,
                    name=entity.name,
                    description=entity.description,
                    manufacturer_name=entity.manufacturer_name,
                    model_name=entity.model_name,
                    serial_number=entity.serial_number,
                    asset_id=entity.asset_id,
                    uuid=entity.uuid,
                    confidence=TopologyConfidence.PROTOCOL_REPORTED,
                    evidence=_evidence(target_key, entity),
                )
            )
            parent = entity.contained_in
            if parent in {None, 0} or entity.index in invalid_children:
                continue
            if parent not in entities:
                continue
            parent_key = _asset_key(target_key, parent)
            containments.append(
                SnmpPhysicalContainmentCandidate(
                    key=f"{parent_key}|contains:{asset_key}",
                    observation_target=target_key,
                    parent_asset_key=parent_key,
                    child_asset_key=asset_key,
                    parent_relative_position=entity.parent_relative_position,
                    confidence=TopologyConfidence.PROTOCOL_REPORTED,
                    evidence=_evidence(
                        target_key,
                        entity,
                        identifiers=_containment_evidence_oids(entity),
                    ),
                )
            )

    return SnmpPhysicalCandidateResult(
        assets=tuple(sorted(assets, key=lambda item: item.key)),
        containments=tuple(sorted(containments, key=lambda item: item.key)),
        issues=tuple(
            sorted(
                findings,
                key=lambda item: (
                    item.observation_target,
                    item.entity_index,
                    item.code,
                    item.parent_index if item.parent_index is not None else -1,
                ),
            )
        ),
    )


def physical_candidate_data(result: SnmpPhysicalCandidateResult) -> dict[str, Any]:
    """Return a stable JSON-compatible candidate representation."""

    def evidence_data(
        evidence: tuple[TopologyEvidenceReference, ...],
    ) -> list[dict[str, str]]:
        return [
            {
                "protocol": item.protocol,
                "observation_target": item.observation_target,
                "identifier": item.identifier,
                "description": item.description,
            }
            for item in evidence
        ]

    return {
        "assets": [
            {
                "key": item.key,
                "observation_target": item.observation_target,
                "entity_index": item.entity_index,
                "physical_class": item.physical_class,
                "name": item.name,
                "description": item.description,
                "manufacturer_name": item.manufacturer_name,
                "model_name": item.model_name,
                "serial_number": item.serial_number,
                "asset_id": item.asset_id,
                "uuid": item.uuid,
                "confidence": item.confidence.value,
                "evidence": evidence_data(item.evidence),
            }
            for item in result.assets
        ],
        "containments": [
            {
                "key": item.key,
                "observation_target": item.observation_target,
                "parent_asset_key": item.parent_asset_key,
                "child_asset_key": item.child_asset_key,
                "parent_relative_position": item.parent_relative_position,
                "confidence": item.confidence.value,
                "evidence": evidence_data(item.evidence),
            }
            for item in result.containments
        ],
        "issues": [
            {
                "observation_target": item.observation_target,
                "code": item.code,
                "entity_index": item.entity_index,
                "parent_index": item.parent_index,
                "message": item.message,
            }
            for item in result.issues
        ],
    }


def physical_candidate_json(result: SnmpPhysicalCandidateResult) -> str:
    """Serialize physical candidates deterministically with a final newline."""
    return json.dumps(
        physical_candidate_data(result), indent=2, ensure_ascii=False
    ) + "\n"
