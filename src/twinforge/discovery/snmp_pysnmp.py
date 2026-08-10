"""Bounded PySNMP adapter for the loopback-only SNMPSim laboratory."""

from __future__ import annotations

import asyncio
import ipaddress
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    UsmUserData,
    usmAesCfb128Protocol,
    usmHMAC192SHA256AuthProtocol,
    usmNoAuthProtocol,
    usmNoPrivProtocol,
    walk_cmd,
)

from .contracts import DiscoveryProviderError, DiscoveryTarget, SnmpNodeObservation
from .snmprec import SnmprecValue, build_snmp_node

DEFAULT_OID_ROOTS = (
    "1.3.6.1.2.1.1",  # SNMPv2-MIB system group
    "1.3.6.1.2.1.2",  # IF-MIB interface table
    "1.3.6.1.2.1.4.20",  # legacy IP address table
    "1.3.6.1.2.1.17.1.4",  # bridge-port to ifIndex mapping
    "1.3.6.1.2.1.17.4.3",  # bridge forwarding database
    "1.3.6.1.2.1.31.1.1",  # IF-MIB interface extensions
    "1.3.6.1.2.1.47.1.1.1",  # RFC 6933 ENTITY-MIB physical table
    "1.0.8802.1.1.2.1.3.7",  # LLDP local port table
    "1.0.8802.1.1.2.1.4.1",  # LLDP remote systems table
)


@dataclass(frozen=True)
class LoopbackSnmpPolicy:
    """Safety limits for the initial local SNMPSim experiment."""

    port: int = 1161
    timeout_seconds: float = 1.0
    retries: int = 0
    max_varbinds: int = 512
    max_responses: int = 128
    response_interval_seconds: float = 0.01
    oid_roots: tuple[str, ...] = DEFAULT_OID_ROOTS

    def __post_init__(self) -> None:
        if not 1 <= self.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.retries < 0:
            raise ValueError("retries must not be negative")
        if self.max_varbinds < 1:
            raise ValueError("max_varbinds must be positive")
        if self.max_responses < 1:
            raise ValueError("max_responses must be positive")
        if self.response_interval_seconds <= 0:
            raise ValueError("response_interval_seconds must be positive")
        if not self.oid_roots:
            raise ValueError("at least one OID root is required")
        if len(self.oid_roots) != len(set(self.oid_roots)):
            raise ValueError("OID roots must be unique")
        for root in self.oid_roots:
            if not _is_numeric_oid(root):
                raise ValueError(
                    f"OID root must be a dotted numeric identifier: {root!r}"
                )

    def validate_target(self, target: DiscoveryTarget) -> None:
        """Reject anything except a literal loopback IP address."""
        try:
            address = ipaddress.ip_address(target.address)
        except ValueError as error:
            raise DiscoveryProviderError(
                "snmp_target_not_literal_ip",
                "the loopback SNMP adapter requires a literal IP address",
            ) from error
        if not address.is_loopback:
            raise DiscoveryProviderError(
                "snmp_target_not_loopback",
                "the loopback SNMP adapter refuses non-loopback targets",
            )


def _is_numeric_oid(value: str) -> bool:
    """Return whether a value is a canonical dotted numeric OID."""
    parts = value.split(".")
    return (
        len(parts) >= 2
        and all(part.isascii() and part.isdigit() for part in parts)
        and all(str(int(part)) == part for part in parts)
    )


class SnmpV3SecurityLevel(str, Enum):
    """Supported SNMPv3 USM security levels."""

    NO_AUTH_NO_PRIV = "noAuthNoPriv"
    AUTH_NO_PRIV = "authNoPriv"
    AUTH_PRIV = "authPriv"


