"""Bounded pycomm3 adapter for read-only CIP Identity evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from importlib.metadata import version
from ipaddress import IPv4Address, ip_address
from typing import Protocol, TypedDict

from pycomm3 import CIPDriver, ClassCode, Services

from .contracts import (
    CipIdentityObservation,
    DiscoveryProviderError,
    DiscoveryTarget,
)


@dataclass(frozen=True)
class CipIdentityReply:
    """Raw Identity Object reply returned by an injectable transport."""

    payload: bytes
    raw_reply: bytes | None = None


class CipIdentityTransport(Protocol):
    """Transport boundary used to keep decoder tests off the network."""

    def read_identity(self, address: str, timeout: float) -> CipIdentityReply:
        """Read Identity Object instance 1 once from one endpoint."""
        ...


class _DecodedIdentity(TypedDict):
    vendor_id: int
    device_type: int
    product_code: int
    major_revision: int
    minor_revision: int
    status: int
    serial_number: int
    product_name: str
    state: int | None


class Pycomm3IdentityTransport:
    """Perform one unconnected Get_Attributes_All request with pycomm3."""

    def read_identity(self, address: str, timeout: float) -> CipIdentityReply:
        driver = CIPDriver(address)
        driver.socket_timeout = timeout
        try:
            if not driver.open():
                raise DiscoveryProviderError(
                    "cip_connection_failed",
                    f"pycomm3 could not connect to {address}",
                )
            result = driver.generic_message(
                service=Services.get_attributes_all,
                class_code=ClassCode.identity_object,
                instance=1,
                connected=False,
                route_path=False,
                name="Identity Object Get_Attributes_All",
                return_response_packet=True,
            )
            if not result:
                detail = result.error or "CIP request returned no response"
                raise DiscoveryProviderError("cip_request_failed", str(detail))
            packet = result.value
            payload = getattr(packet, "value", None)
            if not isinstance(payload, bytes):
                raise DiscoveryProviderError(
                    "cip_invalid_reply",
                    "pycomm3 returned a non-byte Identity Object payload",
                )
            raw_reply = getattr(packet, "raw", None)
            return CipIdentityReply(
                payload=payload,
                raw_reply=raw_reply if isinstance(raw_reply, bytes) else None,
            )
        finally:
            driver.close()


class Pycomm3CipIdentityProvider:
    """Read one CIP identity per explicitly allowlisted private IPv4 target."""

    def __init__(
        self,
        allowed_targets: tuple[DiscoveryTarget, ...],
        *,
        timeout: float = 2.0,
        transport: CipIdentityTransport | None = None,
    ) -> None:
        if not allowed_targets:
            raise ValueError("allowed_targets must not be empty")
        validate_cip_identity_timeout(timeout)
        keys = [target.key for target in allowed_targets]
        if len(keys) != len(set(keys)):
            raise ValueError("allowed_targets must be unique")
        for target in allowed_targets:
            validate_cip_identity_target(target)
        self._allowed_keys = frozenset(keys)
        self._timeout = timeout
        self._transport = transport or Pycomm3IdentityTransport()
        self._requested_keys: set[str] = set()

    def read_cip_identity(
        self,
        target: DiscoveryTarget,
        *,
        captured_at: datetime,
    ) -> CipIdentityObservation:
        """Capture a target once, retaining decoded and raw evidence."""
        validate_cip_identity_target(target)
        if target.key not in self._allowed_keys:
            raise DiscoveryProviderError(
                "cip_target_not_allowed",
                f"target {target.address} is outside the adapter allowlist",
            )
        if target.key in self._requested_keys:
            raise DiscoveryProviderError(
                "cip_request_budget_exceeded",
                f"the one-request budget for {target.address} is exhausted",
            )
        self._requested_keys.add(target.key)
        try:
            reply = self._transport.read_identity(target.address, self._timeout)
            decoded, trailing = decode_cip_identity(reply.payload)
        except DiscoveryProviderError:
            raise
        except Exception as error:
            raise DiscoveryProviderError(
                "cip_identity_read_failed",
                f"failed to read CIP identity from {target.address}: {error}",
            ) from error

        raw_attributes: dict[str, str | int | bool | None] = {
            "adapter": "pycomm3",
            "adapter_version": version("pycomm3"),
            "operation": "get_attributes_all",
            "class_code": 1,
            "instance": 1,
            "request_number": 1,
            "raw_reply_hex": (
                reply.raw_reply.hex() if reply.raw_reply is not None else None
            ),
            "trailing_payload_hex": trailing.hex() if trailing else None,
        }
        return CipIdentityObservation(
            target=target,
            captured_at=captured_at,
            raw_payload_hex=reply.payload.hex(),
            raw_attributes=raw_attributes,
            **decoded,
        )


def validate_cip_identity_timeout(timeout: float) -> None:
    """Validate the bounded timeout without opening a network connection."""
    if timeout <= 0 or timeout > 10:
        raise ValueError("timeout must be greater than 0 and at most 10 seconds")


def validate_cip_identity_target(target: DiscoveryTarget) -> None:
    """Validate the Identity adapter target policy without opening a socket."""
    if target.route:
        raise DiscoveryProviderError(
            "cip_routes_not_supported",
            "the bounded pycomm3 adapter does not traverse CIP routes",
        )
    try:
        address = ip_address(target.address)
    except ValueError as error:
        raise DiscoveryProviderError(
            "cip_ipv4_literal_required",
            "the bounded pycomm3 adapter requires an IPv4 address literal",
        ) from error
    if not isinstance(address, IPv4Address):
        raise DiscoveryProviderError(
            "cip_ipv4_literal_required",
            "the bounded pycomm3 adapter currently supports IPv4 only",
        )
    if not (address.is_private or address.is_loopback or address.is_link_local):
        raise DiscoveryProviderError(
            "cip_public_target_rejected",
            f"public target {target.address} is not permitted",
        )


def decode_cip_identity(payload: bytes) -> tuple[_DecodedIdentity, bytes]:
    """Decode CIP Identity attributes 1-8 from Get_Attributes_All data."""
    if len(payload) < 15:
        raise DiscoveryProviderError(
            "cip_invalid_identity_payload",
            "Identity Object payload is shorter than the required attributes",
        )
    name_length = payload[14]
    name_end = 15 + name_length
    if len(payload) < name_end:
        raise DiscoveryProviderError(
            "cip_invalid_identity_payload",
            "Identity Object product-name length exceeds the payload",
        )
    try:
        product_name = payload[15:name_end].decode("utf-8")
    except UnicodeDecodeError as error:
        raise DiscoveryProviderError(
            "cip_invalid_identity_payload",
            "Identity Object product name is not valid UTF-8",
        ) from error
    state = payload[name_end] if len(payload) > name_end else None
    trailing_start = name_end + (1 if state is not None else 0)
    return (
        {
            "vendor_id": int.from_bytes(payload[0:2], "little"),
            "device_type": int.from_bytes(payload[2:4], "little"),
            "product_code": int.from_bytes(payload[4:6], "little"),
            "major_revision": payload[6],
            "minor_revision": payload[7],
            "status": int.from_bytes(payload[8:10], "little"),
            "serial_number": int.from_bytes(payload[10:14], "little"),
            "product_name": product_name,
            "state": state,
        },
        payload[trailing_start:],
    )
