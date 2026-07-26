"""Vendor-neutral runtime capabilities required by converted controller logic."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class RuntimeCapability(str, Enum):
    """A target-runtime service that portable controller logic may require."""

    EXPLICIT_MESSAGING = "explicit_messaging"
    WALL_CLOCK_READ = "wall_clock_read"
    CONTROLLER_OBJECT_READ = "controller_object_read"
    CONTROLLER_OBJECT_WRITE = "controller_object_write"
    MODULE_REFERENCE = "module_reference"
    PRESCAN_HOOK = "prescan_hook"
    POSTSCAN_HOOK = "postscan_hook"
    DISABLED_SCAN_HOOK = "disabled_scan_hook"


@dataclass(frozen=True)
class RuntimeRequirement:
    """One capability requirement and the captured evidence for it."""

    capability: RuntimeCapability
    evidence: tuple[str, ...]


class RuntimeCapabilityProvider(Protocol):
    """Contract implemented by a target profile or runtime adapter."""

    @property
    def runtime_name(self) -> str:
        """Return the human-readable runtime/profile name."""
        ...

    @property
    def capabilities(self) -> frozenset[RuntimeCapability]:
        """Return the capabilities supplied by this adapter."""
        ...


@dataclass(frozen=True)
class RuntimeCompatibility:
    """Comparison of an AOI's requirements with a runtime provider."""

    runtime_name: str
    required: tuple[RuntimeCapability, ...]
    provided: tuple[RuntimeCapability, ...]
    missing: tuple[RuntimeCapability, ...]

    @property
    def compatible(self) -> bool:
        """Return true when every declared requirement is provided."""

        return not self.missing


def evaluate_runtime_compatibility(
    requirements: tuple[RuntimeRequirement, ...],
    provider: RuntimeCapabilityProvider,
) -> RuntimeCompatibility:
    """Compare deterministic requirement and provider capability sets."""

    required = frozenset(item.capability for item in requirements)
    provided = provider.capabilities
    return RuntimeCompatibility(
        runtime_name=provider.runtime_name,
        required=_sorted_capabilities(required),
        provided=_sorted_capabilities(provided),
        missing=_sorted_capabilities(required - provided),
    )


def _sorted_capabilities(
    capabilities: frozenset[RuntimeCapability],
) -> tuple[RuntimeCapability, ...]:
    return tuple(sorted(capabilities, key=lambda item: item.value))
