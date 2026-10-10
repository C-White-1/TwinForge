"""Prepare deterministic PLCopen symbols before XML serialization."""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from twinforge.converters import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import Controller, Expression, LadderOperation, LadderSeries, Tag
from twinforge.model.expression import ASSIGNMENT_OPERATOR

from .plcopen_library import LIBRARY as GENERATED_LIBRARY
from .plcopen_library import GeneratedFunctionBlock
from .plcopen_network import BIT_STRING_TYPES, BlockInterface, timer_interface
from .plcopen_network import instructions as network_instructions
from .plcopen_network import split_member
from .plcopen_network import unsupported_reason as network_unsupported_reason

from .plcopen_rll import (
    COMPARISON_TYPES,
    VALUE_BLOCK_TYPES,
    parse_supported_rung,
    split_arguments,
)
from .plcopen_xml import (
    milliseconds_time_literal,
    timer_member_integer,
    unique_portable_name,
)


# TC6 names four elementary-type elements differently from the IEC 61131-3
# type name used everywhere else (tc6_xml_v201.xsd, group "elementaryTypes").
# Emitting the IEC name as the element (e.g. <STRING/>) fails validation.
PLCOPEN_TYPE_ELEMENTS = {
    "STRING": "string",
    "WSTRING": "wstring",
    "DATE_AND_TIME": "DT",
    "TIME_OF_DAY": "TOD",
}


def plcopen_type_element(type_name: str) -> str:
    """The TC6 element name for an IEC elementary type name."""

    return PLCOPEN_TYPE_ELEMENTS.get(type_name, type_name)


# IEC 61131-3 standard timers, declared as function block instances.
IEC_TIMER_TYPES = frozenset({"TON", "TOF", "TP"})
_IEC_IDENTIFIER = re.compile(r"[A-Za-z_]\w*")


PLCOPEN_PRIMITIVE_TYPES = frozenset(
    {
        "BOOL",
        "BYTE",
        "WORD",
        "DWORD",
        "LWORD",
        "SINT",
        "INT",
        "DINT",
        "LINT",
        "USINT",
        "UINT",
        "UDINT",
        "ULINT",
        "REAL",
        "LREAL",
        "STRING",
        "WSTRING",
        "TIME",
        "DATE",
        "TIME_OF_DAY",
        "DATE_AND_TIME",
    }
)

_IEC_OPERAND = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")
_NUMERIC_LITERAL = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)")


@dataclass(frozen=True)
class PLCopenTimerExport:
    """Generated IEC state for one Rockwell TIMER tag."""

    preset_ms: int
    input_name: str
    done_name: str
    elapsed_name: str
    executed_name: str


@dataclass(frozen=True)
class PLCopenOneShotExport:
    """Generated IEC state for one Rockwell ONS occurrence."""

    instance_name: str
    input_name: str
    pulse_name: str
    executed_name: str


