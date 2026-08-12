"""Vendor-neutral multi-protocol gateway model."""

from __future__ import annotations

from dataclasses import dataclass, field

from .communication_interface import CommunicationInterface
from .device import Device, DeviceType
from .source_extension import SourceExtension


@dataclass(frozen=True, kw_only=True)
class GatewayProtocolMapping:
    """One evidenced mapping between two named gateway endpoints.

    A mapping must not be created merely because both endpoints exist.
    Source and target references retain the native point/register evidence.
    """

    source_interface: str
    target_interface: str
    evidence: str
    source_reference: str | None = None
    target_reference: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    source_extensions: tuple[SourceExtension, ...] = ()


@dataclass(kw_only=True)
class GatewayDevice(Device):
    """A communication device with endpoints distinct from point mappings."""

    device_type: DeviceType = DeviceType.COMMUNICATION_DEVICE
    protocol_mappings: list[GatewayProtocolMapping] = field(default_factory=list)

    def add_communication_interface(
        self,
        interface: CommunicationInterface,
    ) -> None:
        """Attach a uniquely named protocol endpoint to this gateway."""

        if any(item.name == interface.name for item in self.communication_interfaces):
            raise ValueError(f"duplicate gateway interface name: {interface.name!r}")
        super().add_communication_interface(interface)

    def add_protocol_mapping(self, mapping: GatewayProtocolMapping) -> None:
        """Attach an explicitly evidenced mapping between existing endpoints."""

        interface_names = {
            interface.name for interface in self.communication_interfaces
        }
        missing = {
            name
            for name in (mapping.source_interface, mapping.target_interface)
            if name not in interface_names
        }
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"gateway mapping references unknown interfaces: {names}")
        if mapping.source_interface == mapping.target_interface:
            raise ValueError("gateway mapping endpoints must be distinct")
        if not mapping.evidence.strip():
            raise ValueError("gateway mapping evidence must be explicit")
        self.protocol_mappings.append(mapping)
