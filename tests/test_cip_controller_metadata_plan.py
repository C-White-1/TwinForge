import json

import pytest

from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import DiscoveryTarget
from twinforge.discovery.controller_metadata import (
    CipControllerMetadataPlan,
    CipControllerMetadataRequest,
    CipMetadataNamespace,
    CipMetadataReadService,
    ControllerMetadataField,
    cip_controller_metadata_plan_json,
)


def _target_and_route() -> tuple[DiscoveryTarget, CipRouteDeclaration]:
    target = DiscoveryTarget(address="192.168.1.10")
    route = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=0),),
        maximum_depth=1,
    )
    return target, route


def test_metadata_plan_separates_standard_and_vendor_reads() -> None:
    target, route = _target_and_route()
    plan = CipControllerMetadataPlan(
        target=target,
        route=route,
        authorization_reference="LAB-001",
        requests=(
            CipControllerMetadataRequest(
                name="Identity attributes",
                service=CipMetadataReadService.GET_ATTRIBUTES_ALL,
                class_code=1,
                instance=1,
                namespace=CipMetadataNamespace.STANDARD_CIP,
                specification_reference="CIP Networks Library, Identity Object",
                semantic_field=ControllerMetadataField.FIRMWARE_REVISION,
                decoder="cip_identity_v1",
            ),
            CipControllerMetadataRequest(
                name="Vendor controller name",
                service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
                class_code=0x64,
                instance=1,
                attribute=1,
                namespace=CipMetadataNamespace.VENDOR_SPECIFIC,
                vendor_id=1,
                specification_reference="Authorized vendor fixture pending",
                semantic_field=ControllerMetadataField.LOGICAL_NAME,
            ),
        ),
    )

    document = json.loads(cip_controller_metadata_plan_json(plan))

    assert document["dry_run"] is True
    assert document["operation"] == "cip_controller_metadata"
    assert document["total_request_budget"] == 2
    assert document["runtime_values_permitted"] is False
    assert [item["namespace"] for item in document["requests"]] == [
        "standard_cip",
        "vendor_specific",
    ]
    assert document["requests"][1]["vendor_id"] == 1


def test_get_attribute_single_requires_an_attribute() -> None:
    with pytest.raises(ValueError, match="requires an attribute"):
        CipControllerMetadataRequest(
            name="invalid",
            service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
            class_code=1,
            instance=1,
            namespace=CipMetadataNamespace.STANDARD_CIP,
            specification_reference="CIP specification",
        )


def test_get_attributes_all_rejects_an_attribute() -> None:
    with pytest.raises(ValueError, match="must not specify"):
        CipControllerMetadataRequest(
            name="invalid",
            service=CipMetadataReadService.GET_ATTRIBUTES_ALL,
            class_code=1,
            instance=1,
            attribute=1,
            namespace=CipMetadataNamespace.STANDARD_CIP,
            specification_reference="CIP specification",
        )


def test_vendor_specific_request_requires_vendor_attribution() -> None:
    with pytest.raises(ValueError, match="vendor ID"):
        CipControllerMetadataRequest(
            name="vendor request",
            service=CipMetadataReadService.GET_ATTRIBUTES_ALL,
            class_code=0x64,
            instance=1,
            namespace=CipMetadataNamespace.VENDOR_SPECIFIC,
            specification_reference="Vendor specification",
        )


def test_standard_request_rejects_vendor_attribution() -> None:
    with pytest.raises(ValueError, match="must not specify"):
        CipControllerMetadataRequest(
            name="standard request",
            service=CipMetadataReadService.GET_ATTRIBUTES_ALL,
            class_code=1,
            instance=1,
            namespace=CipMetadataNamespace.STANDARD_CIP,
            vendor_id=1,
            specification_reference="CIP specification",
        )


def test_metadata_plan_rejects_duplicate_object_reads() -> None:
    target, _ = _target_and_route()
    request = CipControllerMetadataRequest(
        name="identity",
        service=CipMetadataReadService.GET_ATTRIBUTES_ALL,
        class_code=1,
        instance=1,
        namespace=CipMetadataNamespace.STANDARD_CIP,
        specification_reference="CIP specification",
    )

    with pytest.raises(ValueError, match="must be unique"):
        CipControllerMetadataPlan(
            target=target,
            authorization_reference="LAB-001",
            requests=(request, request),
        )
