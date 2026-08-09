from datetime import datetime, timezone

from twinforge.discovery import (
    CipIdentityObservation,
    DiscoveryOperation,
    DiscoverySnapshot,
    DiscoveryTarget,
    NetworkIdentityMatchBasis,
    SnmpInterfaceObservation,
    SnmpNodeObservation,
    TopologyCorrelationResult,
    TopologyNodeCandidate,
    correlate_network_nodes_with_cip_identities,
    network_identity_correlation_json,
)


NOW = datetime(2026, 8, 10, tzinfo=timezone.utc)


def _identity(target: DiscoveryTarget, product_name: str):
    return CipIdentityObservation(
        target=target,
        captured_at=NOW,
        vendor_id=1,
        device_type=14,
        product_code=166,
        major_revision=35,
        minor_revision=17,
        status=96,
        serial_number=1234,
        product_name=product_name,
    )


def test_correlates_neighbour_and_fdb_nodes_with_cip_identity() -> None:
    plc = DiscoveryTarget(address="192.168.1.10")
    snapshot = DiscoverySnapshot(
        schema_version="1.0",
        engagement="authorized lab",
        authorization_reference="LAB-001",
        captured_at=NOW,
        operations=(
            DiscoveryOperation.CIP_IDENTITY,
            DiscoveryOperation.SNMP_NETWORK,
        ),
        targets=(plc,),
        identities=(_identity(plc, "1756-L82E"),),
        snmp_nodes=(
            SnmpNodeObservation(
                target=plc,
                captured_at=NOW,
                interfaces=(
                    SnmpInterfaceObservation(
                        index=1,
                        mac_address="02:00:00:00:00:10",
                    ),
                ),
            ),
        ),
    )
    topology = TopologyCorrelationResult(
        nodes=(
            TopologyNodeCandidate(
                key="chassis:plc",
                addresses=("192.168.1.10",),
                chassis_ids=("02:00:00:00:00:10",),
            ),
            TopologyNodeCandidate(
                key="mac:02:00:00:00:00:10",
                chassis_ids=("02:00:00:00:00:10",),
            ),
        ),
        relationships=(),
    )

    result = correlate_network_nodes_with_cip_identities(snapshot, topology)

    by_node = {item.topology_node_key: item for item in result.correlations}
    assert by_node["chassis:plc"].bases == (
        NetworkIdentityMatchBasis.MANAGEMENT_ADDRESS,
        NetworkIdentityMatchBasis.OBSERVED_INTERFACE_MAC,
    )
    assert by_node["mac:02:00:00:00:00:10"].identity_target_key == plc.key
    assert '"evidence_class": "cross_layer_corroborated"' in (
        network_identity_correlation_json(result)
    )


def test_ambiguous_observed_mac_is_left_unresolved() -> None:
    first = DiscoveryTarget(address="192.168.1.10")
    second = DiscoveryTarget(address="192.168.1.11")
    nodes = tuple(
        SnmpNodeObservation(
            target=target,
            captured_at=NOW,
            interfaces=(
                SnmpInterfaceObservation(
                    index=1,
                    mac_address="02:00:00:00:00:10",
                ),
            ),
        )
        for target in (first, second)
    )
    snapshot = DiscoverySnapshot(
        schema_version="1.0",
        engagement="authorized lab",
        authorization_reference="LAB-001",
        captured_at=NOW,
        operations=(
            DiscoveryOperation.CIP_IDENTITY,
            DiscoveryOperation.SNMP_NETWORK,
        ),
        targets=(first, second),
        identities=(_identity(first, "PLC-A"), _identity(second, "PLC-B")),
        snmp_nodes=nodes,
    )
    topology = TopologyCorrelationResult(
        nodes=(
            TopologyNodeCandidate(
                key="mac:02:00:00:00:00:10",
                chassis_ids=("02:00:00:00:00:10",),
            ),
        ),
        relationships=(),
    )

    result = correlate_network_nodes_with_cip_identities(snapshot, topology)

    assert result.correlations == ()
    assert result.unresolved_topology_node_keys == (
        "mac:02:00:00:00:00:10",
    )
