"""Vendor-neutral device communication interfaces and services."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .asset import Asset
from .connection import Connection
from .source_extension import SourceExtension


class CommunicationRole(str, Enum):
    """A protocol-neutral role performed by one communication endpoint."""

    ADAPTER = "adapter"
    SCANNER = "scanner"
    MASTER = "master"
    SLAVE = "slave"
    CLIENT = "client"
    SERVER = "server"
    PEER = "peer"
    UNKNOWN = "unknown"


@dataclass(frozen=True, kw_only=True)
class CommunicationService:
    """One cyclic or explicit service exposed through an interface.

    Fields populated from a Logix MESSAGE tag describe its exported
    configuration. Controller logic may modify MESSAGE members at runtime.
    """

    name: str
    service_type: str
    object_class: str | None = None
    instance: str | None = None
    attribute: str | None = None
    service_code: int | None = None
    requested_length: int | None = None
    connection_path: str | None = None
    local_element: str | None = None
    destination_tag: str | None = None
    configuration_source: str | None = None
    runtime_mutable: bool | None = None
    source_extensions: tuple[SourceExtension, ...] = ()


@dataclass(kw_only=True)
class CommunicationInterface(Asset):
    """A protocol endpoint belonging to a device."""

    protocol: str
    role: CommunicationRole = CommunicationRole.UNKNOWN
    address: str | None = None
    connections: list[Connection] = field(default_factory=list)
    services: list[CommunicationService] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def add_connection(self, connection: Connection) -> None:
        """Attach a cyclic or logical connection to the interface."""

        connection.parent = self
        self.connections.append(connection)

    def add_service(self, service: CommunicationService) -> None:
        """Attach an explicit or abstract communication service."""

        self.services.append(service)