@dataclass(frozen=True)
class SnmpV3Credentials:
    """Read-only SNMPv3 USM configuration kept outside discovery evidence."""

    username: str
    authentication_key: str | None = field(default=None, repr=False)
    privacy_key: str | None = field(default=None, repr=False)
    context_name: str = "twinforge-switch"
    security_level: SnmpV3SecurityLevel = SnmpV3SecurityLevel.AUTH_PRIV

    def __post_init__(self) -> None:
        if not self.username:
            raise ValueError("username must not be empty")
        if not self.context_name:
            raise ValueError("context_name must not be empty")
        requires_authentication = self.security_level is not (
            SnmpV3SecurityLevel.NO_AUTH_NO_PRIV
        )
        requires_privacy = self.security_level is SnmpV3SecurityLevel.AUTH_PRIV
        if requires_authentication and (
            self.authentication_key is None
            or len(self.authentication_key) < 8
        ):
            raise ValueError(
                "authentication_key must contain at least 8 characters "
                f"for {self.security_level.value}"
            )
        if requires_privacy and (
            self.privacy_key is None or len(self.privacy_key) < 8
        ):
            raise ValueError(
                "privacy_key must contain at least 8 characters for authPriv"
            )
        if not requires_authentication and self.authentication_key is not None:
            raise ValueError(
                "authentication_key is not applicable to noAuthNoPriv"
            )
        if not requires_privacy and self.privacy_key is not None:
            raise ValueError(
                f"privacy_key is not applicable to {self.security_level.value}"
            )


def _value(record: Any) -> SnmprecValue:
    """Convert a PySNMP value into the static evidence representation."""
    type_name = record.__class__.__name__
    if type_name in {
        "Integer",
        "Integer32",
        "Counter32",
        "Counter64",
        "Gauge32",
        "TimeTicks",
        "Unsigned32",
    }:
        type_codes = {
            "Counter32": "65",
            "Gauge32": "66",
            "Unsigned32": "66",
            "TimeTicks": "67",
            "Counter64": "70",
        }
        return SnmprecValue(type_codes.get(type_name, "2"), int(record))
    if type_name == "ObjectIdentifier":
        return SnmprecValue("6", record.prettyPrint())
    if type_name == "IpAddress":
        return SnmprecValue("64", record.prettyPrint())
    if type_name == "OctetString":
        octets = bytes(record.asOctets())
        try:
            text = octets.decode("utf-8")
        except UnicodeDecodeError:
            return SnmprecValue("4x", octets.hex())
        if any(character < " " and character not in "\t\r\n" for character in text):
            return SnmprecValue("4x", octets.hex())
        return SnmprecValue("4", text)
    return SnmprecValue(type_name, record.prettyPrint())


class PySnmpLoopbackDiscoveryProvider:
    """Read allowlisted OIDs from a local SNMPSim v2c responder."""

    def __init__(
        self,
        community: str = "twinforge-switch",
        *,
        policy: LoopbackSnmpPolicy | None = None,
    ) -> None:
        if not community:
            raise ValueError("community must not be empty")
        self._community = community
        self._policy = policy or LoopbackSnmpPolicy()

    def read_snmp_node(
        self,
        target: DiscoveryTarget,
        *,
        captured_at: datetime,
    ) -> SnmpNodeObservation:
        """Perform a bounded synchronous capture from the local responder."""
        self._policy.validate_target(target)
        try:
            records = asyncio.run(
                _read_records(
                    target,
                    self._policy,
                    CommunityData(
                        "twinforge-loopback",
                        self._community,
                        mpModel=1,
                    ),
                    ContextData(),
                )
            )
        except DiscoveryProviderError:
            raise
        except (OSError, RuntimeError, ValueError) as error:
            raise DiscoveryProviderError(
                "snmp_capture_failed",
                f"SNMP capture failed for {target.key}: {error}",
            ) from error
        return build_snmp_node(target, captured_at, records)



