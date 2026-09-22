"""Vendor-neutral graphical source evidence, without execution assumptions."""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .ladder import LadderPosition, LadderSeries
from .source_extension import SourceExtension

if TYPE_CHECKING:
    from .add_on_instruction import AddOnInstructionParameter
    from .tag import Tag


@dataclass(frozen=True)
class MemberPath:
    """An index/member/bit-select expression whose every step was proven by a type definition."""

    base: str
    # Lexical steps in source order, e.g. (".STAT", "[2]", ".5"); indexes are literal and in bounds.
    steps: tuple[str, ...]
    # Proven type of the final element (the element type if still an array).
    type_name: str | None
    is_array: bool = False


@dataclass(frozen=True)
class ExpressionOperand:
    """One side of a resolved BinaryExpression, proven the same way a standalone expression is."""

    text: str
    kind: str  # "literal" | "declared_symbol" | "declared_member_path"
    target_tag: "Tag | None" = field(default=None, repr=False)
    target_parameter: "AddOnInstructionParameter | None" = field(default=None, repr=False)
    member_path: "MemberPath | None" = None


@dataclass(frozen=True)
class BinaryExpression:
    """A single evidenced binary operator between two independently proven operands.

    Structural evidence only, deliberately narrow (see
    ``analysis.simple_expressions``): exactly one recognized operator, per
    corpus-evidenced shapes. No truth value, arithmetic result or type
    compatibility is computed or implied by resolving one.
    """

    operator: str
    left: ExpressionOperand
    right: ExpressionOperand


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
    # A Ladder vertical-wire condition resolved by grid position, distinct
    # from expression/target_tag above (which come from an explicit source
    # attribute, never grid geometry). None means not resolved this way.
    ladder_condition: "LadderSeries | None" = field(default=None, repr=False)
    # Set for binding_kind "declared_member_path"; target_tag/target_parameter
    # then name the *base* symbol only, never the member.
    member_path: "MemberPath | None" = None
    # Set for binding_kind "declared_expression"; target_tag/target_parameter/
    # member_path above are unset in that case (a composite expression has no
    # single base symbol of its own).
    binary_expression: "BinaryExpression | None" = None


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
    operand_member_path: "MemberPath | None" = None
    operand_binary_expression: "BinaryExpression | None" = None


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
