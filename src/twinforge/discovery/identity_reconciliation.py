"""Compare CIP identities with SNMP physical candidates without merging them."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .contracts import CipIdentityObservation, DiscoverySnapshot
from .snmp_entity_candidates import (
    SnmpPhysicalAssetCandidate,
    SnmpPhysicalCandidateResult,
    correlate_physical_entities,
)
from .topology import TopologyConfidence, TopologyEvidenceReference


@dataclass(frozen=True)
class CipPhysicalReconciliationCandidate:
    """Exact cross-protocol agreements that may identify the same equipment."""

    key: str
    observation_target: str
    physical_asset_key: str
    matched_fields: tuple[str, ...]
    confidence: TopologyConfidence
    evidence: tuple[TopologyEvidenceReference, ...]


@dataclass(frozen=True)
class IdentityReconciliationResult:
    """Candidate matches plus explicitly unmatched observation keys."""

    matches: tuple[CipPhysicalReconciliationCandidate, ...]
    unmatched_cip_targets: tuple[str, ...]
    unmatched_physical_assets: tuple[str, ...]


def _normalise_text(value: str) -> str:
    """Normalise only case and whitespace, not punctuation or model syntax."""
    return " ".join(value.casefold().split())


def _matching_fields(
    identity: CipIdentityObservation,
    physical: SnmpPhysicalAssetCandidate,
) -> tuple[str, ...]:
    matches: list[str] = []
    product = _normalise_text(identity.product_name)
    physical_names = {
        _normalise_text(value)
        for value in (physical.model_name, physical.name, physical.description)
        if value and value.strip()
    }
    if product and product in physical_names:
        matches.append("product_name")

    serial = physical.serial_number
    if serial is not None and re.fullmatch(r"[0-9]+", serial.strip()):
        if serial.strip() == str(identity.serial_number):
            matches.append("serial_number_decimal")
    return tuple(matches)


def _physical_oids(
    physical: SnmpPhysicalAssetCandidate,
    matched_fields: tuple[str, ...],
) -> set[str]:
    columns: set[int] = set()
    if "product_name" in matched_fields:
        columns.update((2, 7, 13))
    if "serial_number_decimal" in matched_fields:
        columns.add(11)
    suffixes = tuple(
        f".{column}.{physical.entity_index}" for column in sorted(columns)
    )
    return {
        item.identifier
        for item in physical.evidence
        if item.identifier.endswith(suffixes)
    }


def _match_evidence(
    identity: CipIdentityObservation,
    physical: SnmpPhysicalAssetCandidate,
    matched_fields: tuple[str, ...],
) -> tuple[TopologyEvidenceReference, ...]:
    evidence = [
        TopologyEvidenceReference(
            protocol="cip_identity",
            observation_target=identity.target.key,
            identifier=f"cip.identity.{field}",
            description="CIP Identity Object field used for exact comparison",
        )
        for field in matched_fields
    ]
    physical_oids = _physical_oids(physical, matched_fields)
    evidence.extend(
        item for item in physical.evidence if item.identifier in physical_oids
    )
    return tuple(
        sorted(
            evidence,
            key=lambda item: (item.protocol, item.identifier),
        )
    )


def reconcile_cip_physical_identities(
    snapshot: DiscoverySnapshot,
    physical_result: SnmpPhysicalCandidateResult | None = None,
) -> IdentityReconciliationResult:
    """Find exact same-target agreements without vendor-specific coercion."""
    physical = physical_result or correlate_physical_entities(snapshot)
    by_target: dict[str, list[SnmpPhysicalAssetCandidate]] = {}
    for asset in physical.assets:
        by_target.setdefault(asset.observation_target, []).append(asset)

    matches: list[CipPhysicalReconciliationCandidate] = []
    matched_cip_targets: set[str] = set()
    matched_physical_assets: set[str] = set()
    for identity in snapshot.identities:
        for asset in by_target.get(identity.target.key, []):
            matched_fields = _matching_fields(identity, asset)
            if not matched_fields:
                continue
            matches.append(
                CipPhysicalReconciliationCandidate(
                    key=f"cip:{identity.target.key}|matches:{asset.key}",
                    observation_target=identity.target.key,
                    physical_asset_key=asset.key,
                    matched_fields=matched_fields,
                    confidence=TopologyConfidence.CORROBORATED,
                    evidence=_match_evidence(identity, asset, matched_fields),
                )
            )
            matched_cip_targets.add(identity.target.key)
            matched_physical_assets.add(asset.key)

    return IdentityReconciliationResult(
        matches=tuple(sorted(matches, key=lambda item: item.key)),
        unmatched_cip_targets=tuple(
            sorted(
                identity.target.key
                for identity in snapshot.identities
                if identity.target.key not in matched_cip_targets
            )
        ),
        unmatched_physical_assets=tuple(
            sorted(
                asset.key
                for asset in physical.assets
                if asset.key not in matched_physical_assets
            )
        ),
    )


def identity_reconciliation_data(
    result: IdentityReconciliationResult,
) -> dict[str, Any]:
    """Return a stable JSON-compatible reconciliation representation."""
    return {
        "matches": [
            {
                "key": item.key,
                "observation_target": item.observation_target,
                "physical_asset_key": item.physical_asset_key,
                "matched_fields": list(item.matched_fields),
                "confidence": item.confidence.value,
                "evidence": [
                    {
                        "protocol": evidence.protocol,
                        "observation_target": evidence.observation_target,
                        "identifier": evidence.identifier,
                        "description": evidence.description,
                    }
                    for evidence in item.evidence
                ],
            }
            for item in result.matches
        ],
        "unmatched_cip_targets": list(result.unmatched_cip_targets),
        "unmatched_physical_assets": list(result.unmatched_physical_assets),
    }


def identity_reconciliation_json(result: IdentityReconciliationResult) -> str:
    """Serialize reconciliation candidates with deterministic formatting."""
    return json.dumps(
        identity_reconciliation_data(result), indent=2, ensure_ascii=False
    ) + "\n"
