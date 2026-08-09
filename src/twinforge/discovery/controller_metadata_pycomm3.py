"""Live pycomm3 transport and standard decoders for metadata plans."""

from __future__ import annotations

from pycomm3 import CIPDriver

from .cip_pycomm3 import decode_cip_identity
from .cip_pycomm3_routes import encode_pycomm3_route
from .cip_routes import CipRouteDeclaration
from .contracts import DiscoveryProviderError, DiscoveryTarget
from .controller_metadata import CipControllerMetadataRequest
from .controller_metadata_capture import (
    CipMetadataTransportResult,
    MetadataDecoder,
)


class LivePycomm3MetadataTransport:
    """Issue one exact routed metadata request and retain packet evidence."""

    def read_metadata(
        self,
        target: DiscoveryTarget,
        route: CipRouteDeclaration,
        request: CipControllerMetadataRequest,
        timeout: float,
    ) -> CipMetadataTransportResult:
        if route.gateway.key != target.key:
            raise DiscoveryProviderError(
                "cip_metadata_route_target_mismatch",
                "metadata route gateway does not match its target",
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
                class_code=request.class_code,
                instance=request.instance,
                attribute=(
                    request.attribute if request.attribute is not None else b""
                ),
                connected=False,
                unconnected_send=True,
                route_path=encoding.encoded_unconnected_route_path,
                name=request.name,
                return_response_packet=True,
            )
            packet = result.value
            raw_reply = getattr(packet, "raw", None)
            if not isinstance(raw_reply, bytes):
                raise DiscoveryProviderError(
                    "cip_metadata_no_response",
                    str(result.error or "metadata request returned no packet"),
                )
            general_status, additional_status, payload = _packet_evidence(
                raw_reply
            )
            return CipMetadataTransportResult(
                general_status=general_status,
                additional_status=additional_status,
                response_payload=payload,
                raw_reply=raw_reply,
                message=str(result.error) if result.error else None,
            )
        finally:
            driver.close()


def standard_metadata_decoders() -> dict[str, MetadataDecoder]:
    """Return specification-backed decoders with stable registry names."""
    return {
        "cip_identity_firmware_revision": _decode_identity_firmware_revision,
    }


def _decode_identity_firmware_revision(payload: bytes) -> str:
    decoded, _ = decode_cip_identity(payload)
    return f"{decoded['major_revision']}.{decoded['minor_revision']}"


def _packet_evidence(raw_reply: bytes) -> tuple[int, tuple[int, ...], bytes]:
    """Extract the CIP status section used by pycomm3 SendRRData responses."""
    if len(raw_reply) < 44:
        raise DiscoveryProviderError(
            "cip_metadata_invalid_packet",
            "metadata response packet is shorter than the CIP status header",
        )
    general_status = raw_reply[42]
    additional_word_count = raw_reply[43]
    payload_start = 44 + additional_word_count * 2
    if len(raw_reply) < payload_start:
        raise DiscoveryProviderError(
            "cip_metadata_invalid_packet",
            "metadata additional-status length exceeds the response packet",
        )
    additional_status = tuple(
        int.from_bytes(raw_reply[offset : offset + 2], "little")
        for offset in range(44, payload_start, 2)
    )
    return general_status, additional_status, raw_reply[payload_start:]
