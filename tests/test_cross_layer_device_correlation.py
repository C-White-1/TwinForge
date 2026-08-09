from datetime import datetime, timezone

import pytest

from twinforge.assembly import (
    AssembledSoftwareDevice,
    CrossLayerCorrelationError,
    correlate_software_devices_with_routed_modules,
    cross_layer_device_correlation_json,
)
from twinforge.discovery import (
    AcceptedChassisModuleMapping,
    CandidateDisposition,
    ChassisModuleMappingReview,
    ChassisTopologyAcceptanceResult,
    RoutedConfiguredModuleBinding,
)
from twinforge.discovery.topology import TopologyEvidenceReference
from twinforge.model import (
    Device,
    DeviceType,
    Identity,
    Module,
    SoftwareComponent,
    SoftwareComponentKind,
    SoftwareModuleAssembly,
    Tag,
)


NOW = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _module(name: str = "DriveModule") -> Module:
    return Module(name=name, catalog="ETHERNET-MODULE", identity=Identity())


def _device(module: Module) -> AssembledSoftwareDevice:
    definition = SoftwareComponent(
        id="software:def:dvc_pf525",
        name="Dvc_PF525",
        kind=SoftwareComponentKind.FUNCTION_BLOCK,
    )
    source = SoftwareModuleAssembly(
        workspace_key="controller:PLC_A",
        definition=definition,
        instance_tag=Tag(name="Drive01"),
        modules=(module,),
        calls=(),
        evidence=("Main.Drive: Dvc_PF525 accesses DriveModule:I.Data",),
    )
    return AssembledSoftwareDevice(
        device=Device(id="device:drive01", name="Drive01", device_type=DeviceType.DRIVE),
        source=source,
        provider="powerflex_525",
    )


def _binding(module: Module, key: str = "Local/DriveModule") -> RoutedConfiguredModuleBinding:
    return RoutedConfiguredModuleBinding(
        key=key,
        chassis_route_key="192.168.1.10|1:0",
        slot=3,
        module=module,
    )


def _mapping(key: str = "Local/DriveModule") -> AcceptedChassisModuleMapping:
    review = ChassisModuleMappingReview(
        candidate_key=f"candidate:{key}",
        disposition=CandidateDisposition.ACCEPT,
        reviewed_by="lab.operator",
        reviewed_at=NOW,
        rationale="Accepted exact routed comparison",
        controller_asset_id="controller-asset",
        chassis_asset_id="chassis-asset",
        module_asset_id="module-asset",
    )
    return AcceptedChassisModuleMapping(
        candidate_key=review.candidate_key,
        configured_module_key=key,
        chassis_route_key="192.168.1.10|1:0",
        slot=3,
        controller_asset_id="controller-asset",
        chassis_asset_id="chassis-asset",
        module_asset_id="module-asset",
        review=review,
        evidence=(
            TopologyEvidenceReference(
                protocol="cip_routed_slot",
                observation_target="192.168.1.10",
                identifier="192.168.1.10|1:0|slot:3",
                description="exact routed slot evidence",
            ),
        ),
    )


def _accepted(*mappings: AcceptedChassisModuleMapping) -> ChassisTopologyAcceptanceResult:
    return ChassisTopologyAcceptanceResult(
        accepted_mappings=mappings,
        rejected_candidate_keys=(),
        deferred_candidate_keys=(),
        unreviewed_candidate_keys=(),
    )


def test_correlates_software_device_through_original_module_binding() -> None:
    module = _module()
    result = correlate_software_devices_with_routed_modules(
        (_device(module),), (_binding(module),), _accepted(_mapping())
    )

    correlation = result.correlations[0]
    assert correlation.instance_tag == "Drive01"
    assert correlation.slot == 3
    assert correlation.module_asset_id == "module-asset"
    assert "cip_routed_slot" in cross_layer_device_correlation_json(result)
    assert '"evidence_class": "cross_layer_corroborated"' in (
        cross_layer_device_correlation_json(result)
    )


def test_retains_unmatched_software_and_accepted_mapping() -> None:
    result = correlate_software_devices_with_routed_modules(
        (_device(_module("Unbound")),), (), _accepted(_mapping())
    )

    assert len(result.software_devices_without_mapping) == 1
    assert result.mappings_without_software_device == (
        "candidate:Local/DriveModule",
    )


def test_rejects_multiple_routed_bindings_for_same_module() -> None:
    module = _module()
    with pytest.raises(CrossLayerCorrelationError, match="multiple routed bindings"):
        correlate_software_devices_with_routed_modules(
            (_device(module),),
            (_binding(module, "first"), _binding(module, "second")),
            _accepted(),
        )
