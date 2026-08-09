from datetime import datetime, timezone

import pytest

from twinforge.discovery import (
    DiscoveryOperation,
    DiscoveryProviderError,
    DiscoveryScope,
    DiscoveryTarget,
    capture_snapshot,
)
from twinforge.discovery.cip_pycomm3 import (
    CipIdentityReply,
    Pycomm3CipIdentityProvider,
)


PAYLOAD = bytes.fromhex(
    "01000e00a60023116000785634120a436f6e74726f6c6c657203"
)


class FakeTransport:
    def __init__(self, reply: CipIdentityReply | Exception) -> None:
        self.reply = reply
        self.calls: list[tuple[str, float]] = []

    def read_identity(self, address: str, timeout: float) -> CipIdentityReply:
        self.calls.append((address, timeout))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def test_provider_decodes_identity_and_preserves_raw_evidence() -> None:
    target = DiscoveryTarget(address="192.168.1.10")
    transport = FakeTransport(CipIdentityReply(PAYLOAD, b"raw"))
    provider = Pycomm3CipIdentityProvider((target,), transport=transport)

    identity = provider.read_cip_identity(
        target,
        captured_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
    )

    assert transport.calls == [("192.168.1.10", 2.0)]
    assert identity.vendor_id == 1
    assert identity.device_type == 14
    assert identity.product_code == 166
    assert (identity.major_revision, identity.minor_revision) == (35, 17)
    assert identity.status == 0x60
    assert identity.serial_number == 0x12345678
    assert identity.product_name == "Controller"
    assert identity.state == 3
    assert identity.raw_payload_hex == PAYLOAD.hex()
    assert identity.raw_attributes["raw_reply_hex"] == b"raw".hex()
    assert identity.raw_attributes["adapter"] == "pycomm3"


def test_provider_rejects_target_outside_exact_allowlist() -> None:
    allowed = DiscoveryTarget(address="192.168.1.10")
    provider = Pycomm3CipIdentityProvider(
        (allowed,),
        transport=FakeTransport(CipIdentityReply(PAYLOAD)),
    )

    with pytest.raises(DiscoveryProviderError, match="outside.*allowlist"):
        provider.read_cip_identity(
            DiscoveryTarget(address="192.168.1.11"),
            captured_at=datetime.now(timezone.utc),
        )


@pytest.mark.parametrize(
    "target",
    [
        DiscoveryTarget(address="8.8.8.8"),
        DiscoveryTarget(address="plc.example"),
        DiscoveryTarget(address="192.168.1.10", route=(1, 0)),
    ],
)
def test_provider_rejects_public_hostnames_and_routes(target: DiscoveryTarget) -> None:
    with pytest.raises(DiscoveryProviderError):
        Pycomm3CipIdentityProvider((target,))


def test_provider_enforces_one_request_per_target() -> None:
    target = DiscoveryTarget(address="127.0.0.1")
    transport = FakeTransport(CipIdentityReply(PAYLOAD))
    provider = Pycomm3CipIdentityProvider((target,), transport=transport)
    timestamp = datetime.now(timezone.utc)

    provider.read_cip_identity(target, captured_at=timestamp)
    with pytest.raises(DiscoveryProviderError, match="budget"):
        provider.read_cip_identity(target, captured_at=timestamp)

    assert len(transport.calls) == 1


def test_transport_failure_becomes_capture_diagnostic() -> None:
    target = DiscoveryTarget(address="10.0.0.5")
    provider = Pycomm3CipIdentityProvider(
        (target,),
        transport=FakeTransport(RuntimeError("offline")),
    )
    scope = DiscoveryScope(
        engagement="lab",
        authorization_reference="permit-1",
        targets=(target,),
        operations=(DiscoveryOperation.CIP_IDENTITY,),
    )

    snapshot = capture_snapshot(scope, provider)

    assert snapshot.identities == ()
    assert snapshot.diagnostics[0].code == "cip_identity_read_failed"
    assert "offline" in snapshot.diagnostics[0].message
