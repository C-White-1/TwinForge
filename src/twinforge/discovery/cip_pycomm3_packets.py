"""Shared extraction of CIP status evidence from pycomm3 response packets."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import DiscoveryProviderError


@dataclass(frozen=True)
class Pycomm3CipPacketEvidence:
    """CIP status section and payload retained from a SendRRData response."""

    general_status: int
    additional_status: tuple[int, ...]
    payload: bytes
    raw_reply: bytes


def extract_pycomm3_cip_packet_evidence(
    raw_reply: bytes,
) -> Pycomm3CipPacketEvidence:
    """Extract the status layout used by pycomm3 SendRRData responses."""
    if len(raw_reply) < 44:
        raise DiscoveryProviderError(
            "cip_invalid_response_packet",
            "response packet is shorter than the CIP status header",
        )
    general_status = raw_reply[42]
    additional_word_count = raw_reply[43]
    payload_start = 44 + additional_word_count * 2
    if len(raw_reply) < payload_start:
        raise DiscoveryProviderError(
            "cip_invalid_response_packet",
            "additional-status length exceeds the response packet",
        )
    additional_status = tuple(
        int.from_bytes(raw_reply[offset : offset + 2], "little")
        for offset in range(44, payload_start, 2)
    )
    return Pycomm3CipPacketEvidence(
        general_status=general_status,
        additional_status=additional_status,
        payload=raw_reply[payload_start:],
        raw_reply=raw_reply,
    )
