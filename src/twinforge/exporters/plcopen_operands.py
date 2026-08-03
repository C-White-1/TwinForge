"""Prepare deterministic PLCopen symbols before XML serialization."""

from __future__ import annotations

from dataclasses import dataclass
import re

from twinforge.converters import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import Controller, Tag

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

    def __init__(self, *, rising_trigger_type: str = "R_TRIG") -> None:
        self._rising_trigger_type = rising_trigger_type
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

    def _prepare_operands(self, controller: Controller) -> None:
        tags = list(controller.tags.values())
        for program in controller.iter_programs():
            tags.extend(program.tags.values())
        names = {tag.name for tag in tags}
        aliases_by_target = {tag.alias_for: tag.name for tag in tags if tag.alias_for}
        for program in controller.iter_programs():
            tags_by_name = dict(controller.tags)
            tags_by_name.update(program.tags)
            for routine in program.iter_routines():
                for rung in routine.ladder_rungs:
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
