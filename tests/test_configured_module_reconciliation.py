from datetime import datetime, timezone

from twinforge.discovery import (
    CipIdentityObservation,
    ConfiguredModuleBinding,
    ConfiguredModuleComparisonStatus,
    DiscoveryOperation,
    DiscoverySnapshot,
    DiscoveryTarget,
    SnmpNodeObservation,
    SnmpPhysicalEntityObservation,
    TopologyConfidence,
    configured_module_reconciliation_json,
    reconcile_configured_modules,
)
from twinforge.model import (
    ElectronicKey,
    Identity,
    KeyingMode,
    Module,
    Revision,
    VendorIdentity,
)


CAPTURED_AT = datetime(2026, 8, 5, tzinfo=timezone.utc)


def _snapshot() -> DiscoverySnapshot:
    target = DiscoveryTarget(address="192.0.2.90")
    return DiscoverySnapshot(
        schema_version="1.0",
        engagement="authorized-lab",
        authorization_reference="lab-ticket-module",
        captured_at=CAPTURED_AT,
        operations=(
            DiscoveryOperation.CIP_IDENTITY,
            DiscoveryOperation.SNMP_NETWORK,
        ),
        targets=(target,),
        identities=(
            CipIdentityObservation(
                target=target,
                captured_at=CAPTURED_AT,
                vendor_id=1,
                device_type=7,
                product_code=11,
                major_revision=3,
                minor_revision=1,
                status=0,
                serial_number=12345,
                product_name="1756-IB16",
            ),
        ),
        snmp_nodes=(
            SnmpNodeObservation(
                target=target,
                captured_at=CAPTURED_AT,
                physical_entities=(
                    SnmpPhysicalEntityObservation(
                        index=10,
                        model_name="1756-IB16",
                        serial_number="12345",
                        raw_oids={
                            "1.3.6.1.2.1.47.1.1.1.1.11.10": "12345",
                            "1.3.6.1.2.1.47.1.1.1.1.13.10": "1756-IB16",
                        },
                    ),
                ),
            ),
        ),
    )


def _module(*, product_code: int = 11) -> Module:
    return Module(
        name="DI_Slot2",
        catalog="1756-IB16",
        identity=Identity(
            vendor=VendorIdentity(1, "Allen-Bradley / Rockwell Automation"),
            product_type=7,
            product_code=product_code,
            revision=Revision(3, 1),
        ),
        electronic_key=ElectronicKey(mode=KeyingMode.COMPATIBLE_MODULE),
    )


def test_exact_configured_identity_is_correlated_with_physical_evidence() -> None:
    result = reconcile_configured_modules(
        _snapshot(),
        (
            ConfiguredModuleBinding(
                key="controller/DI_Slot2",
                target_key="192.0.2.90|",
                module=_module(),
            ),
        ),
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.status is ConfiguredModuleComparisonStatus.EXACT
    assert candidate.confidence is TopologyConfidence.CORROBORATED
    assert len(candidate.matched_fields) == 5
    assert candidate.conflicting_fields == ()
    assert candidate.electronic_key_mode == "compatible_module"
    assert candidate.electronic_key_evaluation is not None
    assert candidate.electronic_key_evaluation.verdict.value == "deferred"
    assert candidate.electronic_key_evaluation.typical_compatible_revision is True
    assert candidate.physical_asset_keys == (
        "target:192.0.2.90||entity:10",
    )
    assert {item.protocol for item in candidate.evidence} == {
        "cip_identity",
        "l5x_configured_module",
    }


def test_conflict_is_reported_without_claiming_key_compatibility() -> None:
    result = reconcile_configured_modules(
        _snapshot(),
        (
            ConfiguredModuleBinding(
                key="controller/DI_Slot2",
                target_key="192.0.2.90|",
                module=_module(product_code=99),
            ),
        ),
    )

    candidate = result.candidates[0]
    assert candidate.status is ConfiguredModuleComparisonStatus.CONFLICT
    assert candidate.conflicting_fields == ("module_identity.product_code",)
    assert candidate.confidence is TopologyConfidence.INDIRECT


def test_binding_without_cip_identity_remains_explicit() -> None:
    result = reconcile_configured_modules(
        _snapshot(),
        (
            ConfiguredModuleBinding(
                key="controller/unknown",
                target_key="192.0.2.99|",
                module=_module(),
            ),
        ),
    )

    assert result.candidates == ()
    assert result.targets_without_cip_identity == ("192.0.2.99|",)


def test_configured_module_serialization_is_deterministic() -> None:
    binding = ConfiguredModuleBinding(
        key="controller/DI_Slot2",
        target_key="192.0.2.90|",
        module=_module(),
    )

    first = configured_module_reconciliation_json(
        reconcile_configured_modules(_snapshot(), (binding,))
    )
    second = configured_module_reconciliation_json(
        reconcile_configured_modules(_snapshot(), (binding,))
    )

    assert first == second
    assert first.endswith("\n")
