"""Vendor-neutral FDT/DTM (IEC 62453) device-configuration model.

A Device Type Manager (DTM) is a PC-side configuration tool's own record
of one device or communication channel's protocol settings. Confirmed,
against real SCADAPack `.prj` fixtures, to be genuinely independent from
any live connection the configuration PC itself holds (see
docs/architecture/scadapack-rcz-format.md): one real project's
`STATION.CTX` "PLC ADDRESS" (the IDE's own download/monitor link) and its
`.prj`'s own DTM `AddressInfo` (the device's configured field protocol) are
different protocols at different addresses in the same fixture -- not the
same connection recorded twice.

Deliberately not modeled as `CommunicationInterface`/`Connection`
(Rockwell/CIP-shaped: packet intervals, `unicast`, CIP object/instance/
attribute services) -- none of that applies here, and forcing this data
through those fields would mean nearly everything landing in an untyped
metadata dict rather than a real typed field.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .asset import Asset


@dataclass(frozen=True, kw_only=True)
class ProtocolVariant:
    """One protocol/transport combination a DTM's own catalog declares
    support for -- not a claim this project configured or uses it.
    """

    protocol_id: str
    protocol_name: str


@dataclass(frozen=True, kw_only=True)
class ConfiguredProtocolAddress:
    """One protocol variant this project actually configured, with its
    addressing detail and whether it is the active selection.

    Field names follow the source's own DataContract element names
    (`AddressingModeSelection`, `TargetAddress`, ...) rather than being
    renamed to a protocol-neutral vocabulary this project hasn't evidenced
    across enough protocol families yet to generalize confidently.
    """

    protocol_id: str
    protocol_name: str | None = None
    active: bool = False
    addressing_mode: str | None = None
    target_address: str | None = None
    ip_address: str | None = None
    port: int | None = None
    device_serial_number: str | None = None
    local_connection: bool | None = None


@dataclass(kw_only=True)
class DeviceTypeManager(Asset):
    """One FDT/DTM entry from a project: a PC-side tool's own configuration
    record for one device or communication channel -- its own declared
    protocol catalog, and whichever variant(s) this project actually
    configured with real addressing.
    """

    product_name: str | None = None
    product_manufacturer: str | None = None
    supported_protocols: list[ProtocolVariant] = field(default_factory=list)
    configured_protocols: list[ConfiguredProtocolAddress] = field(default_factory=list)
