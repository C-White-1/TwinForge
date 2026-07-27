"""Evidence-backed parameter access discovered in controller software."""

from __future__ import annotations

from dataclasses import dataclass

from .device_parameter import (
    DeviceParameterAdvisory,
    DeviceParameterDefinition,
    DeviceParameterValueEvidence,
)


@dataclass(frozen=True)
class ObservedParameterAccess:
    """One numbered device parameter referenced by controller logic."""

    number: int
    label: str | None = None
    code: str | None = None
    group_prefix: str | None = None
    group_name: str | None = None
    display_name: str | None = None
    reference: str | None = None
    definition: DeviceParameterDefinition | None = None
    observed_read: bool = False
    observed_write: bool = False
    read_buffer_indices: tuple[int, ...] = ()
    evidence: tuple[str, ...] = ()
    configured_value: DeviceParameterValueEvidence | None = None
    runtime_value: DeviceParameterValueEvidence | None = None
    configuration_note: str | None = None
    advisories: tuple[DeviceParameterAdvisory, ...] = ()
