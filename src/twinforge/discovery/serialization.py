"""Stable JSON serialization for discovery evidence."""

from __future__ import annotations

import json
from typing import Any

from .contracts import DiscoverySnapshot, DiscoveryTarget


def _target_data(target: DiscoveryTarget) -> dict[str, Any]:
    return {
        "address": target.address,
        "route": list(target.route),
        "label": target.label,
    }


def snapshot_data(snapshot: DiscoverySnapshot) -> dict[str, Any]:
    """Return the canonical JSON-compatible representation of a snapshot."""
    return {
        "schema_version": snapshot.schema_version,
        "engagement": snapshot.engagement,
        "authorization_reference": snapshot.authorization_reference,
        "captured_at": snapshot.captured_at.isoformat(),
        "operations": [operation.value for operation in snapshot.operations],
        "targets": [_target_data(target) for target in snapshot.targets],
        "identities": [
            {
                "target": _target_data(identity.target),
                "captured_at": identity.captured_at.isoformat(),
                "vendor_id": identity.vendor_id,
                "device_type": identity.device_type,
                "product_code": identity.product_code,
                "major_revision": identity.major_revision,
                "minor_revision": identity.minor_revision,
                "status": identity.status,
                "serial_number": identity.serial_number,
                "product_name": identity.product_name,
                "state": identity.state,
                "configuration_consistency_value": (
                    identity.configuration_consistency_value
                ),
                "heartbeat_interval": identity.heartbeat_interval,
                "raw_payload_hex": identity.raw_payload_hex,
                "raw_attributes": dict(sorted(identity.raw_attributes.items())),
            }
            for identity in snapshot.identities
        ],
        "snmp_nodes": [
            {
                "target": _target_data(node.target),
                "captured_at": node.captured_at.isoformat(),
                "system_name": node.system_name,
                "system_description": node.system_description,
                "system_object_id": node.system_object_id,
                "system_contact": node.system_contact,
                "system_location": node.system_location,
                "uptime_ticks": node.uptime_ticks,
                "interfaces": [
                    {
                        "index": interface.index,
                        "name": interface.name,
                        "description": interface.description,
                        "interface_type": interface.interface_type,
                        "mac_address": interface.mac_address,
                        "speed_bps": interface.speed_bps,
                        "admin_status": interface.admin_status,
                        "operational_status": interface.operational_status,
                        "addresses": [
                            {
                                "address": address.address,
                                "prefix_length": address.prefix_length,
                            }
                            for address in sorted(
                                interface.addresses,
                                key=lambda item: (
                                    item.address,
                                    item.prefix_length or -1,
                                ),
                            )
                        ],
                        "raw_oids": dict(sorted(interface.raw_oids.items())),
                    }
                    for interface in sorted(
                        node.interfaces,
                        key=lambda item: item.index,
                    )
                ],
                "neighbours": [
                    {
                        "protocol": neighbour.protocol,
                        "local_port_number": neighbour.local_port_number,
                        "local_interface_index": neighbour.local_interface_index,
                        "remote_chassis_id": neighbour.remote_chassis_id,
                        "remote_port_id": neighbour.remote_port_id,
                        "remote_system_name": neighbour.remote_system_name,
                        "management_addresses": sorted(neighbour.management_addresses),
                        "raw_oids": dict(sorted(neighbour.raw_oids.items())),
                    }
                    for neighbour in sorted(
                        node.neighbours,
                        key=lambda item: (
                            item.local_port_number,
                            item.remote_chassis_id,
                            item.remote_port_id,
                        ),
                    )
                ],
                "forwarding_entries": [
                    {
                        "mac_address": entry.mac_address,
                        "bridge_port": entry.bridge_port,
                        "interface_index": entry.interface_index,
                        "vlan_id": entry.vlan_id,
                        "status": entry.status,
                        "raw_oids": dict(sorted(entry.raw_oids.items())),
                    }
                    for entry in sorted(
                        node.forwarding_entries,
                        key=lambda item: (
                            item.vlan_id or -1,
                            item.mac_address,
                            item.bridge_port,
                        ),
                    )
                ],
                "physical_entities": [
                    {
                        "index": entity.index,
                        "description": entity.description,
                        "vendor_type_oid": entity.vendor_type_oid,
                        "contained_in": entity.contained_in,
                        "physical_class": entity.physical_class,
                        "parent_relative_position": entity.parent_relative_position,
                        "name": entity.name,
                        "hardware_revision": entity.hardware_revision,
                        "firmware_revision": entity.firmware_revision,
                        "software_revision": entity.software_revision,
                        "serial_number": entity.serial_number,
                        "manufacturer_name": entity.manufacturer_name,
                        "model_name": entity.model_name,
                        "alias": entity.alias,
                        "asset_id": entity.asset_id,
                        "is_fru": entity.is_fru,
                        "manufacturing_date": entity.manufacturing_date,
                        "uris": list(entity.uris),
                        "uuid": entity.uuid,
                        "raw_oids": dict(sorted(entity.raw_oids.items())),
                    }
                    for entity in sorted(
                        node.physical_entities,
                        key=lambda item: item.index,
                    )
                ],
                "raw_oids": dict(sorted(node.raw_oids.items())),
            }
            for node in snapshot.snmp_nodes
        ],
        "diagnostics": [
            {
                "target": _target_data(diagnostic.target),
                "severity": diagnostic.severity.value,
                "code": diagnostic.code,
                "message": diagnostic.message,
            }
            for diagnostic in snapshot.diagnostics
        ],
    }


def snapshot_json(snapshot: DiscoverySnapshot) -> str:
    """Serialize a snapshot with stable formatting and a final newline."""
    return (
        json.dumps(
            snapshot_data(snapshot),
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
