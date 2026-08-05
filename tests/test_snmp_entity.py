from datetime import datetime, timezone

from twinforge.discovery import (
    DiscoveryTarget,
    SnmpPhysicalEntityObservation,
    SnmprecValue,
    build_snmp_node,
    validate_entity_containment,
)


BASE = "1.3.6.1.2.1.47.1.1.1.1"


def test_lowers_rfc6933_physical_entities_and_preserves_raw_evidence():
    records = {
        f"{BASE}.1.100": SnmprecValue("2", 100),
        f"{BASE}.2.100": SnmprecValue("4", "Main chassis"),
        f"{BASE}.4.100": SnmprecValue("2", 0),
        f"{BASE}.5.100": SnmprecValue("2", 3),
        f"{BASE}.7.100": SnmprecValue("4", "Chassis 1"),
        f"{BASE}.12.100": SnmprecValue("4", "Example Corp"),
        f"{BASE}.13.100": SnmprecValue("4", "EX-1000"),
        f"{BASE}.16.100": SnmprecValue("2", 1),
        f"{BASE}.18.100": SnmprecValue("4", "urn:example:asset docs:100"),
        f"{BASE}.19.100": SnmprecValue("4", "00112233445566778899aabbccddeeff"),
        f"{BASE}.1.200": SnmprecValue("2", 200),
        f"{BASE}.2.200": SnmprecValue("4", "I/O module"),
        f"{BASE}.4.200": SnmprecValue("2", 100),
        f"{BASE}.5.200": SnmprecValue("2", 9),
        f"{BASE}.6.200": SnmprecValue("2", 2),
    }

    node = build_snmp_node(
        DiscoveryTarget(address="fixture:entity"),
        datetime(2026, 8, 5, tzinfo=timezone.utc),
        records,
    )

    assert len(node.physical_entities) == 2
    chassis, module = node.physical_entities
    assert chassis.physical_class == 3
    assert chassis.manufacturer_name == "Example Corp"
    assert chassis.is_fru is True
    assert chassis.uris == ("urn:example:asset", "docs:100")
    assert chassis.uuid == "00112233445566778899aabbccddeeff"
    assert module.contained_in == 100
    assert module.parent_relative_position == 2
    assert f"{BASE}.5.200" in module.raw_oids
    assert validate_entity_containment(node.physical_entities) == ()


def test_reports_missing_self_and_cyclic_containment_without_mutation():
    entities = (
        SnmpPhysicalEntityObservation(index=1, contained_in=1),
        SnmpPhysicalEntityObservation(index=2, contained_in=99),
        SnmpPhysicalEntityObservation(index=3, contained_in=4),
        SnmpPhysicalEntityObservation(index=4, contained_in=3),
    )

    issues = validate_entity_containment(entities)

    assert {issue.code for issue in issues} == {
        "self_parent",
        "missing_parent",
        "containment_cycle",
    }
