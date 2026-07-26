"""Vendor-neutral controller software definitions and their bindings."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from .asset import Asset
from .source_extension import SourceExtension

if TYPE_CHECKING:
    from .device import Device
    from .module import Module
    from .tag import Tag


class SoftwareComponentKind(str, Enum):
    """Portable shape of a controller software definition."""

    PROGRAM = "program"
    FUNCTION_BLOCK = "function_block"
    FUNCTION = "function"
    ROUTINE = "routine"
    LIBRARY = "library"
    OTHER = "other"
    UNKNOWN = "unknown"


class SoftwareBindingRole(str, Enum):
    """Meaning of a link from software to an external model object."""

    DEVICE_IMPLEMENTATION = "device_implementation"
    MODULE_ACCESS = "module_access"
    INSTANCE_TAG = "instance_tag"
    COMMAND_TAG = "command_tag"
    STATUS_TAG = "status_tag"
    IO_TAG = "io_tag"
    OTHER = "other"


@dataclass(kw_only=True)
class SoftwareBinding:
    """Evidence-bearing link without changing target ownership."""

    target: Device | Module | Tag
    role: SoftwareBindingRole
    evidence: str
    parent: SoftwareComponent | None = field(default=None, repr=False)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_extensions: list[SourceExtension] = field(
        default_factory=list,
        repr=False,
    )


@dataclass(kw_only=True)
class SoftwareComponent(Asset):
    """A reusable software definition, distinct from each instance tag."""

    kind: SoftwareComponentKind = SoftwareComponentKind.UNKNOWN
    implementation: object | None = None
    vendor: str | None = None
    revision: str | None = None
    bindings: list[SoftwareBinding] = field(default_factory=list)

    def add_binding(self, binding: SoftwareBinding) -> None:
        """Attach a validated, evidence-bearing relationship."""

        if not binding.evidence.strip():
            raise ValueError("software binding evidence must be explicit")
        _validate_binding_target(binding)
        binding.parent = self
        self.bindings.append(binding)

    def bind_device(
        self,
        device: Device,
        *,
        evidence: str,
        metadata: dict[str, Any] | None = None,
    ) -> SoftwareBinding:
        """Record that this definition implements a device abstraction."""

        return self._bind(
            device,
            SoftwareBindingRole.DEVICE_IMPLEMENTATION,
            evidence,
            metadata,
        )

    def bind_module(
        self,
        module: Module,
        *,
        evidence: str,
        metadata: dict[str, Any] | None = None,
    ) -> SoftwareBinding:
        """Record access to a controller-side hardware representation."""

        return self._bind(
            module,
            SoftwareBindingRole.MODULE_ACCESS,
            evidence,
            metadata,
        )

    def bind_tag(
        self,
        tag: Tag,
        *,
        role: SoftwareBindingRole,
        evidence: str,
        metadata: dict[str, Any] | None = None,
    ) -> SoftwareBinding:
        """Record an instance, command, status, or I/O tag relationship."""

        return self._bind(tag, role, evidence, metadata)

    def _bind(
        self,
        target: Device | Module | Tag,
        role: SoftwareBindingRole,
        evidence: str,
        metadata: dict[str, Any] | None,
    ) -> SoftwareBinding:
        binding = SoftwareBinding(
            target=target,
            role=role,
            evidence=evidence,
            metadata=dict(metadata or {}),
        )
        self.add_binding(binding)
        return binding


def _validate_binding_target(binding: SoftwareBinding) -> None:
    """Prevent semantically invalid role/target combinations."""

    from .device import Device
    from .module import Module
    from .tag import Tag

    expected: dict[SoftwareBindingRole, type[object]] = {
        SoftwareBindingRole.DEVICE_IMPLEMENTATION: Device,
        SoftwareBindingRole.MODULE_ACCESS: Module,
        SoftwareBindingRole.INSTANCE_TAG: Tag,
        SoftwareBindingRole.COMMAND_TAG: Tag,
        SoftwareBindingRole.STATUS_TAG: Tag,
        SoftwareBindingRole.IO_TAG: Tag,
    }
    target_type = expected.get(binding.role)
    if target_type is not None and not isinstance(binding.target, target_type):
        raise TypeError(
            f"{binding.role.value} requires {target_type.__name__}, "
            f"got {type(binding.target).__name__}"
        )
