"""Explicitly permitted pycomm3 transport for routed CIP Identity reads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from importlib.metadata import version
from typing import Protocol

from pycomm3 import CIPDriver, ClassCode, Services

from .cip_pycomm3 import (
    CipIdentityReply,
    decode_cip_identity,
    validate_cip_identity_target,
    validate_cip_identity_timeout,
)
from .cip_pycomm3_routes import encode_pycomm3_route
from .cip_routes import CipRouteDeclaration
from .contracts import (
    CipIdentityObservation,
    DiscoveryProviderError,
    DiscoveryTarget,
)
from .controller import CipControllerObservation


@dataclass(frozen=True)
class RoutedExecutionPermit:
    """Attributable confirmation for exact routes in one authorized activity."""

    authorization_reference: str
    confirmed_by: str
    confirmed_at: datetime
    allowed_route_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.authorization_reference.strip():
            raise ValueError("authorization_reference must not be empty")
        if not self.confirmed_by.strip():
            raise ValueError("confirmed_by must not be empty")
        if self.confirmed_at.tzinfo is None:
            raise ValueError("confirmed_at must include a timezone")
        if not self.allowed_route_keys:
            raise ValueError("allowed_route_keys must not be empty")
        if len(self.allowed_route_keys) != len(set(self.allowed_route_keys)):
            raise ValueError("allowed_route_keys must be unique")


class Pycomm3RoutedTransport(Protocol):
    """Injectable boundary for one routed Identity Object request."""

    def read_identity(
        self,
        address: str,
        route_path: bytes,
        timeout: float,
    ) -> CipIdentityReply:
        """Read Identity Object instance 1 through an encoded route."""
        ...


class LivePycomm3RoutedTransport:
    """Issue one UCMM Unconnected Send using an already encoded route."""

    def read_identity(
        self,
        address: str,
        route_path: bytes,
        timeout: float,
    ) -> CipIdentityReply:
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
                unconnected_send=True,
                route_path=route_path,
                name="Routed Identity Object Get_Attributes_All",
                return_response_packet=True,
            )
            if not result:
                detail = result.error or "routed CIP request returned no response"
                raise DiscoveryProviderError("cip_routed_request_failed", str(detail))
            packet = result.value
            payload = getattr(packet, "value", None)
            if not isinstance(payload, bytes):
                raise DiscoveryProviderError(
                    "cip_invalid_reply",
                    "pycomm3 returned a non-byte routed Identity payload",
                )
            raw_reply = getattr(packet, "raw", None)
            return CipIdentityReply(
                payload=payload,
                raw_reply=raw_reply if isinstance(raw_reply, bytes) else None,
            )
        finally:
            driver.close()


class PermittedPycomm3RoutedControllerProvider:
    """Read controller identity only after exact attributable confirmation."""

    def __init__(
        self,
        allowed_routes: tuple[CipRouteDeclaration, ...],
        *,
        authorization_reference: str,
        permit: RoutedExecutionPermit | None = None,
        timeout: float = 2.0,
        transport: Pycomm3RoutedTransport | None = None,
    ) -> None:
        if not allowed_routes:
            raise ValueError("allowed_routes must not be empty")
        if not authorization_reference.strip():
            raise ValueError("authorization_reference must not be empty")
        validate_cip_identity_timeout(timeout)
        keys = [route.key for route in allowed_routes]
        if len(keys) != len(set(keys)):
            raise ValueError("allowed_routes must be unique")
        for route in allowed_routes:
            validate_cip_identity_target(route.gateway)
            encode_pycomm3_route(route)
        self._routes = {route.key: route for route in allowed_routes}
        self._authorization_reference = authorization_reference
        self._permit = permit
        self._timeout = timeout
        self._transport = transport or LivePycomm3RoutedTransport()
        self._requested_routes: set[str] = set()

    def read_controller(
        self,
        target: DiscoveryTarget,
        *,
        route: CipRouteDeclaration | None,
        captured_at: datetime,
    ) -> CipControllerObservation:
        """Read routed Identity evidence; metadata reads remain unsupported."""
        if route is None:
            raise DiscoveryProviderError(
                "cip_route_required",
                "the routed controller provider requires an explicit route",
            )
        if route.gateway.key != target.key or route.key not in self._routes:
            raise DiscoveryProviderError(
                "cip_route_not_allowed",
                "controller route is outside the provider allowlist",
            )
        self._validate_permit(route)
        if route.key in self._requested_routes:
            raise DiscoveryProviderError(
                "cip_routed_request_budget_exceeded",
                "the one-request budget for this routed controller is exhausted",
            )
        self._requested_routes.add(route.key)
        encoding = encode_pycomm3_route(route)
        try:
            reply = self._transport.read_identity(
                target.address,
                encoding.encoded_unconnected_route_path,
                self._timeout,
            )
            decoded, trailing = decode_cip_identity(reply.payload)
        except DiscoveryProviderError:
            raise
        except Exception as error:
            raise DiscoveryProviderError(
                "cip_routed_identity_read_failed",
                f"failed to read routed CIP identity: {error}",
            ) from error
        identity = CipIdentityObservation(
            target=target,
            captured_at=captured_at,
            raw_payload_hex=reply.payload.hex(),
            raw_attributes={
                "adapter": "pycomm3",
                "adapter_version": version("pycomm3"),
                "operation": "routed_get_attributes_all",
                "class_code": 1,
                "instance": 1,
                "route_key": route.key,
                "encoded_route_path_hex": (
                    encoding.encoded_unconnected_route_path.hex()
                ),
                "raw_reply_hex": (
                    reply.raw_reply.hex()
                    if reply.raw_reply is not None
                    else None
                ),
                "trailing_payload_hex": trailing.hex() if trailing else None,
            },
            **decoded,
        )
        return CipControllerObservation(
            target=target,
            captured_at=captured_at,
            identity=identity,
            route=route,
        )

    def _validate_permit(self, route: CipRouteDeclaration) -> None:
        validate_routed_execution(
            self._permit,
            self._authorization_reference,
            (route.key,),
        )


def validate_routed_execution(
    permit: RoutedExecutionPermit | None,
    authorization_reference: str,
    route_keys: tuple[str, ...],
) -> None:
    """Require one matching permit to contain every intended route."""
    if permit is None:
        raise DiscoveryProviderError(
            "cip_routed_execution_not_confirmed",
            "routed CIP execution requires an explicit operator permit",
        )
    if permit.authorization_reference != authorization_reference:
        raise DiscoveryProviderError(
            "cip_authorization_reference_mismatch",
            "operator permit does not match the provider authorization",
        )
    missing = sorted(set(route_keys) - set(permit.allowed_route_keys))
    if missing:
        raise DiscoveryProviderError(
            "cip_route_not_confirmed",
            "route is allowlisted but absent from the operator permit: "
            + ", ".join(missing),
        )
