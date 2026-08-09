import json

import pytest

from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import DiscoveryTarget
from twinforge.discovery.software_inventory_plan import (
    CipRuntimeValueReadPlan,
    CipSoftwareInventoryCapability,
    CipSoftwareInventoryPlan,
    cip_runtime_value_plan_json,
    cip_software_inventory_plan_json,
)


def _target_and_route() -> tuple[DiscoveryTarget, CipRouteDeclaration]:
    target = DiscoveryTarget(address="192.168.1.10")
    return target, CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=0),),
        maximum_depth=1,
    )


def test_software_inventory_plan_cannot_authorize_runtime_values() -> None:
    target, route = _target_and_route()
    plan = CipSoftwareInventoryPlan(
        target=target,
        route=route,
        engagement="TwinForge controlled lab",
        authorization_reference="LAB-001",
        capabilities=(
            CipSoftwareInventoryCapability.PROGRAMS,
            CipSoftwareInventoryCapability.TAG_DEFINITIONS,
        ),
        maximum_requests=12,
    )

    document = json.loads(cip_software_inventory_plan_json(plan))

    assert document["operation"] == "cip_software_inventory"
    assert document["engagement"] == "TwinForge controlled lab"
    assert document["runtime_values_permitted"] is False
    assert document["maximum_requests"] == 12
    assert "tag_paths" not in document


def test_runtime_values_require_a_distinct_approval_and_named_tags() -> None:
    target, route = _target_and_route()
    plan = CipRuntimeValueReadPlan(
        target=target,
        route=route,
        engagement="TwinForge controlled lab",
        authorization_reference="LAB-001",
        runtime_value_approval_reference="LAB-VALUES-002",
        justification="Verify an isolated training controller",
        tag_paths=("Program:MainProgram.MotorRun", "ControllerMode"),
        maximum_requests=2,
    )

    document = json.loads(cip_runtime_value_plan_json(plan))

    assert document["operation"] == "cip_runtime_values"
    assert document["runtime_values_permitted"] is True
    assert document["runtime_value_approval_reference"] == "LAB-VALUES-002"
    assert document["tag_paths"] == [
        "Program:MainProgram.MotorRun",
        "ControllerMode",
    ]


def test_runtime_plan_budget_must_cover_every_named_tag() -> None:
    target, _ = _target_and_route()

    with pytest.raises(ValueError, match="cover every"):
        CipRuntimeValueReadPlan(
            target=target,
            engagement="TwinForge controlled lab",
            authorization_reference="LAB-001",
            runtime_value_approval_reference="LAB-VALUES-002",
            justification="Controlled fixture",
            tag_paths=("TagA", "TagB"),
            maximum_requests=1,
        )


def test_software_capabilities_must_be_unique_and_sorted() -> None:
    target, _ = _target_and_route()

    with pytest.raises(ValueError, match="unique and sorted"):
        CipSoftwareInventoryPlan(
            target=target,
            engagement="TwinForge controlled lab",
            authorization_reference="LAB-001",
            capabilities=(
                CipSoftwareInventoryCapability.TAG_DEFINITIONS,
                CipSoftwareInventoryCapability.PROGRAMS,
            ),
            maximum_requests=2,
        )
