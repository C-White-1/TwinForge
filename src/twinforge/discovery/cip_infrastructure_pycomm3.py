"""Read-only pycomm3 transport for planned CIP infrastructure requests."""

from __future__ import annotations

from pycomm3 import CIPDriver

from .cip_infrastructure_capture import CipInfrastructureTransportResult
from .cip_infrastructure_plan import CipInfrastructureReadRequest
from .cip_pycomm3_packets import extract_pycomm3_cip_packet_evidence
from .cip_pycomm3_routes import encode_pycomm3_route
from .cip_routes import CipRouteDeclaration
from .contracts import DiscoveryProviderError, DiscoveryTarget


class LivePycomm3InfrastructureTransport:
    """Issue one exact routed Assembly or Connection Manager read."""

    def read_infrastructure(
        self,
        target: DiscoveryTarget,
        route: CipRouteDeclaration,
        request: CipInfrastructureReadRequest,
        timeout: float,
    ) -> CipInfrastructureTransportResult:
        """Execute the planned read and preserve packet-level evidence."""
        if route.gateway.key != target.key:
            raise DiscoveryProviderError(
                "cip_infrastructure_route_target_mismatch",
                "infrastructure route gateway does not match its target",
            )
        encoding = encode_pycomm3_route(route)
        driver = CIPDriver(target.address)
        driver.socket_timeout = timeout
        try:
            if not driver.open():
                raise DiscoveryProviderError(
                    "cip_connection_failed",
                    f"pycomm3 could not connect to {target.address}",
                )
            result = driver.generic_message(
                service=request.service.value,
                class_code=request.object_type.class_code,
                instance=request.instance,
                attribute=(
                    request.attribute if request.attribute is not None else b""
                ),
                connected=False,
                unconnected_send=True,
                route_path=encoding.encoded_unconnected_route_path,
                name=(
                    f"{request.object_type.value} instance {request.instance} "
                    f"{request.service.name.lower()}"
                ),
                return_response_packet=True,
            )
            packet = result.value
            raw_reply = getattr(packet, "raw", None)
            if not isinstance(raw_reply, bytes):
                raise DiscoveryProviderError(
                    "cip_infrastructure_no_response",
                    str(
                        result.error
                        or "infrastructure request returned no packet"
                    ),
                )
            evidence = extract_pycomm3_cip_packet_evidence(raw_reply)
            return CipInfrastructureTransportResult(
                general_status=evidence.general_status,
                additional_status=evidence.additional_status,
                response_payload=evidence.payload,
                raw_reply=raw_reply,
                message=str(result.error) if result.error else None,
            )
        finally:
            driver.close()
