from twinforge.discovery import (
    classify_snmp_oid,
    count_snmp_oid_families,
    lowered_snmp_oid_families,
)


def test_classifies_standard_enterprise_and_unknown_oid_families():
    assert classify_snmp_oid("1.3.6.1.2.1.1.5.0").key == "mib-2.system"
    assert classify_snmp_oid("1.0.8802.1.1.2.1.4").key == "ieee-lldp"
    enterprise = classify_snmp_oid("1.3.6.1.4.1.9.9.23")
    assert enterprise.key == "enterprise.9"
    assert not enterprise.standard
    assert classify_snmp_oid("1.3.6.1.2.1.99.1").key == "mib-2.99"
    assert classify_snmp_oid("1.3.6.1.2.1.16.1").key == "rmon-mib"
    assert classify_snmp_oid("1.3.6.1.2.1.14.1").key == "ospf-mib"
    assert classify_snmp_oid("1.3.6.1.2.1.191.1").key == "ospfv3-mib"
    assert classify_snmp_oid("2.999.1").key == "other"


def test_counts_families_deterministically_and_identifies_lowering():
    counts = count_snmp_oid_families(
        (
            "1.3.6.1.4.1.9.1",
            "1.3.6.1.2.1.2.2",
            "1.3.6.1.4.1.9.2",
        )
    )

    assert counts == {"enterprise.9": 2, "mib-2.interfaces": 1}
    assert "mib-2.interfaces" in lowered_snmp_oid_families()
    assert "entity-mib" in lowered_snmp_oid_families()
