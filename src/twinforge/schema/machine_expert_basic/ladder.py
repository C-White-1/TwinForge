"""Declarative ladder-grid rules for `.smbp` rungs.

Every value here is evidenced in docs/architecture/machine-expert-basic-smbp-format.md
("Grid semantics, verified against IL"): widths and pin rows were checked
against each rung's Instruction List across the downloaded samples and the
user-made fixtures in examples/machine_expert_basic/. Element types or block
pins not listed are unknown, and a rung that uses one gets no network.
"""
from dataclasses import dataclass, field

from twinforge.model import LadderOperation


@dataclass(frozen=True)
class BlockPins:
    """Fixed row offset of each pin within a block, inputs and outputs separately."""

    inputs: dict[str, int]
    outputs: dict[str, int]


@dataclass(frozen=True)
class LadderSpec:
    # Conduct power unconditionally and become no instruction. `Short` is the
    # editor's always-true element (IL `LD 1`).
    wires: frozenset[str] = frozenset({"Line", "Short"})
    # Carry only a vertical link on the cell's right edge.
    vertical: frozenset[str] = frozenset({"VerticalLine"})
    # Leftovers of editor selection; no wiring and no IL counterpart.
    ignored: frozenset[str] = frozenset({"None"})
    # Elements in a condition position: (portable operation, operand field).
    conditions: dict[str, tuple[LadderOperation, str | None]] = field(default_factory=lambda: {
        "NormalContact": (LadderOperation.NORMALLY_OPEN_CONTACT, "Descriptor"),
        "NegatedContact": (LadderOperation.NORMALLY_CLOSED_CONTACT, "Descriptor"),
        "RisingEdge": (LadderOperation.POSITIVE_TRANSITION_CONTACT, "Descriptor"),
        "FallingEdge": (LadderOperation.NEGATIVE_TRANSITION_CONTACT, "Descriptor"),
        "Xor": (LadderOperation.UNSUPPORTED, "Descriptor"),
        "Not": (LadderOperation.UNSUPPORTED, None),
        # Descriptor is an instance number, matching IL `RISINGn`.
        "RisingEdgeBlock": (LadderOperation.UNSUPPORTED, "Descriptor"),
        # A generic expression box; may hold an assignment and still passes power.
        "Comparison": (LadderOperation.UNSUPPORTED, "ComparisonExpression"),
    })
    # Elements in the output position: (portable operation, operand field).
    outputs: dict[str, tuple[LadderOperation, str | None]] = field(default_factory=lambda: {
        "Coil": (LadderOperation.COIL, "Descriptor"),
        "SetCoil": (LadderOperation.SET_COIL, "Descriptor"),
        "ResetCoil": (LadderOperation.RESET_COIL, "Descriptor"),
        "NegativeCoil": (LadderOperation.NEGATED_COIL, "Descriptor"),
        "Operation": (LadderOperation.UNSUPPORTED, "OperationExpression"),
    })
    blocks: dict[str, BlockPins] = field(default_factory=lambda: {
        "Timer": BlockPins({"IN": 0}, {"Q": 0}),
        "Counter": BlockPins({"R": 0, "S": 1, "CU": 2, "CD": 3}, {"E": 0, "D": 1, "F": 2}),
        "Drum": BlockPins({"R": 0, "U": 1}, {"F": 0}),
        "WriteVarBasic": BlockPins({"Execute": 0}, {"Done": 0}),
    })
    # Block type by instance address prefix, for Instruction List rungs that
    # name a block only by address (`BLK %TM0`). One-to-one in every grid cell
    # of the samples and fixtures: %TM Timer (35), %DR Drum (8), %C Counter
    # (2), %WRITE_VAR WriteVarBasic (1). Longest prefix wins.
    block_prefixes: dict[str, str] = field(default_factory=lambda: {
        "%TM": "Timer", "%DR": "Drum", "%C": "Counter", "%WRITE_VAR": "WriteVarBasic",
    })
    # Expression boxes: element type -> field holding the expression text.
    expression_fields: dict[str, str] = field(default_factory=lambda: {
        "Comparison": "ComparisonExpression", "Operation": "OperationExpression",
    })
    # IEC type of an expression operand by address prefix (longest prefix
    # wins), per the Generic Functions Library Guide EIO0000003289.04: word
    # objects INT ("Word Objects"; network objects are listed as words),
    # %MD/%KD DINT and %MF/%KF REAL ("Floating Point and Double Word
    # Objects"). Anything else (bits, %TMi.P, %SWi:Xj) is not converted.
    expression_operand_types: dict[str, str] = field(default_factory=lambda: {
        "%MW": "INT", "%KW": "INT", "%SW": "INT", "%IW": "INT", "%QW": "INT", "%IWS": "INT", "%QWS": "INT",
        "%IWE": "INT", "%QWE": "INT", "%IWM": "INT", "%QWM": "INT",
        "%MD": "DINT", "%KD": "DINT", "%MF": "REAL", "%KF": "REAL",
    })
    # Columns occupied; any element not listed is one column wide.
    widths: dict[str, int] = field(default_factory=lambda: {
        "Timer": 2, "Counter": 2, "Drum": 2, "Comparison": 2, "Operation": 2, "WriteVarBasic": 4,
    })
    # Fields holding the cell's grid data.
    element_type: str = "ElementType"
    row: str = "Row"
    column: str = "Column"
    connection: str = "ChosenConnection"
    # A block cell's instance address, e.g. `%TM0`.
    block_name: str = "Descriptor"

    def width(self, element_type: str) -> int:
        return self.widths.get(element_type, 1)

    def known(self, element_type: str) -> bool:
        return (element_type in self.wires or element_type in self.vertical or element_type in self.ignored
                or element_type in self.conditions or element_type in self.outputs or element_type in self.blocks)


LADDER_SPEC = LadderSpec()
