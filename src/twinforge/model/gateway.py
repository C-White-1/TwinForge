"""Vendor-neutral multi-protocol gateway model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .communication_interface import CommunicationInterface
from .device import Device, DeviceType
from .source_extension import SourceExtension
from .tag import Tag


class GatewayTagBindingRole(str, Enum):
    """Position of a controller tag in an evidenced gateway mapping."""

    SOURCE = "source"
    TARGET = "target"


@dataclass(frozen=True, kw_only=True)
class GatewayTagBinding:
    """Bind a gateway endpoint reference to a captured controller tag.

    ``tag_path`` may address a member below ``tag``. Keeping both values
    preserves the exact source operand while providing a typed model link.
    """

    interface_name: str
    endpoint_reference: str
    tag: Tag
    tag_path: str
    role: GatewayTagBindingRole
    evidence: str
    source_extensions: tuple[SourceExtension, ...] = ()


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
    tag_bindings: list[GatewayTagBinding] = field(default_factory=list)

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

    def add_tag_binding(self, binding: GatewayTagBinding) -> None:
        """Attach a typed, explicitly evidenced controller-tag binding."""

        interface_names = {
            interface.name for interface in self.communication_interfaces
        }
        if binding.interface_name not in interface_names:
            raise ValueError(
                "gateway tag binding references unknown interface: "
                f"{binding.interface_name!r}"
            )
        if not binding.endpoint_reference.strip():
            raise ValueError("gateway tag binding endpoint must be explicit")
        if not binding.tag_path.strip():
            raise ValueError("gateway tag binding path must be explicit")
        if not binding.evidence.strip():
            raise ValueError("gateway tag binding evidence must be explicit")
        root_name = binding.tag_path.split(".", maxsplit=1)[0]
        if root_name != binding.tag.name:
            raise ValueError(
                f"gateway tag path {binding.tag_path!r} does not reference "
                f"tag {binding.tag.name!r}"
            )
        if any(
            item.interface_name == binding.interface_name
            and item.endpoint_reference == binding.endpoint_reference
            and item.tag_path == binding.tag_path
            and item.role == binding.role
            for item in self.tag_bindings
        ):
            raise ValueError(f"duplicate gateway tag binding: {binding.tag_path!r}")
        self.tag_bindings.append(binding)
