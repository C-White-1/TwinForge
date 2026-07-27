"""Vendor-neutral visualization model."""

from dataclasses import dataclass, field
from enum import Enum

from .source_extension import SourceExtension


class VisualizationControlKind(str, Enum):
    """Portable visual-control categories."""

    BUTTON = "button"
    TEXT_INPUT = "text_input"
    INDICATOR = "indicator"
    LABEL = "label"
    UNKNOWN = "unknown"


class VisualizationBindingRole(str, Enum):
    """How a control consumes or modifies an automation expression."""

    VALUE = "value"
    COMMAND = "command"
    INPUT = "input"


class VisualizationInteractionKind(str, Enum):
    """Portable user-interaction intents."""

    TOGGLE = "toggle"
    VALUE_INPUT = "value_input"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class VisualizationGeometry:
    """Rectangular control geometry in source canvas units."""

    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True)
class VisualizationBinding:
    """An IEC expression bound to a portable control role."""

    expression: str
    role: VisualizationBindingRole


@dataclass(frozen=True)
class VisualizationInteraction:
    """A portable interaction plus optional value-entry constraints."""

    kind: VisualizationInteractionKind
    operand: str | None = None
    value_format: str | None = None
    minimum: str | None = None
    maximum: str | None = None
    prompt: str | None = None
    source_extensions: tuple[SourceExtension, ...] = ()


@dataclass
class VisualizationControl:
    """One visual control independent of its authoring system."""

    identifier: str
    kind: VisualizationControlKind
    geometry: VisualizationGeometry
    text: str | None = None
    source_type: str | None = None
    bindings: list[VisualizationBinding] = field(default_factory=list)
    interactions: list[VisualizationInteraction] = field(default_factory=list)
    source_extensions: list[SourceExtension] = field(
        default_factory=list,
        repr=False,
    )


@dataclass
class VisualizationCanvas:
    """A named visualization surface."""

    name: str
    width: int | None = None
    height: int | None = None
    controls: list[VisualizationControl] = field(default_factory=list)
    source_extensions: list[SourceExtension] = field(
        default_factory=list,
        repr=False,
    )


@dataclass
class VisualizationDocument:
    """A portable collection of canvases and presentation hints."""

    canvases: list[VisualizationCanvas] = field(default_factory=list)
    theme: str | None = None
    source_extensions: list[SourceExtension] = field(
        default_factory=list,
        repr=False,
    )
