"""Compare configured module evidence with discovered CIP identities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from twinforge.model import Identity, Module

from .chassis import CipChassisSlotObservation, CipSlotState
from .contracts import CipIdentityObservation, DiscoverySnapshot
from .electronic_key_evaluation import (
    ElectronicKeyEvaluation,
    electronic_key_evaluation_data,
    evaluate_electronic_key,
)
from .routed_capture import CipRoutedDiscoverySnapshot
from .identity_reconciliation import (
    IdentityReconciliationResult,
    reconcile_cip_physical_identities,
)
from .topology import TopologyConfidence, TopologyEvidenceReference


class ConfiguredModuleComparisonStatus(str, Enum):
    """Outcome of exact comparable-field checks, without keying inference."""

    EXACT = "exact"
    PARTIAL = "partial"
    CONFLICT = "conflict"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class ConfiguredModuleBinding:
    """Explicit operator or source binding from a module to a target."""

    key: str
    target_key: str
    module: Module


@dataclass(frozen=True)
class ConfiguredModuleReconciliationCandidate:
    """One configured/discovered comparison awaiting operator acceptance."""

    key: str
    configured_module_key: str
    target_key: str
    status: ConfiguredModuleComparisonStatus
    matched_fields: tuple[str, ...]
    conflicting_fields: tuple[str, ...]
    unavailable_fields: tuple[str, ...]
    electronic_key_mode: str | None
    physical_asset_keys: tuple[str, ...]
    confidence: TopologyConfidence
    evidence: tuple[TopologyEvidenceReference, ...]
    electronic_key_evaluation: ElectronicKeyEvaluation | None = None


@dataclass(frozen=True)
class ConfiguredModuleReconciliationResult:
    """Deterministic comparisons and bindings lacking a CIP observation."""

    candidates: tuple[ConfiguredModuleReconciliationCandidate, ...]
    targets_without_cip_identity: tuple[str, ...]


@dataclass(frozen=True)
class RoutedConfiguredModuleBinding:
    """Explicit L5X module binding to one routed chassis slot."""

    key: str
    chassis_route_key: str
    slot: int
    module: Module

    def __post_init__(self) -> None:
        if not self.key or self.key != self.key.strip():
            raise ValueError("binding key must be non-empty and trimmed")
        if (
            not self.chassis_route_key
            or self.chassis_route_key != self.chassis_route_key.strip()
        ):
            raise ValueError("chassis route key must be non-empty and trimmed")
        if isinstance(self.slot, bool) or self.slot < 0:
            raise ValueError("binding slot must be a non-negative integer")


@dataclass(frozen=True)
class RoutedConfiguredModuleIssue:
    """A binding or populated observation that could not be compared."""

    key: str
    reason: str
    chassis_route_key: str
    slot: int


@dataclass(frozen=True)
class RoutedConfiguredModuleReconciliationResult:
    """Slot-aware comparisons plus all unresolved routed evidence."""

    candidates: tuple[ConfiguredModuleReconciliationCandidate, ...]
    issues: tuple[RoutedConfiguredModuleIssue, ...]


def _configured_values(identity: Identity) -> dict[str, int]:
    values: dict[str, int] = {}
    if identity.vendor is not None:
        values["vendor_id"] = identity.vendor.id
    if identity.product_type is not None:
        values["device_type"] = identity.product_type
    if identity.product_code is not None:
        values["product_code"] = identity.product_code
    if identity.revision is not None:
        values["major_revision"] = identity.revision.major
        values["minor_revision"] = identity.revision.minor
    return values


def _discovered_values(identity: CipIdentityObservation) -> dict[str, int]:
    return {
        "vendor_id": identity.vendor_id,
        "device_type": identity.device_type,
        "product_code": identity.product_code,
        "major_revision": identity.major_revision,
        "minor_revision": identity.minor_revision,
    }


def _compare_identity(
    configured: Identity,
    discovered: CipIdentityObservation,
    *,
    prefix: str,
) -> tuple[list[str], list[str], list[str]]:
    configured_values = _configured_values(configured)
    discovered_values = _discovered_values(discovered)
    matched: list[str] = []
    conflicting: list[str] = []
    unavailable: list[str] = []
    for field in discovered_values:
        qualified = f"{prefix}.{field}"
        if field not in configured_values:
            unavailable.append(qualified)
        elif configured_values[field] == discovered_values[field]:
            matched.append(qualified)
        else:
            conflicting.append(qualified)
    return matched, conflicting, unavailable


def _status(
    matched: tuple[str, ...],
    conflicting: tuple[str, ...],
    unavailable: tuple[str, ...],
) -> ConfiguredModuleComparisonStatus:
    if conflicting:
        return ConfiguredModuleComparisonStatus.CONFLICT
    if not matched:
        return ConfiguredModuleComparisonStatus.INSUFFICIENT
    if unavailable:
        return ConfiguredModuleComparisonStatus.PARTIAL
    return ConfiguredModuleComparisonStatus.EXACT


def _evidence(
    binding: ConfiguredModuleBinding,
    identity: CipIdentityObservation,
    fields: tuple[str, ...],
) -> tuple[TopologyEvidenceReference, ...]:
    evidence: list[TopologyEvidenceReference] = []
    for qualified in fields:
        source, field = qualified.split(".", maxsplit=1)
        evidence.append(
            TopologyEvidenceReference(
                protocol="l5x_configured_module",
                observation_target=binding.target_key,
                identifier=f"{binding.key}.{qualified}",
                description=f"configured {source} {field} evidence",
            )
        )
        evidence.append(
            TopologyEvidenceReference(
                protocol="cip_identity",
                observation_target=identity.target.key,
                identifier=f"cip.identity.{field}",
                description="discovered CIP Identity Object comparison field",
            )
        )
    return tuple(
        sorted(evidence, key=lambda item: (item.protocol, item.identifier))
    )


def reconcile_configured_modules(
    snapshot: DiscoverySnapshot,
    bindings: tuple[ConfiguredModuleBinding, ...],
    identity_result: IdentityReconciliationResult | None = None,
) -> ConfiguredModuleReconciliationResult:
    """Compare explicit module bindings without inferring compatibility."""
    identities = {identity.target.key: identity for identity in snapshot.identities}
    physical = identity_result or reconcile_cip_physical_identities(snapshot)
    physical_by_target: dict[str, set[str]] = {}
    for match in physical.matches:
        physical_by_target.setdefault(match.observation_target, set()).add(
            match.physical_asset_key
        )

    candidates: list[ConfiguredModuleReconciliationCandidate] = []
    targets_without_identity: set[str] = set()
    for binding in bindings:
        discovered = identities.get(binding.target_key)
        if discovered is None:
            targets_without_identity.add(binding.target_key)
            continue

        matched, conflicting, unavailable = _compare_identity(
            binding.module.identity,
            discovered,
            prefix="module_identity",
        )
        electronic_key = binding.module.electronic_key
        if electronic_key is not None and electronic_key.identity is not None:
            key_matched, key_conflicting, key_unavailable = _compare_identity(
                electronic_key.identity,
                discovered,
                prefix="electronic_key_identity",
            )
            matched.extend(key_matched)
            conflicting.extend(key_conflicting)
            unavailable.extend(key_unavailable)

        matched_fields = tuple(sorted(matched))
        conflicting_fields = tuple(sorted(conflicting))
        unavailable_fields = tuple(sorted(unavailable))
        comparison_status = _status(
            matched_fields,
            conflicting_fields,
            unavailable_fields,
        )
        evidence_fields = tuple(sorted(set(matched_fields + conflicting_fields)))
        candidates.append(
            ConfiguredModuleReconciliationCandidate(
                key=f"configured:{binding.key}|compares:{binding.target_key}",
                configured_module_key=binding.key,
                target_key=binding.target_key,
                status=comparison_status,
                matched_fields=matched_fields,
                conflicting_fields=conflicting_fields,
                unavailable_fields=unavailable_fields,
                electronic_key_mode=(
                    electronic_key.mode.value
                    if electronic_key is not None
                    and electronic_key.mode is not None
                    else None
                ),
                physical_asset_keys=tuple(
                    sorted(physical_by_target.get(binding.target_key, set()))
                ),
                confidence=(
                    TopologyConfidence.CORROBORATED
                    if matched_fields and not conflicting_fields
                    else TopologyConfidence.INDIRECT
                ),
                evidence=_evidence(binding, discovered, evidence_fields),
                electronic_key_evaluation=evaluate_electronic_key(
                    binding.module,
                    discovered,
                ),
            )
        )

    return ConfiguredModuleReconciliationResult(
        candidates=tuple(sorted(candidates, key=lambda item: item.key)),
        targets_without_cip_identity=tuple(sorted(targets_without_identity)),
    )


def configured_module_reconciliation_data(
    result: ConfiguredModuleReconciliationResult,
) -> dict[str, Any]:
    """Return a stable JSON-compatible configured-module comparison."""
    return {
        "candidates": [
            {
                "key": item.key,
                "configured_module_key": item.configured_module_key,
                "target_key": item.target_key,
                "status": item.status.value,
                "matched_fields": list(item.matched_fields),
                "conflicting_fields": list(item.conflicting_fields),
                "unavailable_fields": list(item.unavailable_fields),
                "electronic_key_mode": item.electronic_key_mode,
                "electronic_key_evaluation": (
                    electronic_key_evaluation_data(item.electronic_key_evaluation)
                    if item.electronic_key_evaluation is not None
                    else None
                ),
                "physical_asset_keys": list(item.physical_asset_keys),
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
            for item in result.candidates
        ],
        "targets_without_cip_identity": list(result.targets_without_cip_identity),
    }


def configured_module_reconciliation_json(
    result: ConfiguredModuleReconciliationResult,
) -> str:
    """Serialize configured-module comparisons deterministically."""
    return json.dumps(
        configured_module_reconciliation_data(result),
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def reconcile_routed_configured_modules(
    snapshot: CipRoutedDiscoverySnapshot,
    bindings: tuple[RoutedConfiguredModuleBinding, ...],
) -> RoutedConfiguredModuleReconciliationResult:
    """Compare explicit L5X bindings with exact routed chassis slots."""
    binding_locations = [
        (binding.chassis_route_key, binding.slot) for binding in bindings
    ]
    if len(binding_locations) != len(set(binding_locations)):
        raise ValueError("routed module bindings must have unique locations")

    observed: dict[tuple[str, int], CipChassisSlotObservation] = {}
    for chassis in snapshot.chassis:
        route_key = chassis.plan.route.key
        for slot in chassis.slots:
            observed[(route_key, slot.slot)] = slot

    candidates: list[ConfiguredModuleReconciliationCandidate] = []
    issues: list[RoutedConfiguredModuleIssue] = []
    bound_locations = set(binding_locations)
    for binding in bindings:
        location = (binding.chassis_route_key, binding.slot)
        slot = observed.get(location)
        if slot is None:
            issues.append(_routed_issue(binding, "slot_not_observed"))
            continue
        if slot.state is not CipSlotState.POPULATED or slot.identity is None:
            issues.append(_routed_issue(binding, slot.state.value))
            continue
        candidates.append(
            _routed_candidate(binding, slot.identity)
        )

    for (route_key, slot_number), slot in observed.items():
        if (
            slot.state is CipSlotState.POPULATED
            and (route_key, slot_number) not in bound_locations
        ):
            issues.append(
                RoutedConfiguredModuleIssue(
                    key=f"unbound:{route_key}|slot:{slot_number}",
                    reason="populated_slot_without_binding",
                    chassis_route_key=route_key,
                    slot=slot_number,
                )
            )

    return RoutedConfiguredModuleReconciliationResult(
        candidates=tuple(sorted(candidates, key=lambda item: item.key)),
        issues=tuple(sorted(issues, key=lambda item: item.key)),
    )


def _routed_issue(
    binding: RoutedConfiguredModuleBinding,
    reason: str,
) -> RoutedConfiguredModuleIssue:
    return RoutedConfiguredModuleIssue(
        key=f"binding:{binding.key}|issue:{reason}",
        reason=reason,
        chassis_route_key=binding.chassis_route_key,
        slot=binding.slot,
    )


def _routed_candidate(
    binding: RoutedConfiguredModuleBinding,
    discovered: CipIdentityObservation,
) -> ConfiguredModuleReconciliationCandidate:
    matched, conflicting, unavailable = _compare_identity(
        binding.module.identity,
        discovered,
        prefix="module_identity",
    )
    electronic_key = binding.module.electronic_key
    if electronic_key is not None and electronic_key.identity is not None:
        key_values = _compare_identity(
            electronic_key.identity,
            discovered,
            prefix="electronic_key_identity",
        )
        matched.extend(key_values[0])
        conflicting.extend(key_values[1])
        unavailable.extend(key_values[2])
    matched_fields = tuple(sorted(matched))
    conflicting_fields = tuple(sorted(conflicting))
    unavailable_fields = tuple(sorted(unavailable))
    evidence_fields = tuple(sorted(set(matched_fields + conflicting_fields)))
    evidence_binding = ConfiguredModuleBinding(
        key=binding.key,
        target_key=discovered.target.key,
        module=binding.module,
    )
    return ConfiguredModuleReconciliationCandidate(
        key=(
            f"configured:{binding.key}|route:{binding.chassis_route_key}"
            f"|slot:{binding.slot}"
        ),
        configured_module_key=binding.key,
        target_key=discovered.target.key,
        status=_status(
            matched_fields,
            conflicting_fields,
            unavailable_fields,
        ),
        matched_fields=matched_fields,
        conflicting_fields=conflicting_fields,
        unavailable_fields=unavailable_fields,
        electronic_key_mode=(
            electronic_key.mode.value
            if electronic_key is not None and electronic_key.mode is not None
            else None
        ),
        physical_asset_keys=(),
        confidence=(
            TopologyConfidence.CORROBORATED
            if matched_fields and not conflicting_fields
            else TopologyConfidence.INDIRECT
        ),
        evidence=tuple(
            sorted(
                _evidence(evidence_binding, discovered, evidence_fields)
                + (
                    TopologyEvidenceReference(
                        protocol="cip_routed_slot",
                        observation_target=discovered.target.key,
                        identifier=(
                            f"{binding.chassis_route_key}|slot:{binding.slot}"
                        ),
                        description="explicit routed chassis-slot observation",
                    ),
                ),
                key=lambda item: (item.protocol, item.identifier),
            )
        ),
        electronic_key_evaluation=evaluate_electronic_key(
            binding.module,
            discovered,
        ),
    )


def routed_configured_module_reconciliation_data(
    result: RoutedConfiguredModuleReconciliationResult,
) -> dict[str, Any]:
    """Return deterministic slot-aware reconciliation evidence."""
    candidate_data = configured_module_reconciliation_data(
        ConfiguredModuleReconciliationResult(
            candidates=result.candidates,
            targets_without_cip_identity=(),
        )
    )["candidates"]
    return {
        "candidates": candidate_data,
        "issues": [
            {
                "key": issue.key,
                "reason": issue.reason,
                "chassis_route_key": issue.chassis_route_key,
                "slot": issue.slot,
            }
            for issue in result.issues
        ],
    }


def routed_configured_module_reconciliation_json(
    result: RoutedConfiguredModuleReconciliationResult,
) -> str:
    """Serialize slot-aware reconciliation deterministically."""
    return json.dumps(
        routed_configured_module_reconciliation_data(result),
        indent=2,
        ensure_ascii=False,
    ) + "\n"
