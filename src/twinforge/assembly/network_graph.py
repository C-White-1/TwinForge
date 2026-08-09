"""Lower accepted SNMP neighbour evidence into a vendor-neutral graph."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from twinforge.discovery import (
    DiscoverySnapshot,
    RelationshipEvidenceClass,
    TopologyAcceptanceResult,
    TopologyCorrelationResult,
)
from twinforge.discovery.topology import TopologyEvidenceReference
from twinforge.model import Asset, Network


class NetworkGraphLoweringError(ValueError):
    """Accepted topology cannot be lowered without inventing a relationship."""


@dataclass(frozen=True)
class NetworkInterfaceEvidence:
    """Observed SNMP interface retained without attaching it to a core device."""

    key: str
    asset_key: str
    observation_target: str
    interface_index: int
    name: str | None
    description: str | None
    interface_type: int | None
    mac_address: str | None
    speed_bps: int | None
    admin_status: int | None
    operational_status: int | None
    addresses: tuple[str, ...]


@dataclass(frozen=True)
class NetworkGraphNode:
    """Explicit durable asset represented as one graph node."""

    asset_key: str
    asset: Asset
    topology_node_keys: tuple[str, ...]
    interfaces: tuple[NetworkInterfaceEvidence, ...]


@dataclass(frozen=True)
class NetworkGraphLink:
    """Operator-accepted neighbour link between durable graph nodes."""

    key: str
    source_asset_key: str
    target_asset_key: str
    source_interface_key: str | None
    source_port_number: int | None
    target_port_id: str | None
    evidence_class: RelationshipEvidenceClass
    evidence: tuple[TopologyEvidenceReference, ...]


@dataclass(frozen=True)
class AcceptedNetworkGraph:
    """Network aggregate plus accepted links and retained interface evidence."""

    network: Network
    nodes: tuple[NetworkGraphNode, ...]
    links: tuple[NetworkGraphLink, ...]


def lower_accepted_network_graph(
    snapshot: DiscoverySnapshot,
    topology: TopologyCorrelationResult,
    acceptance: TopologyAcceptanceResult,
    assets: Mapping[str, Asset],
    *,
    network_id: str,
    network_name: str,
    protocol: str = "ethernet",
) -> AcceptedNetworkGraph:
    """Lower only accepted relationships and exactly observed interfaces."""
    for field, value in (
        ("network_id", network_id),
        ("network_name", network_name),
        ("protocol", protocol),
    ):
        if not value or value != value.strip():
            raise NetworkGraphLoweringError(f"{field} must be non-empty and trimmed")
    topology_nodes = {item.key: item for item in topology.nodes}
    snmp_by_target = {item.target.key: item for item in snapshot.snmp_nodes}
    asset_nodes: dict[str, set[str]] = {}
    for relationship in acceptance.accepted_relationships:
        for asset_key, node_key in (
            (relationship.source_asset_key, relationship.source_node_key),
            (relationship.target_asset_key, relationship.target_node_key),
        ):
            if asset_key not in assets:
                raise NetworkGraphLoweringError(
                    f"accepted relationship references unknown asset {asset_key!r}"
                )
            if node_key not in topology_nodes:
                raise NetworkGraphLoweringError(
                    f"accepted relationship references unknown topology node {node_key!r}"
                )
            asset_nodes.setdefault(asset_key, set()).add(node_key)

    nodes: list[NetworkGraphNode] = []
    interfaces_by_location: dict[tuple[str, int], str] = {}
    for asset_key, node_keys in sorted(asset_nodes.items()):
        interfaces: list[NetworkInterfaceEvidence] = []
        for node_key in sorted(node_keys):
            node = topology_nodes[node_key]
            for target_key in node.observed_target_keys:
                observed = snmp_by_target.get(target_key)
                if observed is None:
                    continue
                for interface in observed.interfaces:
                    key = f"asset:{asset_key}|snmp:{target_key}|if:{interface.index}"
                    location = (node_key, interface.index)
                    previous = interfaces_by_location.setdefault(location, key)
                    if previous != key:
                        raise NetworkGraphLoweringError(
                            f"topology interface {location!r} maps to multiple assets"
                        )
                    interfaces.append(
                        NetworkInterfaceEvidence(
                            key=key,
                            asset_key=asset_key,
                            observation_target=target_key,
                            interface_index=interface.index,
                            name=interface.name,
                            description=interface.description,
                            interface_type=interface.interface_type,
                            mac_address=interface.mac_address,
                            speed_bps=interface.speed_bps,
                            admin_status=interface.admin_status,
                            operational_status=interface.operational_status,
                            addresses=tuple(
                                sorted(item.address for item in interface.addresses)
                            ),
                        )
                    )
        nodes.append(
            NetworkGraphNode(
                asset_key=asset_key,
                asset=assets[asset_key],
                topology_node_keys=tuple(sorted(node_keys)),
                interfaces=tuple(sorted(interfaces, key=lambda item: item.key)),
            )
        )

    links: list[NetworkGraphLink] = []
    for relationship in acceptance.accepted_relationships:
        interface_key = None
        if relationship.source_interface_index is not None:
            interface_key = interfaces_by_location.get(
                (relationship.source_node_key, relationship.source_interface_index)
            )
            if interface_key is None:
                raise NetworkGraphLoweringError(
                    f"accepted relationship {relationship.key!r} references "
                    "an interface absent from SNMP evidence"
                )
        links.append(
            NetworkGraphLink(
                key=relationship.key,
                source_asset_key=relationship.source_asset_key,
                target_asset_key=relationship.target_asset_key,
                source_interface_key=interface_key,
                source_port_number=relationship.source_port_number,
                target_port_id=relationship.target_port_id,
                evidence_class=RelationshipEvidenceClass.OPERATOR_ACCEPTED,
                evidence=relationship.evidence,
            )
        )
    return AcceptedNetworkGraph(
        network=Network(id=network_id, name=network_name, protocol=protocol),
        nodes=tuple(nodes),
        links=tuple(sorted(links, key=lambda item: item.key)),
    )


def accepted_network_graph_data(graph: AcceptedNetworkGraph) -> dict[str, Any]:
    """Return deterministic JSON-compatible accepted network graph data."""
    return {
        "network": {
            "id": graph.network.id,
            "name": graph.network.name,
            "protocol": graph.network.protocol,
        },
        "nodes": [
            {
                "asset_key": node.asset_key,
                "asset_id": node.asset.id,
                "asset_name": node.asset.name,
                "topology_node_keys": list(node.topology_node_keys),
                "interfaces": [interface.__dict__ for interface in node.interfaces],
            }
            for node in graph.nodes
        ],
        "links": [
            {
                "key": link.key,
                "source_asset_key": link.source_asset_key,
                "target_asset_key": link.target_asset_key,
                "source_interface_key": link.source_interface_key,
                "source_port_number": link.source_port_number,
                "target_port_id": link.target_port_id,
                "evidence_class": link.evidence_class.value,
                "evidence": [item.__dict__ for item in link.evidence],
            }
            for link in graph.links
        ],
    }


def accepted_network_graph_json(graph: AcceptedNetworkGraph) -> str:
    """Serialize an accepted network graph deterministically."""
    return json.dumps(accepted_network_graph_data(graph), indent=2) + "\n"
