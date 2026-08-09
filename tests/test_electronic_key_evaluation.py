from datetime import datetime, timezone

import pytest

from twinforge.discovery.contracts import CipIdentityObservation, DiscoveryTarget
from twinforge.discovery.electronic_key_evaluation import (
    ElectronicKeyVerdict,
    evaluate_electronic_key,
)
from twinforge.model import (
    ElectronicKey,
    Identity,
    KeyingMode,
    Module,
    Revision,
    VendorIdentity,
)


def _identity(*, major: int = 3, minor: int = 1) -> Identity:
    return Identity(
        vendor=VendorIdentity(1),
        product_type=7,
        product_code=11,
        revision=Revision(major, minor),
    )


def _module(mode: KeyingMode, identity: Identity | None = None) -> Module:
    return Module(
        name="DI_Slot2",
        catalog="1756-IB16",
        identity=_identity(),
        electronic_key=ElectronicKey(mode=mode, identity=identity),
    )


def _observed(*, major: int = 3, minor: int = 1) -> CipIdentityObservation:
    return CipIdentityObservation(
        target=DiscoveryTarget(address="192.0.2.10"),
        captured_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
        vendor_id=1,
        device_type=7,
        product_code=11,
        major_revision=major,
        minor_revision=minor,
        status=0,
        serial_number=1,
        product_name="Sanitized Module",
    )


@pytest.mark.parametrize(
    ("observed", "verdict"),
    (
        (_observed(), ElectronicKeyVerdict.SATISFIED),
        (_observed(minor=2), ElectronicKeyVerdict.REJECTED),
    ),
)
def test_exact_match_has_a_definitive_field_equality_result(
    observed: CipIdentityObservation,
    verdict: ElectronicKeyVerdict,
) -> None:
    result = evaluate_electronic_key(
        _module(KeyingMode.EXACT_MATCH),
        observed,
    )

    assert result.verdict is verdict


def test_exact_match_defers_when_required_identity_is_incomplete() -> None:
    module = _module(
        KeyingMode.EXACT_MATCH,
        Identity(vendor=VendorIdentity(1)),
    )

    result = evaluate_electronic_key(module, _observed())

    assert result.verdict is ElectronicKeyVerdict.DEFERRED
    assert result.unavailable_fields == (
        "device_type",
        "product_code",
        "major_revision",
        "minor_revision",
    )


def test_disabled_keying_is_reported_without_claiming_identity_compatibility() -> None:
    result = evaluate_electronic_key(
        _module(KeyingMode.DISABLED),
        _observed(),
    )

    assert result.verdict is ElectronicKeyVerdict.DISABLED
    assert result.matched_fields == ()


@pytest.mark.parametrize(
    ("observed", "typical"),
    (
        (_observed(major=3, minor=2), True),
        (_observed(major=4, minor=0), True),
        (_observed(major=2, minor=99), False),
    ),
)
def test_compatible_module_retains_advisory_revision_result_but_defers(
    observed: CipIdentityObservation,
    typical: bool,
) -> None:
    result = evaluate_electronic_key(
        _module(KeyingMode.COMPATIBLE_MODULE),
        observed,
    )

    assert result.verdict is ElectronicKeyVerdict.DEFERRED
    assert result.typical_compatible_revision is typical
    assert "decided by the device" in result.rationale


def test_custom_and_unknown_modes_defer_without_inventing_rules() -> None:
    custom = evaluate_electronic_key(
        _module(KeyingMode.CUSTOM, _identity()),
        _observed(),
    )
    unknown_module = Module(
        name="Future",
        catalog="FutureModule",
        identity=_identity(),
        electronic_key=ElectronicKey(unknown_mode="FutureMode"),
    )
    unknown = evaluate_electronic_key(unknown_module, _observed())

    assert custom.verdict is ElectronicKeyVerdict.DEFERRED
    assert unknown.verdict is ElectronicKeyVerdict.DEFERRED
    assert unknown.mode == "FutureMode"