class PySnmpV3LoopbackDiscoveryProvider:
    """Read allowlisted OIDs from local SNMPSim using authenticated privacy."""

    def __init__(
        self,
        credentials: SnmpV3Credentials,
        *,
        policy: LoopbackSnmpPolicy | None = None,
    ) -> None:
        self._credentials = credentials
        self._policy = policy or LoopbackSnmpPolicy()

    def read_snmp_node(
        self,
        target: DiscoveryTarget,
        *,
        captured_at: datetime,
    ) -> SnmpNodeObservation:
        """Perform a bounded SNMPv3 capture from the local responder."""
        self._policy.validate_target(target)
        authentication = _v3_authentication(self._credentials)
        try:
            records = asyncio.run(
                _read_records(
                    target,
                    self._policy,
                    authentication,
                    ContextData(
                        contextName=self._credentials.context_name.encode("utf-8")
                    ),
                )
            )
        except DiscoveryProviderError:
            raise
        except (OSError, RuntimeError, ValueError) as error:
            raise DiscoveryProviderError(
                "snmp_capture_failed",
                f"SNMPv3 capture failed for {target.key}: {error}",
            ) from error
        return build_snmp_node(target, captured_at, records)


def _v3_authentication(credentials: SnmpV3Credentials) -> UsmUserData:
    """Build PySNMP USM data from a validated explicit security level."""
    if credentials.security_level is SnmpV3SecurityLevel.NO_AUTH_NO_PRIV:
        return UsmUserData(
            credentials.username,
            authProtocol=usmNoAuthProtocol,
            privProtocol=usmNoPrivProtocol,
        )
    assert credentials.authentication_key is not None
    if credentials.security_level is SnmpV3SecurityLevel.AUTH_NO_PRIV:
        return UsmUserData(
            credentials.username,
            credentials.authentication_key,
            authProtocol=usmHMAC192SHA256AuthProtocol,
            privProtocol=usmNoPrivProtocol,
        )
    assert credentials.privacy_key is not None
    return UsmUserData(
        credentials.username,
        credentials.authentication_key,
        credentials.privacy_key,
        authProtocol=usmHMAC192SHA256AuthProtocol,
        privProtocol=usmAesCfb128Protocol,
    )


async def _read_records(
    target: DiscoveryTarget,
    policy: LoopbackSnmpPolicy,
    authentication: CommunityData | UsmUserData,
    context: ContextData,
) -> dict[str, SnmprecValue]:
    """Walk allowlisted roots within the shared request budget."""
    engine = SnmpEngine()
    records: dict[str, SnmprecValue] = {}
    responses = 0
    try:
        transport = await UdpTransportTarget.create(
            (target.address, policy.port),
            timeout=policy.timeout_seconds,
            retries=policy.retries,
        )
        for root in policy.oid_roots:
            remaining = policy.max_varbinds - len(records)
            if remaining <= 0:
                raise DiscoveryProviderError(
                    "snmp_request_budget_exhausted",
                    "SNMP varbind budget was exhausted",
                )
            async for error_indication, error_status, error_index, var_binds in walk_cmd(
                engine,
                authentication,
                transport,
                context,
                ObjectType(ObjectIdentity(root)),
                lexicographicMode=False,
                lookupMib=False,
                maxRows=remaining,
            ):
                responses += 1
                if responses > policy.max_responses:
                    raise DiscoveryProviderError(
                        "snmp_response_budget_exhausted",
                        "SNMP response budget was exhausted",
                    )
                if error_indication:
                    raise DiscoveryProviderError(
                        "snmp_transport_error",
                        str(error_indication),
                    )
                if error_status:
                    location = int(error_index or 0)
                    raise DiscoveryProviderError(
                        "snmp_agent_error",
                        f"{error_status} at varbind {location}",
                    )
                for oid, value in var_binds:
                    records[oid.prettyPrint()] = _value(value)
                    if len(records) > policy.max_varbinds:
                        raise DiscoveryProviderError(
                            "snmp_request_budget_exhausted",
                            "SNMP varbind budget was exhausted",
                        )
                await asyncio.sleep(policy.response_interval_seconds)
    finally:
        engine.close_dispatcher()
    return records
