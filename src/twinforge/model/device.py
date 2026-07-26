"""Vendor-neutral physical or logical automation devices."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .asset import Asset
from .communication_interface import CommunicationInterface
from .device_module_binding import DeviceModuleBinding
from .identity import Identity
from .observed_parameter import ObservedParameterAccess


class DeviceType(str, Enum):
    """Broad equipment role without imposing a vendor taxonomy."""

    DRIVE = "drive"
    INSTRUMENT = "instrument"
    IO_DEVICE = "io_device"
    CONTROLLER = "controller"
    COMMUNICATION_DEVICE = "communication_device"
    OTHER = "other"
    UNKNOWN = "unknown"


@dataclass(kw_only=True)
class Device(Asset):
    """An automation device distinct from its controller representation.

    A physical device may be represented by one or more controller modules.
    Those relationships are held by bindings so a module can retain its
    controller topology and a device can retain its asset identity.
    """

    device_type: DeviceType = DeviceType.UNKNOWN
    manufacturer: str | None = None
    model: str | None = None
    catalog_number: str | None = None
    identity: Identity | None = None
    communication_interfaces: list[CommunicationInterface] = field(
        default_factory=list
    )
    module_bindings: list[DeviceModuleBinding] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)
    observed_parameters: list[ObservedParameterAccess] = field(
        default_factory=list
    )

    def add_communication_interface(
        self,
        interface: CommunicationInterface,
    ) -> None:
        """Attach a communication interface to this device."""

        interface.parent = self
        self.communication_interfaces.append(interface)

    def bind_module(self, binding: DeviceModuleBinding) -> None:
        """Attach controller-module evidence without reparenting the module."""

        binding.parent = self
        self.module_bindings.append(binding)
