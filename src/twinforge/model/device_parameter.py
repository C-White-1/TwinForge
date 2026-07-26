"""Vendor-neutral definitions for configurable device parameters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceParameterOption:
    """One documented value of an enumerated device parameter."""

    value: str
    label: str


@dataclass(frozen=True)
class DeviceParameterFlag:
    """One documented active flag within a packed parameter value."""

    position: str
    label: str


@dataclass(frozen=True)
class DeviceParameterField:
    """One documented field within an encoded parameter value."""

    position: str
    label: str
    options: tuple[DeviceParameterOption, ...] = ()


@dataclass(frozen=True)
class DeviceParameterDefinition:
    """Catalogue metadata for one vendor device parameter."""

    number: int
    code: str
    name: str
    group_prefix: str
    group_name: str
    description: str | None = None
    engineering_unit: str | None = None
    minimum: str | None = None
    maximum: str | None = None
    default: str | None = None
    resolution: str | None = None
    options: tuple[DeviceParameterOption, ...] = ()
    option_set_name: str | None = None
    flags: tuple[DeviceParameterFlag, ...] = ()
    fields: tuple[DeviceParameterField, ...] = ()
    read_only: bool = False
    change_requires_stop: bool = False
    reference: str | None = None
