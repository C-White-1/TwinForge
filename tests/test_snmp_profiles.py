from twinforge.discovery import (
    OSPF_V2_ROUTED_TOPOLOGY_PROFILE,
    OSPF_V3_ROUTED_TOPOLOGY_PROFILE,
    RMON_ETHERNET_STATISTICS_PROFILE,
    SnmpObservationProfileStatus,
    optional_snmp_observation_profiles,
)
from twinforge.discovery.snmp_pysnmp import DEFAULT_OID_ROOTS


def test_rmon_statistics_is_separate_opt_in_evidence_profile() -> None:
    profile = RMON_ETHERNET_STATISTICS_PROFILE

    assert profile.oid_roots == ("1.3.6.1.2.1.16.1.1",)
    assert not profile.enabled_by_default
    assert profile.status is SnmpObservationProfileStatus.EVIDENCE_ONLY
    assert all(not root.startswith("1.3.6.1.2.1.16") for root in DEFAULT_OID_ROOTS)


def test_optional_profiles_are_deterministic() -> None:
    profiles = optional_snmp_observation_profiles()

    assert tuple(item.key for item in profiles) == tuple(
        sorted(item.key for item in profiles)
    )


def test_ospf_profiles_are_opt_in_routed_evidence_only() -> None:
    for profile in (
        OSPF_V2_ROUTED_TOPOLOGY_PROFILE,
        OSPF_V3_ROUTED_TOPOLOGY_PROFILE,
    ):
        assert not profile.enabled_by_default
        assert profile.status is SnmpObservationProfileStatus.EVIDENCE_ONLY
        assert "routed-topology phase" in profile.limitations[-1]
        assert all(root not in DEFAULT_OID_ROOTS for root in profile.oid_roots)
