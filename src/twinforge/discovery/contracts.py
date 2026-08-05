"""Vendor-neutral contracts for authorized, read-only device discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DiscoveryOperation(str, Enum):
    """Evidence-producing operations permitted by Discovery Snapshot v1."""

    CIP_IDENTITY = "cip_identity"
    SNMP_NETWORK = "snmp_network"


class DiscoveryTarget(BaseModel):
    """One explicitly authorized endpoint and optional CIP route."""

    model_config = ConfigDict(frozen=True)

    address: str = Field(min_length=1)
    route: tuple[int, ...] = ()
    label: str | None = None

    @field_validator("address")
    @classmethod
    def address_must_be_trimmed(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("address must not contain surrounding whitespace")
        return value

    @field_validator("route")
    @classmethod
    def route_values_must_not_be_negative(
        cls,
        value: tuple[int, ...],
    ) -> tuple[int, ...]:
        if any(segment < 0 for segment in value):
            raise ValueError("route values must not be negative")
        return value

    @property
    def key(self) -> str:
        """Return a stable endpoint key suitable for evidence correlation."""
        route = "/".join(str(segment) for segment in self.route)
        return f"{self.address}|{route}"


class DiscoveryScope(BaseModel):
    """Explicit authorization boundary for one discovery capture."""

    model_config = ConfigDict(frozen=True)

    engagement: str = Field(min_length=1)
    authorization_reference: str = Field(min_length=1)
    targets: tuple[DiscoveryTarget, ...] = Field(min_length=1)
    operations: tuple[DiscoveryOperation, ...] = (
        DiscoveryOperation.CIP_IDENTITY,
    )

    @field_validator("engagement", "authorization_reference")
    @classmethod
    def text_must_be_trimmed(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("scope text must not contain surrounding whitespace")
        return value

    @field_validator("targets")
    @classmethod
    def targets_must_be_unique(
        cls,
        value: tuple[DiscoveryTarget, ...],
    ) -> tuple[DiscoveryTarget, ...]:
        keys = [target.key for target in value]
        if len(keys) != len(set(keys)):
            raise ValueError("scope targets must be unique")
        return value


@dataclass(frozen=True)
class CipIdentityObservation:
    """Observed CIP Identity Object evidence without model inference."""

    target: DiscoveryTarget
    captured_at: datetime
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
    raw_attributes: dict[str, str | int | bool | None] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must include a timezone")
        numeric = (
            self.vendor_id,
            self.device_type,
            self.product_code,
            self.major_revision,
            self.minor_revision,
            self.status,
            self.serial_number,
        )
        if any(value < 0 for value in numeric):
            raise ValueError("CIP identity numeric fields must not be negative")


@dataclass(frozen=True)
class SnmpNetworkAddressObservation:
    """Address observed on an SNMP interface."""

    address: str
    prefix_length: int | None = None


@dataclass(frozen=True)
class SnmpInterfaceObservation:
    """Interface-table evidence retained using the agent's numeric states."""

    index: int
    name: str | None = None
    description: str | None = None
    interface_type: int | None = None
    mac_address: str | None = None
    speed_bps: int | None = None
    admin_status: int | None = None
    operational_status: int | None = None
    addresses: tuple[SnmpNetworkAddressObservation, ...] = ()
    raw_oids: dict[str, str | int | bool | None] = field(default_factory=dict)


@dataclass(frozen=True)
class SnmpNeighbourObservation:
    """LLDP or equivalent neighbour evidence reported by an SNMP agent."""

    protocol: str
    local_port_number: int
    remote_chassis_id: str
    remote_port_id: str
    local_interface_index: int | None = None
    remote_system_name: str | None = None
    management_addresses: tuple[str, ...] = ()
    raw_oids: dict[str, str | int | bool | None] = field(default_factory=dict)


@dataclass(frozen=True)
class SnmpForwardingEntryObservation:
    """One MAC forwarding entry observed from a bridge MIB."""

    mac_address: str
    bridge_port: int
    interface_index: int | None = None
    vlan_id: int | None = None
    status: int | None = None
    raw_oids: dict[str, str | int | bool | None] = field(default_factory=dict)


@dataclass(frozen=True)
class SnmpPhysicalEntityObservation:
    """RFC 6933 physical-entity evidence with numeric IANA class retained."""

    index: int
    description: str | None = None
    vendor_type_oid: str | None = None
    contained_in: int | None = None
    physical_class: int | None = None
    parent_relative_position: int | None = None
    name: str | None = None
    hardware_revision: str | None = None
    firmware_revision: str | None = None
    software_revision: str | None = None
    serial_number: str | None = None
    manufacturer_name: str | None = None
    model_name: str | None = None
    alias: str | None = None
    asset_id: str | None = None
    is_fru: bool | None = None
    manufacturing_date: str | None = None
    uris: tuple[str, ...] = ()
    uuid: str | None = None
    raw_oids: dict[str, str | int | bool | None] = field(default_factory=dict)


@dataclass(frozen=True)
class SnmpNodeObservation:
    """SNMP evidence for one managed node without topology inference."""

    target: DiscoveryTarget
    captured_at: datetime
    system_name: str | None = None
    system_description: str | None = None
    system_object_id: str | None = None
    system_contact: str | None = None
    system_location: str | None = None
    uptime_ticks: int | None = None
    interfaces: tuple[SnmpInterfaceObservation, ...] = ()
    neighbours: tuple[SnmpNeighbourObservation, ...] = ()
    forwarding_entries: tuple[SnmpForwardingEntryObservation, ...] = ()
    physical_entities: tuple[SnmpPhysicalEntityObservation, ...] = ()
    raw_oids: dict[str, str | int | bool | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must include a timezone")
        if self.uptime_ticks is not None and self.uptime_ticks < 0:
            raise ValueError("uptime_ticks must not be negative")


class DiscoveryDiagnosticSeverity(str, Enum):
    """Severity assigned to evidence-capture diagnostics."""

    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class DiscoveryDiagnostic:
    """A target-specific problem encountered during capture."""

    target: DiscoveryTarget
    severity: DiscoveryDiagnosticSeverity
    code: str
    message: str


@dataclass(frozen=True)
class DiscoverySnapshot:
    """Deterministic collection of observations and capture diagnostics."""

    schema_version: str
    engagement: str
    authorization_reference: str
    captured_at: datetime
    operations: tuple[DiscoveryOperation, ...]
    targets: tuple[DiscoveryTarget, ...]
    identities: tuple[CipIdentityObservation, ...]
    snmp_nodes: tuple[SnmpNodeObservation, ...] = ()
    diagnostics: tuple[DiscoveryDiagnostic, ...] = ()


class DiscoveryProviderError(RuntimeError):
    """Expected failure reported by a discovery provider."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class CipDiscoveryProvider(Protocol):
    """Read-only CIP evidence source implemented by offline or live adapters."""

    def read_cip_identity(
        self,
        target: DiscoveryTarget,
        *,
        captured_at: datetime,
    ) -> CipIdentityObservation:
        """Read the CIP Identity Object for one authorized target."""
        ...


class SnmpDiscoveryProvider(Protocol):
    """Read-only SNMP evidence source supplied by an offline or live adapter."""

    def read_snmp_node(
        self,
        target: DiscoveryTarget,
        *,
        captured_at: datetime,
    ) -> SnmpNodeObservation:
        """Read configured system, interface, neighbour and bridge evidence."""
        ...
