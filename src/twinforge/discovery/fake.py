"""Deterministic offline provider for tests, demos, and design work."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .contracts import (
    CipIdentityObservation,
    DiscoveryProviderError,
    DiscoveryTarget,
    SnmpForwardingEntryObservation,
    SnmpInterfaceObservation,
    SnmpNeighbourObservation,
    SnmpNodeObservation,
)


@dataclass(frozen=True)
class FakeCipIdentity:
    """Fixture values used to construct an observed CIP identity."""

    vendor_id: int
    device_type: int
    product_code: int
    major_revision: int
    minor_revision: int
    status: int
    serial_number: int
    product_name: str
    state: int | None = None
    raw_payload_hex: str | None = None
    raw_attributes: dict[str, str | int | bool | None] | None = None


@dataclass(frozen=True)
class FakeSnmpNode:
    """Fixture values used to construct an observed SNMP node."""

    system_name: str | None = None
    system_description: str | None = None
    system_object_id: str | None = None
    system_contact: str | None = None
    system_location: str | None = None
    uptime_ticks: int | None = None
    interfaces: tuple[SnmpInterfaceObservation, ...] = ()
    neighbours: tuple[SnmpNeighbourObservation, ...] = ()
    forwarding_entries: tuple[SnmpForwardingEntryObservation, ...] = ()
    raw_oids: dict[str, str | int | bool | None] | None = None


class FakeDiscoveryProvider:
    """Return configured evidence without opening sockets or contacting devices."""

    def __init__(
        self,
        identities: dict[str, FakeCipIdentity],
        *,
        snmp_nodes: dict[str, FakeSnmpNode] | None = None,
        failures: dict[str, tuple[str, str]] | None = None,
    ) -> None:
        self._identities = identities
        self._snmp_nodes = snmp_nodes or {}
        self._failures = failures or {}

    def read_cip_identity(
        self,
        target: DiscoveryTarget,
        *,
        captured_at: datetime,
    ) -> CipIdentityObservation:
        """Return fixture evidence associated with ``target.key``."""
        failure = self._failures.get(target.key)
        if failure is not None:
            raise DiscoveryProviderError(*failure)
        try:
            fixture = self._identities[target.key]
        except KeyError as error:
            raise DiscoveryProviderError(
                "identity_fixture_missing",
                f"no fake CIP identity exists for {target.key}",
            ) from error
        return CipIdentityObservation(
            target=target,
            captured_at=captured_at,
            vendor_id=fixture.vendor_id,
            device_type=fixture.device_type,
            product_code=fixture.product_code,
            major_revision=fixture.major_revision,
            minor_revision=fixture.minor_revision,
            status=fixture.status,
            serial_number=fixture.serial_number,
            product_name=fixture.product_name,
            state=fixture.state,
            raw_payload_hex=fixture.raw_payload_hex,
            raw_attributes=fixture.raw_attributes or {},
        )

    def read_snmp_node(
        self,
        target: DiscoveryTarget,
        *,
        captured_at: datetime,
    ) -> SnmpNodeObservation:
        """Return fixture SNMP evidence associated with ``target.key``."""
        failure = self._failures.get(target.key)
        if failure is not None:
            raise DiscoveryProviderError(*failure)
        try:
            fixture = self._snmp_nodes[target.key]
        except KeyError as error:
            raise DiscoveryProviderError(
                "snmp_fixture_missing",
                f"no fake SNMP node exists for {target.key}",
            ) from error
        return SnmpNodeObservation(
            target=target,
            captured_at=captured_at,
            system_name=fixture.system_name,
            system_description=fixture.system_description,
            system_object_id=fixture.system_object_id,
            system_contact=fixture.system_contact,
            system_location=fixture.system_location,
            uptime_ticks=fixture.uptime_ticks,
            interfaces=fixture.interfaces,
            neighbours=fixture.neighbours,
            forwarding_entries=fixture.forwarding_entries,
            raw_oids=fixture.raw_oids or {},
        )