@dataclass(frozen=True)
class PLCopenOperandPlan:
    """All symbols and diagnostics discovered before PLCopen emission."""

    operand_names: dict[str, str]
    boolean_operands: frozenset[str]
    generated_tags: tuple[Tag, ...]
    comparison_tags: dict[str, tuple[Tag, ...]]
    comparison_temps: dict[int, tuple[str, ...]]
    unsupported_comparison_rungs: frozenset[int]
    timers: dict[str, PLCopenTimerExport]
    oneshots: dict[int, PLCopenOneShotExport]
    oneshot_tags: dict[str, tuple[Tag, ...]]
    diagnostics: tuple[ConversionDiagnostic, ...]
    # Tag name -> interface, for tags that are convertible function block
    # instances: IEC timers with a known PT (`iec_function_block_inputs`),
    # and TwinForge-generated blocks (`function_block_semantics`). Network
    # rungs emit a TC6 block for these.
    function_block_instances: dict[str, BlockInterface] = field(default_factory=dict)
    # TwinForge-generated function block definitions the project uses.
    generated_blocks: tuple[GeneratedFunctionBlock, ...] = ()
    # Tag name -> IEC-safe declared name, for tags whose source name is not
    # an IEC identifier (an unnamed Machine Expert - Basic timer is "%TM0").
    tag_names: dict[str, str] = field(default_factory=dict)
    # id() of an Expression node -> the temporary variable its value is
    # stored in: every nested arithmetic node and every comparison result.
    # (The arithmetic directly assigned by an ASSIGNMENT writes its target.)
    expression_temps: dict[int, str] = field(default_factory=dict)
    # id() of a shift `call` node -> its two bit-string temporaries: the
    # converted input and the shifted value.
    expression_bit_temps: dict[int, tuple[str, str]] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> PLCopenOperandPlan:
        """Return an empty plan for a newly constructed exporter."""

        return cls({}, frozenset(), (), {}, {}, frozenset(), {}, {}, {}, ())

    def portable_operand(self, operand: str) -> str:
        """Return the deterministic IEC-safe symbol for one operand."""

        return self.operand_names.get(operand, operand)

    def tag_export_type(self, tag: Tag) -> str:
        """Return the effective scalar type used by PLCopen emission."""

        if tag.data_type:
            return tag.data_type.upper()
        if tag.alias_for:
            if tag.name in self.boolean_operands:
                return "BOOL"
            if (tag.radix or "").lower() == "float":
                return "REAL"
            return "BOOL"
        return ""

    def comparison_operands(self, operands: list[str]) -> list[str]:
        """Map comparison operands, including TIMER.ACC time conversion."""

        if not any(operand.endswith(".ACC") for operand in operands):
            return [self.portable_operand(operand) for operand in operands]
        converted: list[str] = []
        for operand in operands:
            if operand.endswith(".ACC"):
                timer = self.timers.get(operand[:-4])
                converted.append(timer.elapsed_name if timer is not None else operand)
            elif _NUMERIC_LITERAL.fullmatch(operand):
                converted.append(milliseconds_time_literal(int(float(operand))))
            else:
                converted.append(f"DINT_TO_TIME({self.portable_operand(operand)})")
        return converted


