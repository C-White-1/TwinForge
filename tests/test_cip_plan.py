import json

import pytest

from twinforge.discovery import (
    DiscoveryOperation,
    DiscoveryProviderError,
    DiscoveryScope,
    DiscoveryTarget,
    cip_identity_plan_json,
    plan_cip_identity_capture,
)


def _scope(*targets: DiscoveryTarget) -> DiscoveryScope:
    return DiscoveryScope(
        engagement="controlled lab",
        authorization_reference="LAB-001",
        targets=targets,
        operations=(DiscoveryOperation.CIP_IDENTITY,),
    )


def test_plan_is_deterministic_and_shows_complete_request_budget() -> None:
    scope = _scope(
        DiscoveryTarget(address="192.168.1.20", label="second"),
        DiscoveryTarget(address="192.168.1.10", label="first"),
    )

    document = json.loads(
        cip_identity_plan_json(plan_cip_identity_capture(scope, timeout=3.0))
    )

    assert document["dry_run"] is True
    assert document["authorization_reference"] == "LAB-001"
    assert document["operation"] == "cip_identity"
    assert document["timeout_seconds"] == 3.0
    assert document["total_request_budget"] == 2
    assert [item["address"] for item in document["targets"]] == [
        "192.168.1.10",
        "192.168.1.20",
    ]
    assert all(item["request_budget"] == 1 for item in document["targets"])


def test_plan_rejects_scope_without_identity_authorization() -> None:
    scope = DiscoveryScope(
        engagement="controlled lab",
        authorization_reference="LAB-001",
        targets=(DiscoveryTarget(address="192.168.1.10"),),
        operations=(DiscoveryOperation.SNMP_NETWORK,),
    )

    with pytest.raises(ValueError, match="does not authorize"):
        plan_cip_identity_capture(scope)


def test_plan_applies_live_adapter_target_policy_without_a_transport() -> None:
    scope = _scope(DiscoveryTarget(address="8.8.8.8"))

    with pytest.raises(DiscoveryProviderError, match="public target"):
        plan_cip_identity_capture(scope)


@pytest.mark.parametrize("timeout", [0.0, -1.0, 10.1])
def test_plan_applies_live_adapter_timeout_policy(timeout: float) -> None:
    scope = _scope(DiscoveryTarget(address="127.0.0.1"))

    with pytest.raises(ValueError, match="timeout"):
        plan_cip_identity_capture(scope, timeout=timeout)
