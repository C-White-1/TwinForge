"""Relationship between a device and its controller-side module."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from .source_extension import SourceExtension

if TYPE_CHECKING:
    from .device import Device
    from .module import Module


class DeviceModuleRole(str, Enum):
    """Role played by a module in representing a device."""

    CYCLIC_IO = "cyclic_io"
    DIAGNOSTICS = "diagnostics"
    CONFIGURATION = "configuration"
    COMMUNICATION = "communication"
    OTHER = "other"


@dataclass(kw_only=True)
class DeviceModuleBinding:
    """Evidence that a controller module represents a device.

    Binding does not change ``Module.parent`` because that relationship
    describes controller, chassis, and network topology.
    """

    module: Module
    role: DeviceModuleRole
    evidence: str
    parent: Device | None = field(default=None, repr=False)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_extensions: list[SourceExtension] = field(
        default_factory=list,
        repr=False,
    )

    @property
    def identity_scopes_are_distinct(self) -> bool:
        """Confirm that module identity is not being used as device identity."""

        return self.parent is None or (
            self.parent.identity is not self.module.identity
        )
