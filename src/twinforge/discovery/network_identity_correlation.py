"""Correlate topology nodes with CIP identities using retained observations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .contracts import DiscoverySnapshot
from .topology import (
    RelationshipEvidenceClass,
    TopologyCorrelationResult,
)


class NetworkIdentityMatchBasis(str, Enum):
    """Exact evidence path connecting a topology node to a CIP identity."""

    SCOPED_TARGET = "scoped_target"
    MANAGEMENT_ADDRESS = "management_address"
    OBSERVED_INTERFACE_MAC = "observed_interface_mac"


@dataclass(frozen=True)
class NetworkIdentityCorrelation:
    """One unambiguous cross-layer match without merging either observation."""

    topology_node_key: str
    identity_target_key: str
    identity_product_name: str
    bases: tuple[NetworkIdentityMatchBasis, ...]
    evidence_class: RelationshipEvidenceClass = (
        RelationshipEvidenceClass.CROSS_LAYER_CORROBORATED
    )


@dataclass(frozen=True)
class NetworkIdentityCorrelationResult:
    """Deterministic cross-layer matches and deliberately unresolved nodes."""

    correlations: tuple[NetworkIdentityCorrelation, ...]
    unresolved_topology_node_keys: tuple[str, ...]


def correlate_network_nodes_with_cip_identities(
    snapshot: DiscoverySnapshot,
    topology: TopologyCorrelationResult,
) -> NetworkIdentityCorrelationResult:
    """Match nodes only through scoped targets, addresses, or observed MACs."""
    identities = {item.target.key: item for item in snapshot.identities}
    identity_keys_by_address: dict[str, set[str]] = {}
    for identity in snapshot.identities:
        identity_keys_by_address.setdefault(identity.target.address, set()).add(
            identity.target.key
        )

    identity_keys_by_mac: dict[str, set[str]] = {}
    for node in snapshot.snmp_nodes:
        if node.target.key not in identities:
            continue
        for interface in node.interfaces:
            if interface.mac_address:
                identity_keys_by_mac.setdefault(
                    interface.mac_address.lower(), set()
                ).add(node.target.key)

    correlations: list[NetworkIdentityCorrelation] = []
    unresolved: list[str] = []
    for node in topology.nodes:
        candidates: dict[str, set[NetworkIdentityMatchBasis]] = {}
        for target_key in node.observed_target_keys:
            if target_key in identities:
                candidates.setdefault(target_key, set()).add(
                    NetworkIdentityMatchBasis.SCOPED_TARGET
                )
        for address in node.addresses:
            for target_key in identity_keys_by_address.get(address, ()):
                candidates.setdefault(target_key, set()).add(
                    NetworkIdentityMatchBasis.MANAGEMENT_ADDRESS
                )
        for chassis_id in node.chassis_ids:
            for target_key in identity_keys_by_mac.get(chassis_id.lower(), ()):
                candidates.setdefault(target_key, set()).add(
                    NetworkIdentityMatchBasis.OBSERVED_INTERFACE_MAC
                )
        if len(candidates) != 1:
            unresolved.append(node.key)
            continue
        target_key, bases = next(iter(candidates.items()))
        correlations.append(
            NetworkIdentityCorrelation(
                topology_node_key=node.key,
                identity_target_key=target_key,
                identity_product_name=identities[target_key].product_name,
                bases=tuple(sorted(bases, key=lambda item: item.value)),
            )
        )
    return NetworkIdentityCorrelationResult(
        correlations=tuple(
            sorted(correlations, key=lambda item: item.topology_node_key)
        ),
        unresolved_topology_node_keys=tuple(sorted(unresolved)),
    )


def network_identity_correlation_data(
    result: NetworkIdentityCorrelationResult,
) -> dict[str, Any]:
    """Return deterministic JSON-compatible cross-layer correlation data."""
    return {
        "correlations": [
            {
                "topology_node_key": item.topology_node_key,
                "identity_target_key": item.identity_target_key,
                "identity_product_name": item.identity_product_name,
                "bases": [basis.value for basis in item.bases],
                "evidence_class": item.evidence_class.value,
            }
            for item in result.correlations
        ],
        "unresolved_topology_node_keys": list(
            result.unresolved_topology_node_keys
        ),
    }


def network_identity_correlation_json(
    result: NetworkIdentityCorrelationResult,
) -> str:
    """Serialize cross-layer correlation evidence deterministically."""
    return json.dumps(network_identity_correlation_data(result), indent=2) + "\n"
