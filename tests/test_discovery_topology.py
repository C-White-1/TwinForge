from datetime import datetime, timezone

from twinforge.discovery import (
    DiscoveryOperation,
    DiscoverySnapshot,
    DiscoveryTarget,
    SnmpForwardingEntryObservation,
    SnmpNeighbourObservation,
    SnmpNodeObservation,
    TopologyConfidence,
    TopologyRelationshipType,
    correlate_topology,
    topology_json,
)


CAPTURED_AT = datetime(2026, 8, 4, 4, 5, 6, tzinfo=timezone.utc)


def snapshot() -> DiscoverySnapshot:
    switch = DiscoveryTarget(address="192.0.2.60", label="lab-switch")
    plc = DiscoveryTarget(address="192.0.2.70", label="lab-plc")
    return DiscoverySnapshot(
        schema_version="1.0",
        engagement="authorized-lab",
        authorization_reference="lab-ticket-9",
        captured_at=CAPTURED_AT,
        operations=(DiscoveryOperation.SNMP_NETWORK,),
        targets=(switch, plc),
        identities=(),
        snmp_nodes=(
            SnmpNodeObservation(
                target=switch,
                captured_at=CAPTURED_AT,
                system_name="SW-LAB-01",
                neighbours=(
                    SnmpNeighbourObservation(
                        protocol="lldp",
                        local_port_number=2,
                        local_interface_index=3,
                        remote_chassis_id="02:00:00:00:00:70",
                        remote_port_id="1",
                        remote_system_name="PLC-LAB-01",
                        management_addresses=("192.0.2.70",),
                        raw_oids={
                            "1.0.8802.1.1.2.1.4.1.1.5.100.2.1": (
                                "020000000070"
                            )
                        },
                    ),
                ),
                forwarding_entries=(
                    SnmpForwardingEntryObservation(
                        mac_address="02:00:00:00:00:70",
                        bridge_port=2,
                        interface_index=3,
                        status=3,
                        raw_oids={
                            "1.3.6.1.2.1.17.4.3.1.1.2.0.0.0.0.112": (
                                "020000000070"
                            )
                        },
                    ),
                    SnmpForwardingEntryObservation(
                        mac_address="02:00:00:00:00:80",
                        bridge_port=1,
                        interface_index=2,
                        status=3,
                        raw_oids={
                            "1.3.6.1.2.1.17.4.3.1.1.2.0.0.0.0.128": (
                                "020000000080"
                            )
                        },
                    ),
                ),
            ),
        ),
    )


def test_correlates_lldp_and_fdb_without_overclaiming_reachability() -> None:
    result = correlate_topology(snapshot())

    reported = next(
        relationship
        for relationship in result.relationships
        if relationship.relationship_type
        is TopologyRelationshipType.REPORTED_NEIGHBOUR
    )
    indirect = next(
        relationship
        for relationship in result.relationships
        if relationship.relationship_type
        is TopologyRelationshipType.MAC_REACHABILITY
    )

    assert reported.target_node_key == "target:192.0.2.70|"
    assert reported.confidence is TopologyConfidence.CORROBORATED
    assert {item.protocol for item in reported.evidence} == {"lldp", "bridge_fdb"}
    assert indirect.target_node_key == "mac:02:00:00:00:00:80"
    assert indirect.confidence is TopologyConfidence.INDIRECT
    assert indirect.target_port_id is None


def test_topology_serialization_is_deterministic() -> None:
    first = correlate_topology(snapshot())
    second = correlate_topology(snapshot())

    assert topology_json(first) == topology_json(second)
    assert topology_json(first).endswith("\n")
