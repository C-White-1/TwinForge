from __future__ import annotations

import json

import pytest

from twinforge.discovery.cip_infrastructure_plan import (
    CipInfrastructureDiscoveryPlan,
    CipInfrastructureObject,
    CipInfrastructureReadRequest,
    cip_infrastructure_plan_json,
)
from twinforge.discovery.contracts import DiscoveryTarget
from twinforge.discovery.controller_metadata import CipMetadataReadService


TARGET = DiscoveryTarget(address="192.0.2.10", label="authorized fixture")


def _request(
    object_type: CipInfrastructureObject,
    instance: int,
    attribute: int,
) -> CipInfrastructureReadRequest:
    return CipInfrastructureReadRequest(
        object_type=object_type,
        instance=instance,
        attribute=attribute,
        service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
        specification_reference="fixture profile section 4",
        purpose="confirm configured object evidence",
    )


def test_serializes_explicit_assembly_and_connection_manager_reads() -> None:
    plan = CipInfrastructureDiscoveryPlan(
        target=TARGET,
        engagement="laboratory-fixture",
        authorization_reference="approval-17",
        requests=(
            _request(CipInfrastructureObject.CONNECTION_MANAGER, 1, 1),
            _request(CipInfrastructureObject.ASSEMBLY, 101, 3),
        ),
        maximum_requests=2,
    )

    document = json.loads(cip_infrastructure_plan_json(plan))

    assert document["runtime_values_permitted"] is False
    assert document["maximum_requests"] == 2
    assert [item["class_code"] for item in document["requests"]] == [4, 6]
    assert document["requests"][0]["instance"] == 101
    assert document["requests"][0]["attribute"] == 3
    assert document["requests"][1]["object_type"] == "connection_manager"


def test_rejects_implicit_or_under_budgeted_discovery() -> None:
    request = _request(CipInfrastructureObject.ASSEMBLY, 100, 3)

    with pytest.raises(ValueError, match="requires a request"):
        CipInfrastructureDiscoveryPlan(
            target=TARGET,
            engagement="laboratory-fixture",
            authorization_reference="approval-17",
            requests=(),
            maximum_requests=1,
        )
    with pytest.raises(ValueError, match="cover every request"):
        CipInfrastructureDiscoveryPlan(
            target=TARGET,
            engagement="laboratory-fixture",
            authorization_reference="approval-17",
            requests=(
                request,
                _request(CipInfrastructureObject.ASSEMBLY, 101, 3),
            ),
            maximum_requests=1,
        )


def test_requires_attribute_for_single_attribute_service() -> None:
    with pytest.raises(ValueError, match="requires an attribute"):
        CipInfrastructureReadRequest(
            object_type=CipInfrastructureObject.ASSEMBLY,
            instance=100,
            service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
            specification_reference="fixture profile section 4",
        )
