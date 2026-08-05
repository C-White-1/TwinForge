"""Evidence-backed correlation of discovery observations into topology candidates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .contracts import DiscoverySnapshot, SnmpNodeObservation


class TopologyRelationshipType(str, Enum):
    """Meaning supported by the underlying discovery evidence."""

    REPORTED_NEIGHBOUR = "reported_neighbour"
    MAC_REACHABILITY = "mac_reachability"


class TopologyConfidence(str, Enum):
    """Qualitative strength without implying statistical probability."""

    INDIRECT = "indirect"
    PROTOCOL_REPORTED = "protocol_reported"
    CORROBORATED = "corroborated"


@dataclass(frozen=True)
class TopologyEvidenceReference:
    """Reference to one retained observation supporting a candidate."""

    protocol: str
    observation_target: str
    identifier: str
    description: str


@dataclass(frozen=True)
class TopologyNodeCandidate:
    """Candidate node assembled from identifiers, without claiming ownership."""

    key: str
    display_names: tuple[str, ...] = ()
    addresses: tuple[str, ...] = ()
    chassis_ids: tuple[str, ...] = ()
    observed_target_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class TopologyRelationshipCandidate:
    """One evidence-backed relationship awaiting acceptance or reconciliation."""

    key: str
    relationship_type: TopologyRelationshipType
    source_node_key: str
    target_node_key: str
    source_interface_index: int | None
    source_port_number: int | None
    target_port_id: str | None
    confidence: TopologyConfidence
    evidence: tuple[TopologyEvidenceReference, ...]


@dataclass(frozen=True)
class TopologyCorrelationResult:
    """Deterministically ordered nodes and candidate relationships."""

    nodes: tuple[TopologyNodeCandidate, ...]
    relationships: tuple[TopologyRelationshipCandidate, ...]


def _target_node_key(target_key: str) -> str:
    return f"target:{target_key}"


def _chassis_node_key(chassis_id: str) -> str:
    return f"chassis:{chassis_id.lower()}"


def _mac_node_key(mac_address: str) -> str:
    return f"mac:{mac_address.lower()}"


def _known_target_by_address(snapshot: DiscoverySnapshot) -> dict[str, str]:
    return {
        target.address: _target_node_key(target.key)
        for target in snapshot.targets
    }


def _remote_node_key(
    management_addresses: tuple[str, ...],
    chassis_id: str,
    known_addresses: dict[str, str],
) -> str:
    matches = {
        known_addresses[address]
        for address in management_addresses
        if address in known_addresses
    }
    if len(matches) == 1:
        return matches.pop()
    return _chassis_node_key(chassis_id)


def _observation_node(node: SnmpNodeObservation) -> TopologyNodeCandidate:
    addresses = {
        address.address
        for interface in node.interfaces
        for address in interface.addresses
    }
    names = {node.system_name} if node.system_name else set()
    return TopologyNodeCandidate(
        key=_target_node_key(node.target.key),
        display_names=tuple(sorted(names)),
        addresses=tuple(sorted(addresses)),
        observed_target_keys=(node.target.key,),
    )


def _merge_node(
    nodes: dict[str, TopologyNodeCandidate],
    candidate: TopologyNodeCandidate,
) -> None:
    current = nodes.get(candidate.key)
    if current is None:
        nodes[candidate.key] = candidate
        return
    nodes[candidate.key] = TopologyNodeCandidate(
        key=candidate.key,
        display_names=tuple(
            sorted(set(current.display_names) | set(candidate.display_names))
        ),
        addresses=tuple(sorted(set(current.addresses) | set(candidate.addresses))),
        chassis_ids=tuple(
            sorted(set(current.chassis_ids) | set(candidate.chassis_ids))
        ),
        observed_target_keys=tuple(
            sorted(
                set(current.observed_target_keys)
                | set(candidate.observed_target_keys)
            )
        ),
    )


def correlate_topology(snapshot: DiscoverySnapshot) -> TopologyCorrelationResult:
    """Correlate SNMP observations while preserving relationship semantics."""
    nodes: dict[str, TopologyNodeCandidate] = {}
    relationships: list[TopologyRelationshipCandidate] = []
    known_addresses = _known_target_by_address(snapshot)

    for target in snapshot.targets:
        _merge_node(
            nodes,
            TopologyNodeCandidate(
                key=_target_node_key(target.key),
                display_names=(target.label,) if target.label else (),
                addresses=(target.address,),
                observed_target_keys=(target.key,),
            ),
        )
    for identity in snapshot.identities:
        _merge_node(
            nodes,
            TopologyNodeCandidate(
                key=_target_node_key(identity.target.key),
                display_names=(identity.product_name,),
                addresses=(identity.target.address,),
                observed_target_keys=(identity.target.key,),
            ),
        )

    for observed_node in snapshot.snmp_nodes:
        _merge_node(nodes, _observation_node(observed_node))
        source_key = _target_node_key(observed_node.target.key)
        neighbour_links: dict[tuple[str, int | None], int] = {}
        for neighbour in observed_node.neighbours:
            target_key = _remote_node_key(
                neighbour.management_addresses,
                neighbour.remote_chassis_id,
                known_addresses,
            )
            _merge_node(
                nodes,
                TopologyNodeCandidate(
                    key=target_key,
                    display_names=(neighbour.remote_system_name,)
                    if neighbour.remote_system_name
                    else (),
                    addresses=tuple(sorted(neighbour.management_addresses)),
                    chassis_ids=(neighbour.remote_chassis_id,),
                ),
            )
            evidence = tuple(
                TopologyEvidenceReference(
                    protocol=neighbour.protocol,
                    observation_target=observed_node.target.key,
                    identifier=oid,
                    description="neighbour reported by the remote-systems table",
                )
                for oid in sorted(neighbour.raw_oids)
            )
            relationship = TopologyRelationshipCandidate(
                key=(
                    f"{source_key}|lldp:{neighbour.local_port_number}|"
                    f"{target_key}|{neighbour.remote_port_id}"
                ),
                relationship_type=TopologyRelationshipType.REPORTED_NEIGHBOUR,
                source_node_key=source_key,
                target_node_key=target_key,
                source_interface_index=neighbour.local_interface_index,
                source_port_number=neighbour.local_port_number,
                target_port_id=neighbour.remote_port_id,
                confidence=TopologyConfidence.PROTOCOL_REPORTED,
                evidence=evidence,
            )
            neighbour_links[
                (neighbour.remote_chassis_id.lower(), neighbour.local_interface_index)
            ] = len(relationships)
            relationships.append(relationship)

        for entry in observed_node.forwarding_entries:
            corroborated_index = neighbour_links.get(
                (entry.mac_address.lower(), entry.interface_index)
            )
            evidence = TopologyEvidenceReference(
                protocol="bridge_fdb",
                observation_target=observed_node.target.key,
                identifier=next(iter(sorted(entry.raw_oids)), entry.mac_address),
                description="MAC learned through the bridge forwarding table",
            )
            if corroborated_index is not None:
                current = relationships[corroborated_index]
                relationships[corroborated_index] = TopologyRelationshipCandidate(
                    key=current.key,
                    relationship_type=current.relationship_type,
                    source_node_key=current.source_node_key,
                    target_node_key=current.target_node_key,
                    source_interface_index=current.source_interface_index,
                    source_port_number=current.source_port_number,
                    target_port_id=current.target_port_id,
                    confidence=TopologyConfidence.CORROBORATED,
                    evidence=tuple(sorted(current.evidence + (evidence,), key=_evidence_key)),
                )
                continue

            target_key = _mac_node_key(entry.mac_address)
            _merge_node(
                nodes,
                TopologyNodeCandidate(
                    key=target_key,
                    chassis_ids=(entry.mac_address,),
                ),
            )
            relationships.append(
                TopologyRelationshipCandidate(
                    key=(
                        f"{source_key}|fdb:{entry.bridge_port}|{target_key}"
                    ),
                    relationship_type=TopologyRelationshipType.MAC_REACHABILITY,
                    source_node_key=source_key,
                    target_node_key=target_key,
                    source_interface_index=entry.interface_index,
                    source_port_number=entry.bridge_port,
                    target_port_id=None,
                    confidence=TopologyConfidence.INDIRECT,
                    evidence=(evidence,),
                )
            )

    return TopologyCorrelationResult(
        nodes=tuple(sorted(nodes.values(), key=lambda item: item.key)),
        relationships=tuple(sorted(relationships, key=lambda item: item.key)),
    )


def _evidence_key(evidence: TopologyEvidenceReference) -> tuple[str, str, str]:
    return evidence.protocol, evidence.observation_target, evidence.identifier


def topology_data(result: TopologyCorrelationResult) -> dict[str, Any]:
    """Return a stable JSON-compatible topology candidate representation."""
    return {
        "nodes": [
            {
                "key": node.key,
                "display_names": list(node.display_names),
                "addresses": list(node.addresses),
                "chassis_ids": list(node.chassis_ids),
                "observed_target_keys": list(node.observed_target_keys),
            }
            for node in result.nodes
        ],
        "relationships": [
            {
                "key": relationship.key,
                "relationship_type": relationship.relationship_type.value,
                "source_node_key": relationship.source_node_key,
                "target_node_key": relationship.target_node_key,
                "source_interface_index": relationship.source_interface_index,
                "source_port_number": relationship.source_port_number,
                "target_port_id": relationship.target_port_id,
                "confidence": relationship.confidence.value,
                "evidence": [
                    {
                        "protocol": evidence.protocol,
                        "observation_target": evidence.observation_target,
                        "identifier": evidence.identifier,
                        "description": evidence.description,
                    }
                    for evidence in relationship.evidence
                ],
            }
            for relationship in result.relationships
        ],
    }


def topology_json(result: TopologyCorrelationResult) -> str:
    """Serialize topology candidates deterministically with a final newline."""
    return json.dumps(topology_data(result), indent=2, ensure_ascii=False) + "\n"
