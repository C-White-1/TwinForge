"""Evidence-backed drift detection with explicit capture completeness."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .contracts import DiscoverySnapshot
from .routed_capture import CipRoutedDiscoverySnapshot
from .software_inventory_capture import CipSoftwareInventoryObservation
from .topology import TopologyCorrelationResult, TopologyEvidenceReference


class DriftDomain(str, Enum):
    """Independent evidence domains that must be captured explicitly."""

    HARDWARE = "hardware"
    FIRMWARE = "firmware"
    CONFIGURATION = "configuration"
    NETWORK = "network"


class DriftChangeType(str, Enum):
    """Set-level change between two complete domain captures."""

    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"


DriftValue = str | int | bool | None


@dataclass(frozen=True)
class DriftRecord:
    """Normalized evidence record whose attributes remain inspectable."""

    domain: DriftDomain
    key: str
    attributes: tuple[tuple[str, DriftValue], ...]
    evidence: tuple[TopologyEvidenceReference, ...]


@dataclass(frozen=True)
class DiscoveryDriftState:
    """One time-qualified state with explicit domain completeness."""

    captured_at: datetime
    complete_domains: tuple[DriftDomain, ...]
    records: tuple[DriftRecord, ...]

    def __post_init__(self) -> None:
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must include a timezone")
        if len(self.complete_domains) != len(set(self.complete_domains)):
            raise ValueError("complete drift domains must be unique")
        if tuple(sorted(self.complete_domains, key=lambda item: item.value)) != (
            self.complete_domains
        ):
            raise ValueError("complete drift domains must be sorted")
        keys = [(item.domain, item.key) for item in self.records]
        if len(keys) != len(set(keys)):
            raise ValueError("drift record keys must be unique within a domain")
        if any(item.domain not in self.complete_domains for item in self.records):
            raise ValueError("drift records require a complete captured domain")


@dataclass(frozen=True)
class DriftFinding:
    """One attributable difference between comparable states."""

    domain: DriftDomain
    key: str
    change_type: DriftChangeType
    before: DriftRecord | None
    after: DriftRecord | None


@dataclass(frozen=True)
class DiscoveryDriftResult:
    """Findings plus domains withheld because either capture was incomplete."""

    baseline_captured_at: datetime
    current_captured_at: datetime
    compared_domains: tuple[DriftDomain, ...]
    skipped_domains: tuple[DriftDomain, ...]
    findings: tuple[DriftFinding, ...]


def build_discovery_drift_state(
    *,
    captured_at: datetime,
    complete_domains: tuple[DriftDomain, ...],
    snapshot: DiscoverySnapshot | None = None,
    routed: CipRoutedDiscoverySnapshot | None = None,
    software: tuple[CipSoftwareInventoryObservation, ...] = (),
    topology: TopologyCorrelationResult | None = None,
) -> DiscoveryDriftState:
    """Normalize only evidence supplied for explicitly complete domains."""
    complete = set(complete_domains)
    if (
        {DriftDomain.HARDWARE, DriftDomain.FIRMWARE} & complete
        and snapshot is None
        and routed is None
    ):
        raise ValueError(
            "hardware and firmware completeness require identity or routed evidence"
        )
    if DriftDomain.CONFIGURATION in complete and not software:
        raise ValueError("configuration completeness requires software observations")
    if DriftDomain.NETWORK in complete and topology is None:
        raise ValueError("network completeness requires topology evidence")

    records: list[DriftRecord] = []
    if snapshot is not None:
        for identity in snapshot.identities:
            evidence = (
                TopologyEvidenceReference(
                    protocol="cip_identity",
                    observation_target=identity.target.key,
                    identifier="cip.identity",
                    description="CIP Identity Object observation",
                ),
            )
            if DriftDomain.HARDWARE in complete:
                records.append(
                    _record(
                        DriftDomain.HARDWARE,
                        f"cip:{identity.target.key}",
                        {
                            "vendor_id": identity.vendor_id,
                            "device_type": identity.device_type,
                            "product_code": identity.product_code,
                            "serial_number": identity.serial_number,
                            "product_name": identity.product_name,
                        },
                        evidence,
                    )
                )
            if DriftDomain.FIRMWARE in complete:
                records.append(
                    _record(
                        DriftDomain.FIRMWARE,
                        f"cip:{identity.target.key}",
                        {
                            "major_revision": identity.major_revision,
                            "minor_revision": identity.minor_revision,
                        },
                        evidence,
                    )
                )
    if routed is not None:
        for chassis in routed.chassis:
            route_key = chassis.plan.route.key
            for slot in chassis.slots:
                identity = slot.identity
                evidence = (
                    TopologyEvidenceReference(
                        protocol="cip_routed_slot",
                        observation_target=chassis.plan.route.gateway.key,
                        identifier=f"{route_key}|slot:{slot.slot}",
                        description="bounded routed chassis-slot observation",
                    ),
                )
                key = f"cip-slot:{route_key}|slot:{slot.slot}"
                if DriftDomain.HARDWARE in complete:
                    records.append(
                        _record(
                            DriftDomain.HARDWARE,
                            key,
                            {
                                "state": slot.state.value,
                                "vendor_id": identity.vendor_id if identity else None,
                                "device_type": identity.device_type if identity else None,
                                "product_code": identity.product_code if identity else None,
                                "serial_number": identity.serial_number if identity else None,
                                "product_name": identity.product_name if identity else None,
                            },
                            evidence,
                        )
                    )
                if DriftDomain.FIRMWARE in complete and identity is not None:
                    records.append(
                        _record(
                            DriftDomain.FIRMWARE,
                            key,
                            {
                                "major_revision": identity.major_revision,
                                "minor_revision": identity.minor_revision,
                            },
                            evidence,
                        )
                    )
    if DriftDomain.CONFIGURATION in complete:
        for observation in software:
            route_key = observation.route.key
            for item in observation.items:
                records.append(
                    _record(
                        DriftDomain.CONFIGURATION,
                        (
                            f"software:{route_key}|{item.capability.value}"
                            f"|{item.parent or ''}|{item.name}"
                        ),
                        {
                            "instance_id": item.instance_id,
                            "data_type": item.data_type,
                            "language": item.language,
                        },
                        (
                            TopologyEvidenceReference(
                                protocol="cip_software_inventory",
                                observation_target=observation.target.key,
                                identifier=(
                                    f"{item.capability.value}:{item.parent or ''}:{item.name}"
                                ),
                                description="structural controller software metadata",
                            ),
                        ),
                    )
                )
    if DriftDomain.NETWORK in complete and topology is not None:
        for item in topology.relationships:
            records.append(
                _record(
                    DriftDomain.NETWORK,
                    item.key,
                    {
                        "relationship_type": item.relationship_type.value,
                        "evidence_class": item.evidence_class.value,
                        "source_node_key": item.source_node_key,
                        "target_node_key": item.target_node_key,
                        "source_interface_index": item.source_interface_index,
                        "source_port_number": item.source_port_number,
                        "target_port_id": item.target_port_id,
                        "confidence": item.confidence.value,
                    },
                    item.evidence,
                )
            )
    return DiscoveryDriftState(
        captured_at=captured_at,
        complete_domains=tuple(sorted(complete, key=lambda item: item.value)),
        records=tuple(sorted(records, key=lambda item: (item.domain.value, item.key))),
    )


def detect_discovery_drift(
    baseline: DiscoveryDriftState,
    current: DiscoveryDriftState,
) -> DiscoveryDriftResult:
    """Compare only domains explicitly complete in both evidence states."""
    comparable = set(baseline.complete_domains) & set(current.complete_domains)
    all_domains = set(DriftDomain)
    before = {
        (item.domain, item.key): item
        for item in baseline.records
        if item.domain in comparable
    }
    after = {
        (item.domain, item.key): item
        for item in current.records
        if item.domain in comparable
    }
    findings: list[DriftFinding] = []
    for domain, key in sorted(set(before) | set(after), key=lambda item: (item[0].value, item[1])):
        old = before.get((domain, key))
        new = after.get((domain, key))
        if old is None:
            change = DriftChangeType.ADDED
        elif new is None:
            change = DriftChangeType.REMOVED
        elif old.attributes != new.attributes:
            change = DriftChangeType.CHANGED
        else:
            continue
        findings.append(DriftFinding(domain, key, change, old, new))
    return DiscoveryDriftResult(
        baseline_captured_at=baseline.captured_at,
        current_captured_at=current.captured_at,
        compared_domains=tuple(sorted(comparable, key=lambda item: item.value)),
        skipped_domains=tuple(sorted(all_domains - comparable, key=lambda item: item.value)),
        findings=tuple(findings),
    )


def _record(
    domain: DriftDomain,
    key: str,
    attributes: dict[str, DriftValue],
    evidence: tuple[TopologyEvidenceReference, ...],
) -> DriftRecord:
    return DriftRecord(
        domain=domain,
        key=key,
        attributes=tuple(sorted(attributes.items())),
        evidence=evidence,
    )


def discovery_drift_data(result: DiscoveryDriftResult) -> dict[str, Any]:
    """Return deterministic JSON-compatible drift findings."""
    def record(item: DriftRecord | None) -> dict[str, Any] | None:
        if item is None:
            return None
        return {
            "domain": item.domain.value,
            "key": item.key,
            "attributes": dict(item.attributes),
            "evidence": [evidence.__dict__ for evidence in item.evidence],
        }

    return {
        "baseline_captured_at": result.baseline_captured_at.isoformat(),
        "current_captured_at": result.current_captured_at.isoformat(),
        "compared_domains": [item.value for item in result.compared_domains],
        "skipped_domains": [item.value for item in result.skipped_domains],
        "findings": [
            {
                "domain": item.domain.value,
                "key": item.key,
                "change_type": item.change_type.value,
                "before": record(item.before),
                "after": record(item.after),
            }
            for item in result.findings
        ],
    }


def discovery_drift_json(result: DiscoveryDriftResult) -> str:
    """Serialize drift findings deterministically with a final newline."""
    return json.dumps(discovery_drift_data(result), indent=2, ensure_ascii=False) + "\n"