class PLCopenOperandPlanner:
    """Discover deterministic symbols without serializing PLCopen XML."""

    def __init__(self, *, rising_trigger_type: str = "R_TRIG", include_unverified_blocks: bool = False) -> None:
        self._rising_trigger_type = rising_trigger_type
        # Export instances of generated blocks whose behaviour is not yet
        # verified (see plcopen_library.GeneratedFunctionBlock.verified).
        self._include_unverified_blocks = include_unverified_blocks
        self._operand_names: dict[str, str] = {}
        self._boolean_operands: set[str] = set()
        self._generated_tags: list[Tag] = []
        self._comparison_tags: dict[str, list[Tag]] = {}
        self._comparison_temps: dict[int, list[str]] = {}
        self._unsupported_comparison_rungs: set[int] = set()
        self._timers: dict[str, PLCopenTimerExport] = {}
        self._oneshots: dict[int, PLCopenOneShotExport] = {}
        self._oneshot_tags: dict[str, list[Tag]] = {}
        self._diagnostics: list[ConversionDiagnostic] = []
        self._function_block_instances: dict[str, BlockInterface] = {}
        self._generated_blocks: dict[str, GeneratedFunctionBlock] = {}
        self._withheld_blocks: set[str] = set()
        self._tag_names: dict[str, str] = {}
        self._expression_temps: dict[int, str] = {}
        self._expression_bit_temps: dict[int, tuple[str, str]] = {}
        self._expression_temp_count = 0

    def prepare(self, controller: Controller) -> PLCopenOperandPlan:
        """Discover all required symbols in deterministic source order."""

        self._reset()
        self._prepare_operands(controller)
        self._prepare_timers(controller)
        self._prepare_oneshots(controller)
        return PLCopenOperandPlan(
            operand_names=dict(self._operand_names),
            boolean_operands=frozenset(self._boolean_operands),
            generated_tags=tuple(self._generated_tags),
            comparison_tags={
                name: tuple(tags) for name, tags in self._comparison_tags.items()
            },
            comparison_temps={
                rung: tuple(names) for rung, names in self._comparison_temps.items()
            },
            unsupported_comparison_rungs=frozenset(self._unsupported_comparison_rungs),
            timers=dict(self._timers),
            oneshots=dict(self._oneshots),
            oneshot_tags={
                name: tuple(tags) for name, tags in self._oneshot_tags.items()
            },
            diagnostics=tuple(self._diagnostics),
            function_block_instances=dict(self._function_block_instances),
            generated_blocks=tuple(self._generated_blocks.values()),
            tag_names=dict(self._tag_names),
            expression_temps=dict(self._expression_temps),
            expression_bit_temps=dict(self._expression_bit_temps),
        )

    def _reset(self) -> None:
        self._operand_names = {}
        self._boolean_operands = set()
        self._generated_tags = []
        self._comparison_tags = {}
        self._comparison_temps = {}
        self._unsupported_comparison_rungs = set()
        self._timers = {}
        self._oneshots = {}
        self._oneshot_tags = {}
        self._diagnostics = []
        self._function_block_instances = {}
        self._generated_blocks = {}
        self._withheld_blocks = set()
        self._tag_names = {}
        self._expression_temps = {}
        self._expression_bit_temps = {}
        self._expression_temp_count = 0

    def _prepare_operands(self, controller: Controller) -> None:
        tags = list(controller.tags.values())
        for program in controller.iter_programs():
            tags.extend(program.tags.values())
        names = {tag.name for tag in tags}
        self._prepare_function_block_instances(tags, names)
        aliases_by_target = {tag.alias_for: tag.name for tag in tags if tag.alias_for}
        for program in controller.iter_programs():
            tags_by_name = dict(controller.tags)
            tags_by_name.update(program.tags)
            for routine in program.iter_routines():
                for rung in routine.ladder_rungs:
                    if rung.text is None and rung.network is not None:
                        self._prepare_network_operands(rung.network, names, program.name, routine.name, rung.number)
                        continue
                    parsed = parse_supported_rung(rung.text)
                    if parsed is None:
                        continue
                    comparisons = [
                        operand_text
                        for opcode, operand_text in parsed.tail_conditions
                        if opcode in COMPARISON_TYPES
                    ]
                    if any(
                        self._comparison_uses_unsupported_type(
                            operand_text,
                            tags_by_name,
                        )
                        for operand_text in comparisons
                    ):
                        self._unsupported_comparison_rungs.add(id(rung))
                        continue
                    if comparisons:
                        temp_names: list[str] = []
                        for index in range(len(comparisons)):
                            base = (
                                f"Cmp_{program.name}_{routine.name}_"
                                f"{rung.number if rung.number is not None else 'N'}_"
                                f"{index + 1}"
                            )
                            temp_name = unique_portable_name(base, names)
                            names.add(temp_name)
                            temp_names.append(temp_name)
                            self._comparison_tags.setdefault(
                                program.name,
                                [],
                            ).append(
                                Tag(
                                    name=temp_name,
                                    data_type="BOOL",
                                    description=(
                                        "TwinForge comparison result for "
                                        f"{routine.name} rung {rung.number}"
                                    ),
                                )
                            )
                        self._comparison_temps[id(rung)] = temp_names
                    for opcode, operand_text in parsed.instructions:
                        operands = (
                            split_arguments(operand_text)
                            if opcode
                            in {
                                *COMPARISON_TYPES,
                                *VALUE_BLOCK_TYPES,
                            }
                            else [operand_text]
                        )
                        if opcode in {"TON", "TOF", "RTO", "CTU", "CTD"}:
                            operands = [split_arguments(operand_text)[0]]
                        for operand in operands:
                            is_boolean = opcode in {
                                "XIC",
                                "XIO",
                                "OTE",
                                "OTL",
                                "OTU",
                            }
                            if is_boolean:
                                self._boolean_operands.add(operand)
                            if _IEC_OPERAND.fullmatch(
                                operand
                            ) or _NUMERIC_LITERAL.fullmatch(operand):
                                continue
                            portable = aliases_by_target.get(operand)
                            if portable is None:
                                portable = unique_portable_name(
                                    operand,
                                    names,
                                )
                                names.add(portable)
                                self._generated_tags.append(
                                    Tag(
                                        name=portable,
                                        data_type=("BOOL" if is_boolean else "REAL"),
                                        description=(
                                            "Portable surrogate for Rockwell "
                                            f"operand {operand}"
                                        ),
                                        metadata={"plcopen_source_operand": operand},
                                    )
                                )
                                self._diagnostic(
                                    "raw_operand_rewritten",
                                    "raw Rockwell operand was replaced by an "
                                    "IEC-safe surrogate variable",
                                    portable,
                                    raw_value=operand,
                                )
                            self._operand_names[operand] = portable

    def _prepare_function_block_instances(self, tags: list[Tag], names: set[str]) -> None:
        """Find IEC timer instances and give non-IEC tag names an IEC-safe name."""
        for tag in tags:
            inputs = tag.metadata.get("iec_function_block_inputs") or {}
            generated = GENERATED_LIBRARY.get(tag.metadata.get("function_block_semantics") or "")
            if tag.data_type in IEC_TIMER_TYPES and "PT" in inputs:
                self._function_block_instances[tag.name] = timer_interface(tag.data_type, str(inputs["PT"]))
            elif generated is not None and not (generated.verified or self._include_unverified_blocks):
                if generated.name not in self._withheld_blocks:
                    self._withheld_blocks.add(generated.name)
                    self._diagnostic(
                        "generated_block_unverified",
                        f"{generated.name} reproduces {tag.data_type} behaviour that is not yet verified "
                        f"({generated.source}); its instances are not exported",
                        generated.name,
                    )
            elif generated is not None:
                constant_pins = [pin for pin, _ in generated.inputs if pin in inputs]
                self._function_block_instances[tag.name] = BlockInterface(
                    generated.name, tuple(pin for pin, _ in generated.inputs),
                    tuple(pin for pin, _ in generated.outputs), generated.bool_outputs,
                    tuple((pin, str(inputs[pin])) for pin in constant_pins), standard=False,
                )
                self._generated_blocks.setdefault(generated.name, generated)
            if _IEC_IDENTIFIER.fullmatch(tag.name):
                continue
            portable = unique_portable_name(tag.name, names)
            names.add(portable)
            self._tag_names[tag.name] = portable
            self._operand_names[tag.name] = portable
            self._diagnostic(
                "tag_name_rewritten",
                "source tag name is not an IEC identifier and was declared under an IEC-safe name",
                portable,
                raw_value=tag.name,
            )

    def _prepare_network_operands(
        self, network: LadderSeries, names: set[str], program: str = "", routine: str = "", rung: int | None = None,
    ) -> None:
        """Declare surrogates for network operands that are not IEC identifiers.

        Only networks the LD emitter can encode are considered; every
        instruction in one is a contact or coil, so its operand is BOOL by
        use. A raw source operand such as Machine Expert - Basic's unnamed
        `%I0.1` (a real I/O point with no symbol) becomes one IEC-safe
        surrogate, reused wherever the operand recurs.
        """
        if network_unsupported_reason(network, self._function_block_instances) is not None:
            return
        for instruction in network_instructions(network):
            operand = instruction.operand or ""
            if instruction.expression is not None:
                self._prepare_expression(instruction.expression, names, program, routine, rung)
                continue
            if instruction.operation in (LadderOperation.FUNCTION_BLOCK_INPUT,
                                         LadderOperation.BLOCK_OUTPUT_REFERENCE):
                continue  # a block pin, not a variable
            member = split_member(operand)
            if member is not None:
                # A timer output read as a contact: `%TM2.Q` -> `<instance>.Q`.
                root, name = member
                self._operand_names[operand] = f"{self._operand_names.get(root, root)}.{name}"
                continue
            self._boolean_operands.add(operand)
            if _IEC_OPERAND.fullmatch(operand) or operand in self._operand_names:
                continue
            portable = unique_portable_name(operand, names)
            names.add(portable)
            self._generated_tags.append(
                Tag(
                    name=portable,
                    data_type="BOOL",
                    description=f"Portable surrogate for source operand {operand}",
                    metadata={"plcopen_source_operand": operand},
                )
            )
            self._diagnostic(
                "raw_operand_rewritten",
                "raw source operand was replaced by an IEC-safe surrogate variable",
                portable,
                raw_value=operand,
            )
            self._operand_names[operand] = portable

    def _prepare_expression(
        self, expression: Expression, names: set[str], program: str, routine: str, rung: int | None,
    ) -> None:
        """Typed surrogates for raw operands, and temporaries for intermediate values."""
        direct = expression.right if expression.operator == ASSIGNMENT_OPERATOR else None
        for node in expression.iter_nodes():
            if node.kind == "variable" and not _IEC_IDENTIFIER.fullmatch(node.text) \
                    and node.text not in self._operand_names:
                portable = unique_portable_name(node.text, names)
                names.add(portable)
                self._generated_tags.append(Tag(
                    name=portable, data_type=node.data_type,
                    description=f"Portable surrogate for source operand {node.text}",
                    metadata={"plcopen_source_operand": node.text},
                ))
                self._diagnostic(
                    "raw_operand_rewritten",
                    "raw source operand was replaced by an IEC-safe surrogate variable",
                    portable,
                    raw_value=node.text,
                )
                self._operand_names[node.text] = portable
            needs_temp = node.kind in ("binary", "call") and node.operator != ASSIGNMENT_OPERATOR                 and node is not direct
            if needs_temp:
                self._expression_temps[id(node)] = self._expression_temp(
                    node.data_type, names, program, routine, rung)
            if node.kind == "call":
                bits = BIT_STRING_TYPES[node.data_type]
                self._expression_bit_temps[id(node)] = (
                    self._expression_temp(bits, names, program, routine, rung),
                    self._expression_temp(bits, names, program, routine, rung),
                )

    def _expression_temp(self, data_type: str, names: set[str], program: str, routine: str, rung: int | None) -> str:
        """Declare one typed program variable holding an intermediate value."""
        self._expression_temp_count += 1
        index = self._expression_temp_count
        rung_label = rung if rung is not None else "N"
        temp = unique_portable_name(f"Expr_{program}_{routine}_{rung_label}_{index}", names)
        names.add(temp)
        self._comparison_tags.setdefault(program, []).append(Tag(
            name=temp, data_type=data_type,
            description=f"TwinForge expression value for {routine} rung {rung}",
        ))
        return temp

    def _prepare_timers(self, controller: Controller) -> None:
        tags = [
            *controller.tags.values(),
            *(
                tag
                for program in controller.iter_programs()
                for tag in program.tags.values()
            ),
        ]
        names = {tag.name for tag in tags}
        names.update(tag.name for tag in self._generated_tags)
        for tag in tags:
            if (tag.data_type or "").upper() != "TIMER":
                continue
            preset_ms = timer_member_integer(tag, "PRE")
            if preset_ms is None:
                self._diagnostic(
                    "timer_preset_missing",
                    "TIMER has no readable decorated PRE value; zero "
                    "milliseconds was used",
                    tag.name,
                )
                preset_ms = 0
            generated: list[str] = []
            for suffix, data_type in (
                ("IN", "BOOL"),
                ("DN", "BOOL"),
                ("ET", "TIME"),
                ("Executed", "BOOL"),
            ):
                name = unique_portable_name(f"{tag.name}_{suffix}", names)
                names.add(name)
                generated.append(name)
                self._generated_tags.append(
                    Tag(
                        name=name,
                        data_type=data_type,
                        description=(f"TwinForge IEC timer {suffix} for {tag.name}"),
                    )
                )
            self._timers[tag.name] = PLCopenTimerExport(
                preset_ms=preset_ms,
                input_name=generated[0],
                done_name=generated[1],
                elapsed_name=generated[2],
                executed_name=generated[3],
            )

    def _prepare_oneshots(self, controller: Controller) -> None:
        names = set(controller.tags)
        names.update(tag.name for tag in self._generated_tags)
        for program in controller.iter_programs():
            names.update(program.tags)
            names.update(
                tag.name for tag in self._comparison_tags.get(program.name, [])
            )
            for routine in program.iter_routines():
                for rung in routine.ladder_rungs:
                    parsed = parse_supported_rung(rung.text)
                    if parsed is None:
                        continue
                    instructions = [
                        operand
                        for opcode, operand in parsed.tail_conditions
                        if opcode == "ONS"
                    ]
                    if not instructions:
                        continue
                    storage_operand = instructions[0]
                    base = (
                        f"ONS_{program.name}_{routine.name}_"
                        f"{rung.number if rung.number is not None else 'N'}"
                    )
                    generated: list[str] = []
                    for suffix in ("FB", "IN", "Pulse", "Executed"):
                        name = unique_portable_name(
                            f"{base}_{suffix}",
                            names,
                        )
                        names.add(name)
                        generated.append(name)
                    tags = self._oneshot_tags.setdefault(program.name, [])
                    tags.append(
                        Tag(
                            name=generated[0],
                            data_type="R_TRIG",
                            description=(
                                "TwinForge rising-edge instance for Rockwell "
                                f"ONS storage operand {storage_operand}"
                            ),
                            metadata={
                                "plcopen_derived_type": (self._rising_trigger_type),
                                "rockwell_ons_storage": storage_operand,
                            },
                        )
                    )
                    for name, description in (
                        (generated[1], "input"),
                        (generated[2], "one-scan pulse"),
                        (generated[3], "execution"),
                    ):
                        tags.append(
                            Tag(
                                name=name,
                                data_type="BOOL",
                                description=(
                                    f"TwinForge ONS {description} for {storage_operand}"
                                ),
                            )
                        )
                    self._oneshots[id(rung)] = PLCopenOneShotExport(
                        instance_name=generated[0],
                        input_name=generated[1],
                        pulse_name=generated[2],
                        executed_name=generated[3],
                    )

    def _comparison_uses_unsupported_type(
        self,
        operand_text: str,
        tags_by_name: dict[str, Tag],
    ) -> bool:
        for operand in split_arguments(operand_text):
            root_name = operand.split(".", 1)[0]
            tag = tags_by_name.get(root_name)
            if tag is None:
                continue
            export_type = self._tag_export_type(tag)
            if export_type == "TIMER" and operand == f"{root_name}.ACC":
                continue
            if export_type not in PLCOPEN_PRIMITIVE_TYPES:
                return True
        return False

    def _tag_export_type(self, tag: Tag) -> str:
        if tag.data_type:
            return tag.data_type.upper()
        if tag.alias_for:
            if tag.name in self._boolean_operands:
                return "BOOL"
            if (tag.radix or "").lower() == "float":
                return "REAL"
            return "BOOL"
        return ""

    def _diagnostic(
        self,
        code: str,
        message: str,
        object_name: str | None,
        *,
        raw_value: str | None = None,
    ) -> None:
        self._diagnostics.append(
            ConversionDiagnostic(
                severity=DiagnosticSeverity.WARNING,
                code=code,
                message=message,
                object_name=object_name,
                raw_value=raw_value,
            )
        )
