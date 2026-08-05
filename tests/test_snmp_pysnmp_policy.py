import pytest

from twinforge.discovery import DiscoveryProviderError, DiscoveryTarget
from twinforge.discovery.snmp_pysnmp import (
    LoopbackSnmpPolicy,
    PySnmpLoopbackDiscoveryProvider,
    SnmpV3Credentials,
)


def test_loopback_policy_accepts_ipv4_and_ipv6_loopback() -> None:
    policy = LoopbackSnmpPolicy()

    policy.validate_target(DiscoveryTarget(address="127.0.0.1"))
    policy.validate_target(DiscoveryTarget(address="::1"))


@pytest.mark.parametrize("address", ["192.0.2.60", "8.8.8.8", "localhost"])
def test_loopback_policy_rejects_non_loopback_or_hostname(address: str) -> None:
    with pytest.raises(DiscoveryProviderError):
        LoopbackSnmpPolicy().validate_target(DiscoveryTarget(address=address))


def test_loopback_policy_validates_request_limits() -> None:
    with pytest.raises(ValueError, match="max_varbinds must be positive"):
        LoopbackSnmpPolicy(max_varbinds=0)


def test_loopback_provider_rejects_empty_community() -> None:
    with pytest.raises(ValueError, match="community must not be empty"):
        PySnmpLoopbackDiscoveryProvider(community="")


def test_snmp_v3_credentials_hide_keys_from_repr() -> None:
    credentials = SnmpV3Credentials(
        username="twinforge-local",
        authentication_key="secret-auth-key",
        privacy_key="secret-privacy-key",
    )

    representation = repr(credentials)

    assert "secret-auth-key" not in representation
    assert "secret-privacy-key" not in representation
    assert "twinforge-local" in representation


def test_snmp_v3_credentials_require_protocol_length_keys() -> None:
    with pytest.raises(ValueError, match="authentication_key"):
        SnmpV3Credentials(
            username="twinforge-local",
            authentication_key="short",
            privacy_key="secret-privacy-key",
        )
