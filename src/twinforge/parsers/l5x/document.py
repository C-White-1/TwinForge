"""Typed result for one Rockwell L5X export document."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from twinforge.converters import ConversionDiagnostic
from twinforge.model import (
    AddOnInstruction,
    Controller,
    Module,
    Program,
    SoftwareComponent,
    Tag,
)
from twinforge.model.source_extension import SourceExtension


class L5XTargetType(str, Enum):
    """Supported values of the L5X root ``TargetType`` attribute."""

    CONTROLLER = "Controller"
    MODULE = "Module"
    PROGRAM = "Program"
    ADD_ON_INSTRUCTION = "AddOnInstructionDefinition"


L5XTarget = Controller | Module | Program | AddOnInstruction


@dataclass(frozen=True)
class L5XDocument:
    """One converted target plus lossless document-level evidence."""

    target_type: L5XTargetType
    target_name: str
    target: L5XTarget
    source_path: Path
    context_controller_names: tuple[str, ...] = ()
    software_component: SoftwareComponent | None = None
    diagnostics: tuple[ConversionDiagnostic, ...] = ()
    context_controller_tags: tuple[Tag, ...] = ()
    source_extensions: tuple[SourceExtension, ...] = field(
        default_factory=tuple,
        repr=False,
    )
