from datetime import datetime, timezone

from twinforge.discovery import (
    DiscoveryOperation,
    DiscoveryScope,
    DiscoveryTarget,
    FakeDiscoveryProvider,
    FakeSnmpNode,
    SnmpForwardingEntryObservation,
    SnmpInterfaceObservation,
    SnmpNeighbourObservation,
    SnmpNetworkAddressObservation,
    capture_snapshot,
    snapshot_data,
    snapshot_json,
)


CAPTURED_AT = datetime(2026, 8, 4, 3, 4, 5, tzinfo=timezone.utc)


def test_snmp_snapshot_preserves_and_orders_network_evidence() -> None:
    switch = DiscoveryTarget(address="192.0.2.60", label="lab-switch")
    second_interface = SnmpInterfaceObservation(
        index=2,
        name="GigabitEthernet1/0/2",
        mac_address="00:11:22:33:44:02",
        admin_status=1,
        operational_status=1,
        raw_oids={"1.3.6.1.2.1.2.2.1.8.2": 1},
    )
    first_interface = SnmpInterfaceObservation(
        index=1,
        name="Vlan1",
        interface_type=53,
        addresses=(
            SnmpNetworkAddressObservation("192.0.2.60", 24),
        ),
    )
    fixture = FakeSnmpNode(
        system_name="SW-LAB-01",
        system_description="Simulated managed switch",
        system_object_id="1.3.6.1.4.1.9.1.9999",
        system_location="TwinForge laboratory",
        uptime_ticks=123456,
        interfaces=(second_interface, first_interface),
        neighbours=(
            SnmpNeighbourObservation(
                protocol="lldp",
                local_port_number=2,
                remote_chassis_id="00:aa:bb:cc:dd:ee",
                remote_port_id="1",
                local_interface_index=2,
                remote_system_name="PLC-LAB-01",
                management_addresses=("192.0.2.70",),
                raw_oids={"1.0.8802.1.1.2.example": "PLC-LAB-01"},
            ),
        ),
        forwarding_entries=(
            SnmpForwardingEntryObservation(
                mac_address="00:aa:bb:cc:dd:ee",
                bridge_port=2,
                interface_index=2,
                vlan_id=1,
                status=3,
            ),
        ),
        raw_oids={"1.3.6.1.2.1.1.5.0": "SW-LAB-01"},
    )
    scope = DiscoveryScope(
        engagement="authorized-snmp-lab",
        authorization_reference="lab-ticket-7",
        targets=(switch,),
        operations=(DiscoveryOperation.SNMP_NETWORK,),
    )
    provider = FakeDiscoveryProvider({}, snmp_nodes={switch.key: fixture})

    snapshot = capture_snapshot(
        scope,
        provider,
        snmp_provider=provider,
        captured_at=CAPTURED_AT,
    )
    repeated = capture_snapshot(
        scope,
        provider,
        snmp_provider=provider,
        captured_at=CAPTURED_AT,
    )
    data = snapshot_data(snapshot)

    assert snapshot.identities == ()
    assert snapshot.snmp_nodes[0].raw_oids == {
        "1.3.6.1.2.1.1.5.0": "SW-LAB-01"
    }
    assert [item["index"] for item in data["snmp_nodes"][0]["interfaces"]] == [
        1,
        2,
    ]
    assert data["snmp_nodes"][0]["neighbours"][0]["protocol"] == "lldp"
    assert snapshot_json(snapshot) == snapshot_json(repeated)


def test_missing_snmp_provider_is_recorded_for_each_target() -> None:
    switch = DiscoveryTarget(address="192.0.2.80")
    scope = DiscoveryScope(
        engagement="authorized-snmp-lab",
        authorization_reference="lab-ticket-8",
        targets=(switch,),
        operations=(DiscoveryOperation.SNMP_NETWORK,),
    )

    snapshot = capture_snapshot(
        scope,
        FakeDiscoveryProvider({}),
        captured_at=CAPTURED_AT,
    )

    assert snapshot.snmp_nodes == ()
    assert snapshot.diagnostics[0].code == "snmp_provider_missing"
