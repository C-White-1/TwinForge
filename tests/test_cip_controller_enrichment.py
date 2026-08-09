from datetime import datetime, timezone

import pytest

from twinforge.discovery.cip_pycomm3_routed import RoutedExecutionPermit
from twinforge.discovery.cip_routes import CipRouteDeclaration, CipRouteSegment
from twinforge.discovery.contracts import (
    CipIdentityObservation,
    DiscoveryProviderError,
    DiscoveryTarget,
)
from twinforge.discovery.controller import CipControllerObservation
from twinforge.discovery.controller_enrichment import (
    MetadataEnrichedControllerProvider,
)
from twinforge.discovery.controller_metadata import (
    CipControllerMetadataPlan,
    CipControllerMetadataRequest,
    CipMetadataNamespace,
    CipMetadataReadService,
)
from twinforge.discovery.controller_metadata_capture import (
    CipMetadataTransportResult,
    PermittedControllerMetadataExecutor,
)


TIMESTAMP = datetime(2026, 8, 9, tzinfo=timezone.utc)


class _IdentityProvider:
    def __init__(self, vendor_id: int) -> None:
        self.vendor_id = vendor_id
        self.calls = 0

    def read_controller(
        self,
        target: DiscoveryTarget,
        *,
        route: CipRouteDeclaration | None,
        captured_at: datetime,
    ) -> CipControllerObservation:
        self.calls += 1
        return CipControllerObservation(
            target=target,
            route=route,
            captured_at=captured_at,
            identity=CipIdentityObservation(
                target=target,
                captured_at=captured_at,
                vendor_id=self.vendor_id,
                device_type=14,
                product_code=1,
                major_revision=1,
                minor_revision=0,
                status=0,
                serial_number=1,
                product_name="Controller",
            ),
        )


class _MetadataTransport:
    def __init__(self) -> None:
        self.calls = 0

    def read_metadata(
        self,
        target: DiscoveryTarget,
        route: CipRouteDeclaration,
        request: CipControllerMetadataRequest,
        timeout: float,
    ) -> CipMetadataTransportResult:
        self.calls += 1
        return CipMetadataTransportResult(
            general_status=0,
            response_payload=b"unused",
            raw_reply=b"unused",
        )


def test_vendor_mismatch_stops_before_vendor_specific_request() -> None:
    target = DiscoveryTarget(address="192.168.1.10")
    route = CipRouteDeclaration(
        gateway=target,
        segments=(CipRouteSegment(port=1, link=0),),
        maximum_depth=1,
    )
    plan = CipControllerMetadataPlan(
        target=target,
        route=route,
        authorization_reference="LAB-001",
        requests=(
            CipControllerMetadataRequest(
                name="vendor fixture",
                service=CipMetadataReadService.GET_ATTRIBUTES_ALL,
                class_code=0x64,
                instance=1,
                namespace=CipMetadataNamespace.VENDOR_SPECIFIC,
                vendor_id=1,
                specification_reference="Controlled fixture",
            ),
        ),
    )
    permit = RoutedExecutionPermit(
        authorization_reference="LAB-001",
        confirmed_by="operator@example.test",
        confirmed_at=TIMESTAMP,
        allowed_route_keys=(route.key,),
    )
    identity_provider = _IdentityProvider(vendor_id=2)
    metadata_transport = _MetadataTransport()
    executor = PermittedControllerMetadataExecutor(
        plan,
        permit=permit,
        transport=metadata_transport,
    )
    provider = MetadataEnrichedControllerProvider(
        identity_provider,
        executor,
    )

    with pytest.raises(DiscoveryProviderError, match="vendor does not match"):
        provider.read_controller(
            target,
            route=route,
            captured_at=TIMESTAMP,
        )

    assert identity_provider.calls == 1
    assert metadata_transport.calls == 0
