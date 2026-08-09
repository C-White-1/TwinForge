"""Correlate software devices with approved routed module mappings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from twinforge.discovery import (
    ChassisTopologyAcceptanceResult,
    RoutedConfiguredModuleBinding,
)
from twinforge.discovery.topology import (
    RelationshipEvidenceClass,
    TopologyEvidenceReference,
)

from .software_devices import AssembledSoftwareDevice


class CrossLayerCorrelationError(ValueError):
    """Cross-layer evidence is ambiguous or internally inconsistent."""


@dataclass(frozen=True)
class CorrelatedSoftwareDevice:
    """Reversible link across software, configuration, and routed evidence."""

    key: str
    workspace_key: str
    software_definition: str
    instance_tag: str
    provider: str
    configured_module_key: str
    chassis_route_key: str
    slot: int
    controller_asset_id: str
    chassis_asset_id: str
    module_asset_id: str
    software_evidence: tuple[str, ...]
    routed_evidence: tuple[TopologyEvidenceReference, ...]


@dataclass(frozen=True)
class CrossLayerDeviceCorrelationResult:
    """Correlations plus every unmatched software device and mapping."""

    correlations: tuple[CorrelatedSoftwareDevice, ...]
    software_devices_without_mapping: tuple[str, ...]
    mappings_without_software_device: tuple[str, ...]


def _software_key(item: AssembledSoftwareDevice) -> str:
    source = item.source
    return (
        f"{source.workspace_key}|definition:{source.definition.name}"
        f"|instance:{source.instance_tag.name}"
    )


def correlate_software_devices_with_routed_modules(
    devices: tuple[AssembledSoftwareDevice, ...],
    bindings: tuple[RoutedConfiguredModuleBinding, ...],
    accepted: ChassisTopologyAcceptanceResult,
) -> CrossLayerDeviceCorrelationResult:
    """Join layers only through original module objects and accepted mappings."""
    binding_by_module: dict[int, RoutedConfiguredModuleBinding] = {}
    for binding in bindings:
        module_key = id(binding.module)
        if module_key in binding_by_module:
            raise CrossLayerCorrelationError(
                "one configured module has multiple routed bindings"
            )
        binding_by_module[module_key] = binding

    mapping_by_binding = {
        item.configured_module_key: item for item in accepted.accepted_mappings
    }
    if len(mapping_by_binding) != len(accepted.accepted_mappings):
        raise CrossLayerCorrelationError(
            "accepted mappings contain duplicate configured module keys"
        )

    correlations: list[CorrelatedSoftwareDevice] = []
    unmatched_devices: list[str] = []
    used_mappings: set[str] = set()
    for item in devices:
        software_key = _software_key(item)
        matched_bindings = {
            binding_by_module[id(module)].key: binding_by_module[id(module)]
            for module in item.source.modules
            if id(module) in binding_by_module
        }
        matched_mappings = [
            mapping_by_binding[key]
            for key in sorted(matched_bindings)
            if key in mapping_by_binding
        ]
        if not matched_mappings:
            unmatched_devices.append(software_key)
            continue
        if len(matched_mappings) != 1:
            raise CrossLayerCorrelationError(
                f"software device {software_key!r} resolves to multiple accepted mappings"
            )
        mapping = matched_mappings[0]
        used_mappings.add(mapping.candidate_key)
        correlations.append(
            CorrelatedSoftwareDevice(
                key=f"software:{software_key}|mapping:{mapping.candidate_key}",
                workspace_key=item.source.workspace_key,
                software_definition=item.source.definition.name,
                instance_tag=item.source.instance_tag.name,
                provider=item.provider,
                configured_module_key=mapping.configured_module_key,
                chassis_route_key=mapping.chassis_route_key,
                slot=mapping.slot,
                controller_asset_id=mapping.controller_asset_id,
                chassis_asset_id=mapping.chassis_asset_id,
                module_asset_id=mapping.module_asset_id,
                software_evidence=item.source.evidence,
                routed_evidence=mapping.evidence,
            )
        )

    return CrossLayerDeviceCorrelationResult(
        correlations=tuple(sorted(correlations, key=lambda item: item.key)),
        software_devices_without_mapping=tuple(sorted(unmatched_devices)),
        mappings_without_software_device=tuple(
            sorted(
                item.candidate_key
                for item in accepted.accepted_mappings
                if item.candidate_key not in used_mappings
            )
        ),
    )


def cross_layer_device_correlation_data(
    result: CrossLayerDeviceCorrelationResult,
) -> dict[str, Any]:
    """Return deterministic JSON-compatible cross-layer evidence."""
    return {
        "correlations": [
            {
                "key": item.key,
                "evidence_class": (
                    RelationshipEvidenceClass.CROSS_LAYER_CORROBORATED.value
                ),
                "workspace_key": item.workspace_key,
                "software_definition": item.software_definition,
                "instance_tag": item.instance_tag,
                "provider": item.provider,
                "configured_module_key": item.configured_module_key,
                "chassis_route_key": item.chassis_route_key,
                "slot": item.slot,
                "controller_asset_id": item.controller_asset_id,
                "chassis_asset_id": item.chassis_asset_id,
                "module_asset_id": item.module_asset_id,
                "software_evidence": list(item.software_evidence),
                "routed_evidence": [
                    {
                        "protocol": evidence.protocol,
                        "observation_target": evidence.observation_target,
                        "identifier": evidence.identifier,
                        "description": evidence.description,
                    }
                    for evidence in item.routed_evidence
                ],
            }
            for item in result.correlations
        ],
        "software_devices_without_mapping": list(
            result.software_devices_without_mapping
        ),
        "mappings_without_software_device": list(
            result.mappings_without_software_device
        ),
    }


def cross_layer_device_correlation_json(
    result: CrossLayerDeviceCorrelationResult,
) -> str:
    """Serialize cross-layer device correlations deterministically."""
    return json.dumps(
        cross_layer_device_correlation_data(result),
        indent=2,
        ensure_ascii=False,
    ) + "\n"
