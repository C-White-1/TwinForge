from datetime import datetime, timezone

import pytest

from twinforge.assembly import (
    NetworkGraphLoweringError,
    accepted_network_graph_json,
    lower_accepted_network_graph,
)
from twinforge.discovery import (
    AcceptedTopologyRelationship,
    CandidateDisposition,
    DiscoveryOperation,
    DiscoverySnapshot,
    DiscoveryTarget,
    SnmpInterfaceObservation,
    SnmpNetworkAddressObservation,
    SnmpNodeObservation,
    TopologyAcceptanceResult,
    TopologyCorrelationResult,
    TopologyEvidenceReference,
    TopologyNodeCandidate,
    TopologyRelationshipReview,
)
from twinforge.model import Asset


NOW = datetime(2026, 8, 10, tzinfo=timezone.utc)


def _fixture(interface_index: int | None = 7):
    switch_target = DiscoveryTarget(address="192.168.1.2")
    plc_target = DiscoveryTarget(address="192.168.1.10")
    snapshot = DiscoverySnapshot(
        schema_version="1.0",
        engagement="authorized lab",
        authorization_reference="LAB-001",
        captured_at=NOW,
        operations=(DiscoveryOperation.SNMP_NETWORK,),
        targets=(switch_target, plc_target),
        identities=(),
        snmp_nodes=(
            SnmpNodeObservation(
                target=switch_target,
                captured_at=NOW,
                interfaces=(
                    SnmpInterfaceObservation(
                        index=7,
                        name="uplink7",
                        interface_type=6,
                        mac_address="02:00:00:00:00:07",
                        operational_status=1,
                        addresses=(
                            SnmpNetworkAddressObservation("192.168.1.2", 24),
                        ),
                    ),
                ),
            ),
        ),
    )
    source_node = f"target:{switch_target.key}"
    target_node = f"target:{plc_target.key}"
    topology = TopologyCorrelationResult(
        nodes=(
            TopologyNodeCandidate(
                key=source_node,
                observed_target_keys=(switch_target.key,),
            ),
            TopologyNodeCandidate(
                key=target_node,
                observed_target_keys=(plc_target.key,),
            ),
        ),
        relationships=(),
    )
    review = TopologyRelationshipReview(
        candidate_key="lldp-link",
        disposition=CandidateDisposition.ACCEPT,
        reviewed_by="lab.operator",
        reviewed_at=NOW,
        rationale="Verified laboratory cabling",
        source_asset_key="asset:switch",
        target_asset_key="asset:plc",
    )
    evidence = (
        TopologyEvidenceReference(
            protocol="lldp",
            observation_target=switch_target.key,
            identifier="lldp.remote.1",
            description="LLDP reported neighbour",
        ),
    )
    acceptance = TopologyAcceptanceResult(
        accepted_relationships=(
            AcceptedTopologyRelationship(
                key="accepted:lldp-link",
                candidate_key="lldp-link",
                source_node_key=source_node,
                target_node_key=target_node,
                source_asset_key="asset:switch",
                target_asset_key="asset:plc",
                source_interface_index=interface_index,
                source_port_number=7,
                target_port_id="eth0",
                review=review,
                evidence=evidence,
            ),
        ),
        rejected_candidate_keys=(),
        deferred_candidate_keys=(),
        unreviewed_candidate_keys=(),
    )
    assets = {
        "asset:switch": Asset(id="switch-1", name="Switch"),
        "asset:plc": Asset(id="plc-1", name="PLC"),
    }
    return snapshot, topology, acceptance, assets


def test_lowers_observed_interfaces_and_only_accepted_neighbour_links() -> None:
    snapshot, topology, acceptance, assets = _fixture()

    graph = lower_accepted_network_graph(
        snapshot,
        topology,
        acceptance,
        assets,
        network_id="network-1",
        network_name="Controls LAN",
    )

    switch = next(node for node in graph.nodes if node.asset_key == "asset:switch")
    assert switch.interfaces[0].interface_index == 7
    assert switch.interfaces[0].addresses == ("192.168.1.2",)
    assert graph.links[0].source_interface_key == switch.interfaces[0].key
    assert '"evidence_class": "operator_accepted"' in (
        accepted_network_graph_json(graph)
    )


def test_unknown_durable_asset_is_rejected() -> None:
    snapshot, topology, acceptance, assets = _fixture()
    del assets["asset:plc"]

    with pytest.raises(NetworkGraphLoweringError, match="unknown asset"):
        lower_accepted_network_graph(
            snapshot,
            topology,
            acceptance,
            assets,
            network_id="network-1",
            network_name="Controls LAN",
        )


def test_explicit_interface_reference_must_exist_in_snmp_evidence() -> None:
    snapshot, topology, acceptance, assets = _fixture(interface_index=99)

    with pytest.raises(NetworkGraphLoweringError, match="absent from SNMP"):
        lower_accepted_network_graph(
            snapshot,
            topology,
            acceptance,
            assets,
            network_id="network-1",
            network_name="Controls LAN",
        )
