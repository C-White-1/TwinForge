"""Source-neutral evidence for calls made by controller programs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .add_on_instruction import AddOnInstructionParameter
from .connection import Connection
from .module import Module
from .software_component import SoftwareComponent
from .tag import Tag


class SoftwareCallLanguage(str, Enum):
    """Source representation in which a call was observed."""

    LADDER = "ladder"
    STRUCTURED_TEXT = "structured_text"


class SoftwareCallBindingRole(str, Enum):
    """Meaning established for one call operand."""

    INSTANCE = "instance"
    PARAMETER = "parameter"
    UNMATCHED = "unmatched"


class SoftwareParameterFlow(str, Enum):
    """Normalized data flow supported by the AOI parameter Usage attribute."""

    INPUT = "input"
    OUTPUT = "output"
    IN_OUT = "in_out"
    UNKNOWN = "unknown"


class ModuleDataDirection(str, Enum):
    """Logix module-defined data area referenced by an operand."""

    INPUT = "input"
    OUTPUT = "output"
    CONFIGURATION = "configuration"
    STATUS = "status"
    UNKNOWN = "unknown"


class SoftwareTagScope(str, Enum):
    """Controller namespace in which an operand tag was resolved."""

    PROGRAM = "program"
    CONTROLLER = "controller"
    CONTROLLER_CONTEXT = "controller_context"


@dataclass(frozen=True)
class SoftwareCallArgument:
    """One losslessly captured call operand."""

    position: int
    source: str
    name: str | None = None
    direction: str | None = None


@dataclass(frozen=True)
class SoftwareCallSite:
    """A candidate software invocation and its exact source evidence."""

    callee: str
    arguments: tuple[SoftwareCallArgument, ...]
    program_name: str
    routine_name: str
    language: SoftwareCallLanguage
    source_text: str
    source_path: Path | None = None
    rung_number: int | None = None
    line_number: int | None = None


@dataclass(frozen=True)
class SoftwareCallArgumentBinding:
    """Evidence-backed association between an operand and AOI interface."""

    argument: SoftwareCallArgument
    role: SoftwareCallBindingRole
    parameter: AddOnInstructionParameter | None = None
    target_tag: Tag | None = None
    target_tag_scope: SoftwareTagScope | None = None
    target_module: Module | None = None
    target_connection: Connection | None = None
    module_data_path: str | None = None
    module_data_direction: ModuleDataDirection | None = None
    flow: SoftwareParameterFlow = SoftwareParameterFlow.UNKNOWN


@dataclass(frozen=True)
class ResolvedSoftwareCall:
    """A call conservatively matched to one reusable software definition."""

    call_site: SoftwareCallSite
    definition: SoftwareComponent
    instance_tag: Tag | None = None
    argument_bindings: tuple[SoftwareCallArgumentBinding, ...] = ()


@dataclass(frozen=True)
class SoftwareModuleAssembly:
    """A software instance proven to access controller-side modules."""

    workspace_key: str
    definition: SoftwareComponent
    instance_tag: Tag
    modules: tuple[Module, ...]
    calls: tuple[ResolvedSoftwareCall, ...]
    evidence: tuple[str, ...]
