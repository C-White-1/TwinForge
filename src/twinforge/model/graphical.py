"""Vendor-neutral graphical source evidence, without execution assumptions."""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .ladder import LadderPosition
from .source_extension import SourceExtension

if TYPE_CHECKING:
    from .add_on_instruction import AddOnInstructionParameter
    from .tag import Tag


@dataclass
class GraphicalPin:
    name: str | None = None
    # Source interface direction is not a claim about memory read/write effects.
    direction: str = ""
    expression: str | None = None
    inverted: bool | None = None
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
    interface_status: str | None = None
    parameter_index: int | None = None
    role: str = "data"
    binding_kind: str = "unresolved"
    target_tag: "Tag | None" = field(default=None, repr=False)
    # Set instead of target_tag when this pin resolves within a Function
    # Block body, against that FB's own parameter -- a distinct namespace
    # from the project's global tags, never both at once.
    target_parameter: "AddOnInstructionParameter | None" = field(default=None, repr=False)


@dataclass
class GraphicalVariableReferences:
    """Pins referring to the same declared symbol, not wiring or memory effects."""

    symbol_name: str
    # Pairs are (object index, pin index), preserving duplicate names/directions.
    input_pins: list[tuple[int, int]] = field(default_factory=list)
    output_pins: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class GraphicalLinkEndpoint:
    """One `linkFB` endpoint, identified by name, not position or proximity."""

    object_name: str | None = None
    pin_name: str | None = None
    status: str = "unresolved"  # resolved | missing_object | ambiguous_object | missing_pin | ambiguous_pin
    object_index: int | None = None
    pin_index: int | None = None


@dataclass
class GraphicalLink:
    """An explicit `linkFB` wire; resolving it is not an execution-order claim."""

    source: GraphicalLinkEndpoint = field(default_factory=GraphicalLinkEndpoint)
    destination: GraphicalLinkEndpoint = field(default_factory=GraphicalLinkEndpoint)
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)


@dataclass
class GraphicalObject:
    kind: str
    instance_name: str | None = None
    type_name: str | None = None
    operand: str | None = None
    text: str | None = None
    position: LadderPosition | None = None
    width: int | None = None
    height: int | None = None
    pins: list[GraphicalPin] = field(default_factory=list)
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
    # Original predecessor hint, not a resolved scheduling edge.
    execution_after: str | None = None
    interface_status: str | None = None
    interface_index: int | None = None
    # Contact operand binding; distinct from pin binding_kind above.
    operand_binding_kind: str | None = None
    target_tag: "Tag | None" = field(default=None, repr=False)
    # Canonical declared SFC step name for a "<step>.X"/".x" contact operand.
    target_step_name: str | None = None


@dataclass
class GraphicalDiagram:
    """Ordered diagram objects and source evidence; not an executable network.

    Connections are deliberately not inferred from proximity, object order,
    repeated expressions or the absence of explicit source wires.
    """

    language: str
    objects: list[GraphicalObject] = field(default_factory=list)
    links: list[GraphicalLink] = field(default_factory=list)
    connectivity_resolved: bool = False
    execution_order_resolved: bool = False
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
    # Indices into objects; scoped to this network, never to the entire task.
    execution_order: list[int] = field(default_factory=list)
    execution_order_basis: str | None = None
    shared_variables: list[GraphicalVariableReferences] = field(default_factory=list)
