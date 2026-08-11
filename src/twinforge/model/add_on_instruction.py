"""Vendor-neutral Add-On Instruction definition model."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Iterator
from typing import Any

from .routine import Routine
from .source_extension import SourceExtension
from .tag import Tag
from .tag_value import TagValue
from .datatype import Datatype


@dataclass
class AddOnInstructionParameter:
    """One externally visible parameter of a reusable instruction."""

    name: str
    data_type: str | None = None
    resolved_data_type: str | None = None
    data_type_definition: Datatype | None = None
    usage: str | None = None
    dimensions: str | None = None
    radix: str | None = None
    required: bool | None = None
    visible: bool | None = None
    constant: bool | None = None
    external_access: str | None = None
    alias_for: str | None = None
    description: str | None = None
    default_value: TagValue | None = None
    source_extensions: list[SourceExtension] = field(
        default_factory=list, repr=False
    )

    @property
    def effective_data_type(self) -> str | None:
        """Return documented or safely resolved datatype evidence."""

        return self.data_type or self.resolved_data_type


@dataclass
class AddOnInstructionDependency:
    """A named definition required by an Add-On Instruction."""

    dependency_type: str
    name: str
    target: object | None = None
    source_extensions: list[SourceExtension] = field(
        default_factory=list, repr=False
    )


@dataclass
class AddOnInstruction:
    """Reusable controller instruction and its implementation routines."""

    name: str
    revision: str | None = None
    vendor: str | None = None
    description: str | None = None
    execute_prescan: bool | None = None
    execute_postscan: bool | None = None
    execute_enable_in_false: bool | None = None
    parameters: dict[str, AddOnInstructionParameter] = field(
        default_factory=dict
    )
    routines: dict[str, Routine] = field(default_factory=dict)
    scan_mode_routines: dict[str, Routine] = field(default_factory=dict)
    local_tags: dict[str, Tag] = field(default_factory=dict)
    dependencies: list[AddOnInstructionDependency] = field(
        default_factory=list
    )
    parent: Any | None = field(default=None, repr=False)
    source_extensions: list[SourceExtension] = field(
        default_factory=list, repr=False
    )

    def add_parameter(self, parameter: AddOnInstructionParameter) -> None:
        if parameter.name in self.parameters:
            raise ValueError(
                f"Parameter '{parameter.name}' already exists"
            )
        self.parameters[parameter.name] = parameter

    def add_routine(self, routine: Routine) -> None:
        if routine.name in self.routines:
            raise ValueError(f"Routine '{routine.name}' already exists")
        routine.parent = self
        self.routines[routine.name] = routine

    def add_scan_mode_routine(self, routine: Routine) -> None:
        """Retain one lifecycle routine separately from primary logic."""

        if routine.name in self.scan_mode_routines:
            raise ValueError(
                f"Scan mode routine '{routine.name}' already exists"
            )
        routine.parent = self
        self.scan_mode_routines[routine.name] = routine

    def iter_routines(self) -> Iterator[Routine]:
        """Yield primary and scan-mode routines in captured order."""

        yield from self.routines.values()
        yield from self.scan_mode_routines.values()

    def add_local_tag(self, tag: Tag) -> None:
        if tag.name in self.local_tags:
            raise ValueError(f"Local tag '{tag.name}' already exists")
        tag.parent = self
        self.local_tags[tag.name] = tag
