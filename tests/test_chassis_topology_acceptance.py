from datetime import datetime, timezone

import pytest

from twinforge.discovery.acceptance import (
    AcceptancePolicyError,
    CandidateDisposition,
)
from twinforge.discovery.chassis_topology_acceptance import (
    ChassisModuleMappingReview,
    apply_chassis_module_mapping_reviews,
    chassis_topology_acceptance_json,
)
from twinforge.discovery.configured_module_reconciliation import (
    ConfiguredModuleComparisonStatus,
    ConfiguredModuleReconciliationCandidate,
    RoutedConfiguredModuleBinding,
    RoutedConfiguredModuleReconciliationResult,
)
from twinforge.discovery.topology import (
    TopologyConfidence,
    TopologyEvidenceReference,
)
from twinforge.model import Identity, Module


NOW = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _binding(key: str = "Local/DI") -> RoutedConfiguredModuleBinding:
    return RoutedConfiguredModuleBinding(
        key=key,
        chassis_route_key="192.168.1.10|1:0",
        slot=2,
        module=Module(name="DI", catalog="1756-IB16", identity=Identity()),
    )


def _result(
    status: ConfiguredModuleComparisonStatus = ConfiguredModuleComparisonStatus.EXACT,
) -> RoutedConfiguredModuleReconciliationResult:
    return RoutedConfiguredModuleReconciliationResult(
        candidates=(
            ConfiguredModuleReconciliationCandidate(
                key="configured:Local/DI|route:192.168.1.10|1:0|slot:2",
                configured_module_key="Local/DI",
                target_key="192.168.1.10",
                status=status,
                matched_fields=("module_identity.vendor_id",),
                conflicting_fields=(),
                unavailable_fields=(),
                electronic_key_mode=None,
                physical_asset_keys=(),
                confidence=TopologyConfidence.CORROBORATED,
                evidence=(
                    TopologyEvidenceReference(
                        protocol="cip_routed_slot",
                        observation_target="192.168.1.10",
                        identifier="192.168.1.10|1:0|slot:2",
                        description="routed slot evidence",
                    ),
                ),
            ),
        ),
        issues=(),
    )


def _review(**changes: object) -> ChassisModuleMappingReview:
    values: dict[str, object] = {
        "candidate_key": _result().candidates[0].key,
        "disposition": CandidateDisposition.ACCEPT,
        "reviewed_by": "lab.operator",
        "reviewed_at": NOW,
        "rationale": "Exact routed module comparison",
        "controller_asset_id": "controller-1",
        "chassis_asset_id": "chassis-1",
        "module_asset_id": "module-2",
    }
    values.update(changes)
    return ChassisModuleMappingReview(**values)  # type: ignore[arg-type]


def test_accepts_explicit_route_slot_and_core_asset_mapping() -> None:
    result = apply_chassis_module_mapping_reviews(
        _result(), (_binding(),), (_review(),)
    )

    mapping = result.accepted_mappings[0]
    assert mapping.chassis_route_key == "192.168.1.10|1:0"
    assert mapping.slot == 2
    assert mapping.module_asset_id == "module-2"
    assert "cip_routed_slot" in chassis_topology_acceptance_json(result)


def test_rejected_mapping_cannot_name_core_assets() -> None:
    with pytest.raises(AcceptancePolicyError, match="cannot name core assets"):
        apply_chassis_module_mapping_reviews(
            _result(),
            (_binding(),),
            (_review(disposition=CandidateDisposition.REJECT),),
        )


def test_conflicting_mapping_requires_explicit_override() -> None:
    with pytest.raises(AcceptancePolicyError, match="explicit override"):
        apply_chassis_module_mapping_reviews(
            _result(ConfiguredModuleComparisonStatus.CONFLICT),
            (_binding(),),
            (_review(),),
        )


def test_mapping_requires_the_original_explicit_binding() -> None:
    with pytest.raises(AcceptancePolicyError, match="no supplied routed binding"):
        apply_chassis_module_mapping_reviews(_result(), (), (_review(),))
