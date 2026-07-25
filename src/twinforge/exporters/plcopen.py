from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from twinforge.converters import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import Controller, LadderRung, Program, Tag, Task

from .plcopen_codesys import CodesysProfileSupport
from .plcopen_rll import (
    COMPARISON_TYPES as _COMPARISON_TYPES,
    SUPPORTED_RLL_INSTRUCTIONS as PLCOPEN_SUPPORTED_RLL_INSTRUCTIONS,
    VALUE_BLOCK_TYPES as _VALUE_BLOCK_TYPES,
    parse_jsr as _parse_jsr,
    parse_supported_rung as _parse_supported_rung,
    split_arguments as _split_arguments,
)
from .plcopen_types import (
    PLCOPEN_201_NAMESPACE,
    PLCOPEN_CODESYS_NAMESPACE,
    PLCopenExportResult,
    PLCopenProfile,
)
from .plcopen_validation import (
    PLCopenValidationError,
    PLCopenValidationUnavailable,
    validate_plcopen_xml,
)
from .plcopen_xml import (
    milliseconds_duration as _milliseconds_duration,
    milliseconds_time_literal as _milliseconds_time_literal,
    plcopen_scalar_value as _plcopen_scalar_value,
    qualified_name as _q,
    timer_member_integer as _timer_member_integer,
    unique_portable_name as _unique_portable_name,
    variable_add_data as _variable_add_data,
)

__all__ = [
    "PLCOPEN_201_NAMESPACE",
    "PLCOPEN_CODESYS_NAMESPACE",
    "PLCOPEN_SUPPORTED_RLL_INSTRUCTIONS",
    "PLCopenExporter",
    "PLCopenExportResult",
    "PLCopenProfile",
    "PLCopenValidationError",
    "PLCopenValidationUnavailable",
    "validate_plcopen_xml",
]

XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
TWINFORGE_RLL_EXTENSION = "https://twinforge.dev/plcopenxml/rockwell-rll"
TWINFORGE_ALIAS_EXTENSION = "https://twinforge.dev/plcopenxml/rockwell-alias"
TWINFORGE_ONS_EXTENSION = "https://twinforge.dev/plcopenxml/rockwell-ons"
TWINFORGE_ENGINEERING_UNIT_EXTENSION = (
    "https://twinforge.dev/plcopenxml/engineering-unit"
)

_PRIMITIVE_TYPES = {
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
_NOP_INSTRUCTION = re.compile(r"\s*NOP\s*\(\s*\)\s*;\s*")
_IEC_OPERAND = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")
_NUMERIC_LITERAL = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)")
@dataclass(frozen=True)
class _TimerExport:
    preset_ms: int
    input_name: str
    done_name: str
    elapsed_name: str
    executed_name: str


@dataclass(frozen=True)
class _OneShotExport:
    instance_name: str
    input_name: str
    pulse_name: str
    executed_name: str


class PLCopenExporter:
    def __init__(self, profile: PLCopenProfile | str = PLCopenProfile.STANDARD_201):
        self.profile = PLCopenProfile(profile)
        self.diagnostics: list[ConversionDiagnostic] = []
        self._next_local_id = 1
        self._codesys = CodesysProfileSupport(PLCOPEN_CODESYS_NAMESPACE)
        self._operand_names: dict[str, str] = {}
        self._boolean_operands: set[str] = set()
        self._generated_tags: list[Tag] = []
        self._comparison_tags: dict[str, list[Tag]] = {}
        self._comparison_temps: dict[int, list[str]] = {}
        self._unsupported_comparison_rungs: set[int] = set()
        self._timers: dict[str, _TimerExport] = {}
        self._oneshots: dict[int, _OneShotExport] = {}
        self._oneshot_tags: dict[str, list[Tag]] = {}

    def build(
        self,
        controller: Controller,
        *,
        project_name: str | None = None,
        creation_time: datetime | None = None,
    ) -> ET.Element:
        self.diagnostics = []
        self._next_local_id = 1
        self._codesys.reset()
        self._operand_names = {}
        self._boolean_operands = set()
        self._generated_tags = []
        self._comparison_tags = {}
        self._comparison_temps = {}
        self._unsupported_comparison_rungs = set()
        self._timers = {}
        self._oneshots = {}
        self._oneshot_tags = {}
        self._prepare_operands(controller)
        self._prepare_timers(controller)
        self._prepare_oneshots(controller)
        namespace = self.profile.namespace
        ET.register_namespace("", namespace)
        root = ET.Element(_q(namespace, "project"))
        timestamp = (creation_time or datetime.now(timezone.utc)).isoformat()
        ET.SubElement(
            root,
            _q(namespace, "fileHeader"),
            {
                "companyName": "TwinForge",
                "productName": "TwinForge",
                "productVersion": "0.1.0",
                "creationDateTime": timestamp,
            },
        )
        self._content_header(root, project_name or controller.name or "TwinForge")

        types = ET.SubElement(root, _q(namespace, "types"))
        ET.SubElement(types, _q(namespace, "dataTypes"))
        pous = ET.SubElement(types, _q(namespace, "pous"))
        instances = ET.SubElement(root, _q(namespace, "instances"))
        configurations = ET.SubElement(instances, _q(namespace, "configurations"))

        if self.profile is PLCopenProfile.CODESYS:
            self._codesys_application(root, controller)
        else:
            for program in controller.iter_programs():
                self._program(pous, program)
            self._standard_configuration(configurations, controller)
        return root

    def export(
        self,
        controller: Controller,
        *,
        destination: str | Path | None = None,
        project_name: str | None = None,
        creation_time: datetime | None = None,
    ) -> PLCopenExportResult:
        root = self.build(
            controller,
            project_name=project_name,
            creation_time=creation_time,
        )
        ET.indent(root, space="  ")
        xml = ET.tostring(root, encoding="unicode", xml_declaration=True)
        if destination is not None:
            Path(destination).write_text(xml, encoding="utf-8")
        return PLCopenExportResult(xml=xml, diagnostics=list(self.diagnostics))

    def _content_header(self, root: ET.Element, name: str) -> None:
        ns = self.profile.namespace
        header = ET.SubElement(root, _q(ns, "contentHeader"), {"name": name})
        coordinate = ET.SubElement(header, _q(ns, "coordinateInfo"))
        for language in ("fbd", "ld", "sfc"):
            element = ET.SubElement(coordinate, _q(ns, language))
            ET.SubElement(element, _q(ns, "scaling"), {"x": "1", "y": "1"})

    def _standard_configuration(
        self, configurations: ET.Element, controller: Controller
    ) -> None:
        ns = self.profile.namespace
        configuration = ET.SubElement(
            configurations, _q(ns, "configuration"), {"name": controller.name or "PLC"}
        )
        resource = ET.SubElement(
            configuration, _q(ns, "resource"), {"name": "Application"}
        )
        for task in controller.iter_tasks():
            self._task(resource, task)
        self._variables(
            resource,
            "globalVars",
            [*controller.tags.values(), *self._generated_tags],
        )

    def _codesys_application(self, root: ET.Element, controller: Controller) -> None:
        """Delegate CODESYS project wrapping to the target adapter."""

        self._codesys.emit_application(
            root,
            controller,
            self._generated_tags,
            needs_standard_library=bool(self._timers or self._oneshots),
            emit_task=lambda parent, task: self._task(
                parent,
                task,
                codesys=True,
            ),
            emit_variables=lambda parent, tags: self._variables(
                parent,
                "globalVars",
                list(tags),
                attributes={"name": "ControllerTags"},
            ),
            emit_program=lambda parent, program: self._program(
                parent,
                program,
                codesys=True,
            ),
        )

    def _task(self, parent: ET.Element, task: Task, *, codesys: bool = False) -> None:
        ns = self.profile.namespace
        attributes = {
            "name": task.name,
            "priority": str(task.priority if task.priority is not None else 1),
        }
        if task.rate is not None:
            attributes["interval"] = _milliseconds_duration(task.rate)
        task_element = ET.SubElement(parent, _q(ns, "task"), attributes)
        programs = task.scheduled_programs
        if not programs and task.scheduled_program_names:
            self._diagnostic(
                "unresolved_scheduled_programs",
                "task contains program names that were not resolved",
                task.name,
                raw_value=", ".join(task.scheduled_program_names),
            )
        for program in programs:
            instance = ET.SubElement(
                task_element,
                _q(ns, "pouInstance"),
                {"name": program.name, "typeName": "" if codesys else program.name},
            )
            if codesys:
                documentation = ET.SubElement(instance, _q(ns, "documentation"))
                ET.SubElement(documentation, _q(XHTML_NAMESPACE, "xhtml"))
        if codesys:
            self._codesys.append_task_settings(task_element, task)

    def _program(
        self, parent: ET.Element, program: Program, *, codesys: bool = False
    ) -> None:
        ns = self.profile.namespace
        pou = ET.SubElement(
            parent, _q(ns, "pou"), {"name": program.name, "pouType": "program"}
        )
        interface = ET.SubElement(pou, _q(ns, "interface"))
        self._variables(
            interface,
            "localVars",
            [
                *program.tags.values(),
                *self._comparison_tags.get(program.name, []),
                *self._oneshot_tags.get(program.name, []),
            ],
        )
        routine = program.main_routine
        if routine is None:
            self._diagnostic(
                "program_without_main_routine",
                "program has no main routine",
                program.name,
            )
            return
        action_routines = [
            candidate
            for candidate in program.iter_routines()
            if candidate is not routine
        ]
        action_names = {candidate.name for candidate in action_routines}
        if action_routines:
            actions = ET.SubElement(pou, _q(ns, "actions"))
            for action_routine in action_routines:
                action = ET.SubElement(
                    actions, _q(ns, "action"), {"name": action_routine.name}
                )
                self._routine_body(
                    action,
                    action_routine.ladder_rungs,
                    program.name,
                    action_names=action_names,
                    codesys=codesys,
                )
                if codesys:
                    self._codesys.append_object_id(
                        action,
                        self._codesys.object_id(
                            f"Application/program/{program.name}/action/{action_routine.name}"
                        ),
                    )
        self._routine_body(
            pou,
            routine.ladder_rungs,
            program.name,
            action_names=action_names,
            codesys=codesys,
        )
        if codesys:
            self._codesys.append_object_id(
                pou,
                self._codesys.object_id(
                    f"Application/program/{program.name}"
                ),
            )

    def _routine_body(
        self,
        parent: ET.Element,
        rungs: list[LadderRung],
        program_name: str,
        *,
        action_names: set[str],
        codesys: bool,
    ) -> None:
        ns = self.profile.namespace
        body = ET.SubElement(parent, _q(ns, "body"))
        ld = ET.SubElement(body, _q(ns, "LD"))
        if codesys:
            ld.append(ET.Comment("ObjectVersion: LD2"))
        for rung in rungs:
            self._rung(
                ld,
                rung,
                program_name,
                action_names=action_names,
                codesys=codesys,
            )

    def _variables(
        self,
        parent: ET.Element,
        list_name: str,
        tags,
        *,
        attributes: dict[str, str] | None = None,
    ) -> ET.Element | None:
        supported: list[Tag] = []
        for tag in tags:
            data_type = self._tag_export_type(tag)
            if tag.alias_for:
                self._diagnostic(
                    "alias_exported_as_surrogate",
                    "Rockwell alias was exported as a portable variable without an I/O binding",
                    tag.name,
                    raw_value=tag.alias_for,
                )
            derived_type = tag.metadata.get("plcopen_derived_type")
            if (
                data_type not in _PRIMITIVE_TYPES
                and data_type != "TIMER"
                and derived_type is None
            ):
                self._diagnostic(
                    "unsupported_variable_type",
                    "variable is preserved in the source model but not declared in this PLCopen milestone",
                    tag.name,
                    raw_value=tag.data_type,
                )
                continue
            if tag.dimensions:
                self._diagnostic(
                    "array_variable_not_exported",
                    "array variable export is not implemented",
                    tag.name,
                    raw_value=tag.dimensions,
                )
                continue
            supported.append(tag)
        if not supported:
            return None
        ns = self.profile.namespace
        variable_list = ET.SubElement(
            parent, _q(ns, list_name), attributes if attributes is not None else {}
        )
        for tag in supported:
            derived_type = tag.metadata.get("plcopen_derived_type")
            variable = ET.SubElement(
                variable_list, _q(ns, "variable"), {"name": tag.name}
            )
            type_element = ET.SubElement(variable, _q(ns, "type"))
            if derived_type is not None:
                ET.SubElement(
                    type_element,
                    _q(ns, "derived"),
                    {"name": str(derived_type)},
                )
            elif self._tag_export_type(tag) == "TIMER":
                timer_type = (
                    self._codesys.library_type("TON")
                    if self.profile is PLCopenProfile.CODESYS
                    else "TON"
                )
                ET.SubElement(type_element, _q(ns, "derived"), {"name": timer_type})
            else:
                ET.SubElement(type_element, _q(ns, self._tag_export_type(tag)))
            if tag.initial_value is not None:
                initial_value = ET.SubElement(variable, _q(ns, "initialValue"))
                ET.SubElement(
                    initial_value,
                    _q(ns, "simpleValue"),
                    {"value": _plcopen_scalar_value(tag)},
                )
            source_operand = tag.alias_for or tag.metadata.get("plcopen_source_operand")
            if source_operand:
                add_data = _variable_add_data(variable, ns)
                data = ET.SubElement(
                    add_data,
                    _q(ns, "data"),
                    {
                        "name": TWINFORGE_ALIAS_EXTENSION,
                        "handleUnknown": "preserve",
                    },
                )
                alias_for = ET.SubElement(data, "AliasFor", {"xmlns": ""})
                alias_for.text = source_operand
            ons_storage = tag.metadata.get("rockwell_ons_storage")
            if ons_storage:
                add_data = _variable_add_data(variable, ns)
                data = ET.SubElement(
                    add_data,
                    _q(ns, "data"),
                    {
                        "name": TWINFORGE_ONS_EXTENSION,
                        "handleUnknown": "preserve",
                    },
                )
                storage = ET.SubElement(data, "StorageOperand", {"xmlns": ""})
                storage.text = str(ons_storage)
            if tag.engineering_unit is not None:
                add_data = _variable_add_data(variable, ns)
                data = ET.SubElement(
                    add_data,
                    _q(ns, "data"),
                    {
                        "name": TWINFORGE_ENGINEERING_UNIT_EXTENSION,
                        "handleUnknown": "preserve",
                    },
                )
                unit = ET.SubElement(
                    data,
                    "EngineeringUnit",
                    {
                        "xmlns": "",
                        "Symbol": tag.engineering_unit.symbol,
                        "Source": tag.engineering_unit.source.value,
                        "Confidence": tag.engineering_unit.confidence.value,
                    },
                )
                if tag.engineering_unit.source_operand:
                    unit.set(
                        "SourceOperand",
                        tag.engineering_unit.source_operand,
                    )
                if tag.engineering_unit.inherited_from:
                    unit.set(
                        "InheritedFrom",
                        tag.engineering_unit.inherited_from,
                    )
                for evidence in tag.engineering_unit_evidence:
                    attributes = {
                        "Symbol": evidence.symbol,
                        "Source": evidence.source.value,
                        "Confidence": evidence.confidence.value,
                    }
                    if evidence.source_operand:
                        attributes["SourceOperand"] = evidence.source_operand
                    if evidence.inherited_from:
                        attributes["InheritedFrom"] = evidence.inherited_from
                    ET.SubElement(unit, "Evidence", attributes)
            if tag.description:
                documentation = ET.SubElement(variable, _q(ns, "documentation"))
                xhtml = ET.SubElement(documentation, _q(XHTML_NAMESPACE, "xhtml"))
                xhtml.text = tag.description
        return variable_list

    def _rung(
        self,
        ld: ET.Element,
        rung: LadderRung,
        program_name: str,
        *,
        action_names: set[str],
        codesys: bool,
    ) -> None:
        ns = self.profile.namespace
        if rung.text and _NOP_INSTRUCTION.fullmatch(rung.text):
            self._comment(
                ld,
                rung.comment or "Rockwell NOP (intentional no operation)",
                raw_rll=rung.text,
            )
            return
        if id(rung) in self._unsupported_comparison_rungs:
            raw = rung.text or ""
            self._diagnostic(
                "unsupported_comparison_operand_type",
                "comparison references a structured variable type that is not exported yet",
                program_name,
                raw_value=raw,
            )
            self._comment(ld, f"Unsupported Rockwell RLL: {raw}", raw_rll=raw)
            return
        jsr_target = _parse_jsr(rung.text)
        if jsr_target is not None:
            if jsr_target not in action_names:
                raw = rung.text or ""
                self._diagnostic(
                    "unresolved_jsr_target",
                    "JSR target does not resolve to a routine in the program",
                    program_name,
                    raw_value=jsr_target,
                )
                self._comment(ld, f"Unresolved Rockwell RLL: {raw}", raw_rll=raw)
                return
            self._action_call(ld, jsr_target, comment=rung.comment, codesys=codesys)
            return
        parsed = _parse_supported_rung(rung.text)
        if parsed is None:
            raw = rung.text or ""
            self._diagnostic(
                "unsupported_rll_rung",
                "rung was emitted as a non-executable comment because it contains unsupported RLL",
                program_name,
                raw_value=raw,
            )
            self._comment(ld, f"Unsupported Rockwell RLL: {raw}", raw_rll=raw)
            return
        timer_operands = [
            _split_arguments(operand)[0] if opcode == "TON" else operand
            for opcode, operand in parsed.outputs
            if opcode in {"TON", "RES"}
        ]
        if any(operand not in self._timers for operand in timer_operands):
            raw = rung.text or ""
            self._diagnostic(
                "unsupported_timer_operand",
                "TON or RES references a tag that is not an exported TIMER",
                program_name,
                raw_value=raw,
            )
            self._comment(ld, f"Unsupported Rockwell RLL: {raw}", raw_rll=raw)
            return

        rail_id = self._id()
        rail = ET.SubElement(ld, _q(ns, "leftPowerRail"), {"localId": str(rail_id)})
        self._position(rail)
        ET.SubElement(rail, _q(ns, "connectionPointOut"), {"formalParameter": "none"})
        condition_id = rail_id
        if rung.comment:
            self._comment(ld, rung.comment)
        condition_ids = [condition_id]
        if parsed.branches:
            condition_ids = []
            for branch in parsed.branches:
                branch_condition = rail_id
                for opcode, operand in branch:
                    branch_condition = self._contact(
                        ld, opcode, operand, [branch_condition]
                    )
                condition_ids.append(branch_condition)
        comparison_index = 0
        for opcode, operand in parsed.tail_conditions:
            if opcode in {"XIC", "XIO"}:
                condition_ids = [self._contact(ld, opcode, operand, condition_ids)]
            elif opcode == "ONS":
                condition_ids = [
                    self._oneshot_block(
                        ld,
                        self._oneshots[id(rung)],
                        condition_ids,
                    )
                ]
            else:
                temp_name = self._comparison_temps[id(rung)][comparison_index]
                comparison_index += 1
                condition_ids = [
                    self._comparison(ld, opcode, operand, condition_ids, temp_name)
                ]
        execution_ids = condition_ids
        execution_from_block = False
        for opcode, operand in parsed.outputs:
            if opcode == "TON":
                self._timer_block(ld, operand, execution_ids)
            elif opcode == "RES":
                execution_ids = [
                    self._timer_reset_block(
                        ld,
                        operand,
                        execution_ids,
                        input_from_block=execution_from_block,
                    )
                ]
                execution_from_block = True
            elif opcode in _VALUE_BLOCK_TYPES:
                execution_ids = [
                    self._value_block(
                        ld,
                        opcode,
                        operand,
                        execution_ids,
                        input_from_block=execution_from_block,
                    )
                ]
                execution_from_block = True
            else:
                self._coil(
                    ld,
                    opcode,
                    operand,
                    execution_ids,
                    formal_parameter="ENO" if execution_from_block else None,
                )

        right_id = self._id()
        right = ET.SubElement(ld, _q(ns, "rightPowerRail"), {"localId": str(right_id)})
        self._position(right)
        ET.SubElement(right, _q(ns, "connectionPointIn"))

    def _contact(
        self,
        ld: ET.Element,
        opcode: str,
        operand: str,
        condition_ids: list[int],
    ) -> int:
        ns = self.profile.namespace
        local_id = self._id()
        attributes = {"localId": str(local_id)}
        if opcode == "XIO":
            attributes["negated"] = "true"
        contact = ET.SubElement(ld, _q(ns, "contact"), attributes)
        self._position(contact)
        point_in = ET.SubElement(contact, _q(ns, "connectionPointIn"))
        for condition_id in condition_ids:
            self._condition_connection(point_in, condition_id)
        ET.SubElement(contact, _q(ns, "connectionPointOut"))
        variable = ET.SubElement(contact, _q(ns, "variable"))
        variable.text = self._portable_operand(operand)
        return local_id

    def _coil(
        self,
        ld: ET.Element,
        opcode: str,
        operand: str,
        condition_ids: list[int],
        *,
        formal_parameter: str | None = None,
    ) -> int:
        ns = self.profile.namespace
        local_id = self._id()
        attributes = {"localId": str(local_id)}
        if opcode == "OTL":
            attributes["storage"] = "set"
        elif opcode == "OTU":
            attributes["storage"] = "reset"
        coil = ET.SubElement(ld, _q(ns, "coil"), attributes)
        self._position(coil)
        point_in = ET.SubElement(coil, _q(ns, "connectionPointIn"))
        for condition_id in condition_ids:
            self._condition_connection(point_in, condition_id)
            if formal_parameter is not None:
                point_in[-1].set("formalParameter", formal_parameter)
        ET.SubElement(coil, _q(ns, "connectionPointOut"))
        variable = ET.SubElement(coil, _q(ns, "variable"))
        variable.text = self._portable_operand(operand)
        return local_id

    def _comparison(
        self,
        ld: ET.Element,
        opcode: str,
        operand_text: str,
        condition_ids: list[int],
        result_name: str,
    ) -> int:
        ns = self.profile.namespace
        operands = _split_arguments(operand_text)
        if len(operands) != 2:
            raise ValueError(f"comparison {opcode} requires two operands")
        input_ids: list[int] = []
        for operand in self._comparison_operands(operands):
            input_id = self._id()
            input_variable = ET.SubElement(
                ld, _q(ns, "inVariable"), {"localId": str(input_id)}
            )
            self._position(input_variable)
            ET.SubElement(input_variable, _q(ns, "connectionPointOut"))
            expression = ET.SubElement(input_variable, _q(ns, "expression"))
            expression.text = self._portable_operand(operand)
            input_ids.append(input_id)

        block_id = self._id()
        block = ET.SubElement(
            ld,
            _q(ns, "block"),
            {"localId": str(block_id), "typeName": _COMPARISON_TYPES[opcode]},
        )
        self._position(block)
        inputs = ET.SubElement(block, _q(ns, "inputVariables"))
        enable = ET.SubElement(inputs, _q(ns, "variable"), {"formalParameter": "EN"})
        enable_point = ET.SubElement(enable, _q(ns, "connectionPointIn"))
        for condition_id in condition_ids:
            self._condition_connection(enable_point, condition_id)
        for index, input_id in enumerate(input_ids, start=1):
            variable = ET.SubElement(
                inputs,
                _q(ns, "variable"),
                {"formalParameter": ""},
            )
            point = ET.SubElement(variable, _q(ns, "connectionPointIn"))
            ET.SubElement(
                point,
                _q(ns, "connection"),
                {"refLocalId": str(input_id)},
            )
        ET.SubElement(block, _q(ns, "inOutVariables"))
        outputs = ET.SubElement(block, _q(ns, "outputVariables"))
        enabled = ET.SubElement(outputs, _q(ns, "variable"), {"formalParameter": "ENO"})
        ET.SubElement(enabled, _q(ns, "connectionPointOut"))
        result = ET.SubElement(outputs, _q(ns, "variable"), {"formalParameter": ""})
        result_point = ET.SubElement(result, _q(ns, "connectionPointOut"))
        expression = ET.SubElement(result_point, _q(ns, "expression"))
        expression.text = result_name
        return self._contact(ld, "XIC", result_name, condition_ids)

    def _timer_block(
        self,
        ld: ET.Element,
        operand_text: str,
        condition_ids: list[int],
    ) -> int:
        ns = self.profile.namespace
        timer_name = _split_arguments(operand_text)[0]
        timer = self._timers[timer_name]
        self._coil(ld, "OTE", timer.input_name, condition_ids)
        condition_right_id = self._id()
        condition_right = ET.SubElement(
            ld,
            _q(ns, "rightPowerRail"),
            {"localId": str(condition_right_id)},
        )
        self._position(condition_right)
        ET.SubElement(condition_right, _q(ns, "connectionPointIn"))

        timer_rail_id = self._id()
        timer_rail = ET.SubElement(
            ld, _q(ns, "leftPowerRail"), {"localId": str(timer_rail_id)}
        )
        self._position(timer_rail)
        ET.SubElement(
            timer_rail,
            _q(ns, "connectionPointOut"),
            {"formalParameter": "none"},
        )
        input_id = self._id()
        input_value = ET.SubElement(
            ld, _q(ns, "inVariable"), {"localId": str(input_id)}
        )
        self._position(input_value)
        ET.SubElement(input_value, _q(ns, "connectionPointOut"))
        input_expression = ET.SubElement(input_value, _q(ns, "expression"))
        input_expression.text = timer.input_name
        preset_id = self._id()
        preset_value = ET.SubElement(
            ld, _q(ns, "inVariable"), {"localId": str(preset_id)}
        )
        self._position(preset_value)
        ET.SubElement(preset_value, _q(ns, "connectionPointOut"))
        preset_expression = ET.SubElement(preset_value, _q(ns, "expression"))
        preset_expression.text = _milliseconds_time_literal(timer.preset_ms)

        block_id = self._id()
        block = ET.SubElement(
            ld,
            _q(ns, "block"),
            {
                "localId": str(block_id),
                "typeName": "TON",
                "instanceName": timer_name,
            },
        )
        self._position(block)
        inputs = ET.SubElement(block, _q(ns, "inputVariables"))
        for parameter, references in (
            ("EN", [timer_rail_id]),
            ("IN", [input_id]),
            ("PT", [preset_id]),
        ):
            variable = ET.SubElement(
                inputs, _q(ns, "variable"), {"formalParameter": parameter}
            )
            point = ET.SubElement(variable, _q(ns, "connectionPointIn"))
            for reference in references:
                self._condition_connection(point, reference)
        ET.SubElement(block, _q(ns, "inOutVariables"))
        outputs = ET.SubElement(block, _q(ns, "outputVariables"))
        enabled = ET.SubElement(outputs, _q(ns, "variable"), {"formalParameter": "ENO"})
        ET.SubElement(enabled, _q(ns, "connectionPointOut"))
        for parameter, name in (
            ("Q", timer.done_name),
            ("ET", timer.elapsed_name),
        ):
            variable = ET.SubElement(
                outputs, _q(ns, "variable"), {"formalParameter": parameter}
            )
            point = ET.SubElement(variable, _q(ns, "connectionPointOut"))
            expression = ET.SubElement(point, _q(ns, "expression"))
            expression.text = name
        if self.profile is PLCopenProfile.CODESYS:
            self._codesys.append_call_type(block)
        return self._coil(
            ld,
            "OTE",
            timer.executed_name,
            [block_id],
            formal_parameter="ENO",
        )

    def _timer_reset_block(
        self,
        ld: ET.Element,
        timer_name: str,
        condition_ids: list[int],
        *,
        input_from_block: bool = False,
    ) -> int:
        ns = self.profile.namespace
        timer = self._timers[timer_name]
        value_ids: list[int] = []
        for value in ("FALSE", _milliseconds_time_literal(timer.preset_ms)):
            local_id = self._id()
            variable = ET.SubElement(
                ld, _q(ns, "inVariable"), {"localId": str(local_id)}
            )
            self._position(variable)
            ET.SubElement(variable, _q(ns, "connectionPointOut"))
            expression = ET.SubElement(variable, _q(ns, "expression"))
            expression.text = value
            value_ids.append(local_id)
        block_id = self._id()
        block = ET.SubElement(
            ld,
            _q(ns, "block"),
            {
                "localId": str(block_id),
                "typeName": "TON",
                "instanceName": timer_name,
            },
        )
        self._position(block)
        inputs = ET.SubElement(block, _q(ns, "inputVariables"))
        for parameter, references in (
            ("EN", condition_ids),
            ("IN", [value_ids[0]]),
            ("PT", [value_ids[1]]),
        ):
            variable = ET.SubElement(
                inputs, _q(ns, "variable"), {"formalParameter": parameter}
            )
            point = ET.SubElement(variable, _q(ns, "connectionPointIn"))
            for reference in references:
                self._condition_connection(
                    point,
                    reference,
                    formal_parameter=(
                        "ENO" if parameter == "EN" and input_from_block else None
                    ),
                )
        ET.SubElement(block, _q(ns, "inOutVariables"))
        outputs = ET.SubElement(block, _q(ns, "outputVariables"))
        enabled = ET.SubElement(outputs, _q(ns, "variable"), {"formalParameter": "ENO"})
        ET.SubElement(enabled, _q(ns, "connectionPointOut"))
        for parameter, name in (
            ("Q", timer.done_name),
            ("ET", timer.elapsed_name),
        ):
            variable = ET.SubElement(
                outputs, _q(ns, "variable"), {"formalParameter": parameter}
            )
            point = ET.SubElement(variable, _q(ns, "connectionPointOut"))
            expression = ET.SubElement(point, _q(ns, "expression"))
            expression.text = name
        if self.profile is PLCopenProfile.CODESYS:
            self._codesys.append_call_type(block)
        return block_id

    def _oneshot_block(
        self,
        ld: ET.Element,
        oneshot: _OneShotExport,
        condition_ids: list[int],
    ) -> int:
        ns = self.profile.namespace
        self._coil(ld, "OTE", oneshot.input_name, condition_ids)
        input_right = ET.SubElement(
            ld, _q(ns, "rightPowerRail"), {"localId": str(self._id())}
        )
        self._position(input_right)
        ET.SubElement(input_right, _q(ns, "connectionPointIn"))

        trigger_rail_id = self._id()
        trigger_rail = ET.SubElement(
            ld,
            _q(ns, "leftPowerRail"),
            {"localId": str(trigger_rail_id)},
        )
        self._position(trigger_rail)
        ET.SubElement(
            trigger_rail,
            _q(ns, "connectionPointOut"),
            {"formalParameter": "none"},
        )
        input_id = self._id()
        input_variable = ET.SubElement(
            ld, _q(ns, "inVariable"), {"localId": str(input_id)}
        )
        self._position(input_variable)
        ET.SubElement(input_variable, _q(ns, "connectionPointOut"))
        input_expression = ET.SubElement(input_variable, _q(ns, "expression"))
        input_expression.text = oneshot.input_name

        block_id = self._id()
        block = ET.SubElement(
            ld,
            _q(ns, "block"),
            {
                "localId": str(block_id),
                "typeName": "R_TRIG",
                "instanceName": oneshot.instance_name,
            },
        )
        self._position(block)
        inputs = ET.SubElement(block, _q(ns, "inputVariables"))
        for parameter, reference in (
            ("EN", trigger_rail_id),
            ("CLK", input_id),
        ):
            variable = ET.SubElement(
                inputs, _q(ns, "variable"), {"formalParameter": parameter}
            )
            point = ET.SubElement(variable, _q(ns, "connectionPointIn"))
            self._condition_connection(point, reference)
        ET.SubElement(block, _q(ns, "inOutVariables"))
        outputs = ET.SubElement(block, _q(ns, "outputVariables"))
        enabled = ET.SubElement(outputs, _q(ns, "variable"), {"formalParameter": "ENO"})
        ET.SubElement(enabled, _q(ns, "connectionPointOut"))
        pulse = ET.SubElement(outputs, _q(ns, "variable"), {"formalParameter": "Q"})
        pulse_point = ET.SubElement(pulse, _q(ns, "connectionPointOut"))
        pulse_expression = ET.SubElement(pulse_point, _q(ns, "expression"))
        pulse_expression.text = oneshot.pulse_name
        if self.profile is PLCopenProfile.CODESYS:
            self._codesys.append_call_type(block)
        self._coil(
            ld,
            "OTE",
            oneshot.executed_name,
            [block_id],
            formal_parameter="ENO",
        )
        trigger_right = ET.SubElement(
            ld, _q(ns, "rightPowerRail"), {"localId": str(self._id())}
        )
        self._position(trigger_right)
        ET.SubElement(trigger_right, _q(ns, "connectionPointIn"))

        continuation_rail_id = self._id()
        continuation_rail = ET.SubElement(
            ld,
            _q(ns, "leftPowerRail"),
            {"localId": str(continuation_rail_id)},
        )
        self._position(continuation_rail)
        ET.SubElement(
            continuation_rail,
            _q(ns, "connectionPointOut"),
            {"formalParameter": "none"},
        )
        return self._contact(
            ld,
            "XIC",
            oneshot.pulse_name,
            [continuation_rail_id],
        )

    def _value_block(
        self,
        ld: ET.Element,
        opcode: str,
        operand_text: str,
        condition_ids: list[int],
        *,
        input_from_block: bool,
    ) -> int:
        ns = self.profile.namespace
        operands = _split_arguments(operand_text)
        sources, destination = operands[:-1], operands[-1]
        source_ids: list[int] = []
        for source in sources:
            local_id = self._id()
            variable = ET.SubElement(
                ld, _q(ns, "inVariable"), {"localId": str(local_id)}
            )
            self._position(variable)
            ET.SubElement(variable, _q(ns, "connectionPointOut"))
            expression = ET.SubElement(variable, _q(ns, "expression"))
            expression.text = self._portable_operand(source)
            source_ids.append(local_id)
        block_id = self._id()
        block = ET.SubElement(
            ld,
            _q(ns, "block"),
            {
                "localId": str(block_id),
                "typeName": _VALUE_BLOCK_TYPES[opcode],
            },
        )
        self._position(block)
        inputs = ET.SubElement(block, _q(ns, "inputVariables"))
        enable = ET.SubElement(inputs, _q(ns, "variable"), {"formalParameter": "EN"})
        enable_point = ET.SubElement(enable, _q(ns, "connectionPointIn"))
        for condition_id in condition_ids:
            self._condition_connection(
                enable_point,
                condition_id,
                formal_parameter="ENO" if input_from_block else None,
            )
        for source_id in source_ids:
            variable = ET.SubElement(
                inputs, _q(ns, "variable"), {"formalParameter": ""}
            )
            point = ET.SubElement(variable, _q(ns, "connectionPointIn"))
            self._condition_connection(point, source_id)
        ET.SubElement(block, _q(ns, "inOutVariables"))
        outputs = ET.SubElement(block, _q(ns, "outputVariables"))
        enabled = ET.SubElement(outputs, _q(ns, "variable"), {"formalParameter": "ENO"})
        ET.SubElement(enabled, _q(ns, "connectionPointOut"))
        result = ET.SubElement(outputs, _q(ns, "variable"), {"formalParameter": ""})
        result_point = ET.SubElement(result, _q(ns, "connectionPointOut"))
        expression = ET.SubElement(result_point, _q(ns, "expression"))
        expression.text = self._portable_operand(destination)
        return block_id

    def _condition_connection(
        self,
        point_in: ET.Element,
        condition_id: int,
        *,
        formal_parameter: str | None = None,
    ) -> None:
        attributes = {"refLocalId": str(condition_id)}
        if formal_parameter is not None:
            attributes["formalParameter"] = formal_parameter
        ET.SubElement(
            point_in,
            _q(self.profile.namespace, "connection"),
            attributes,
        )

    def _action_call(
        self,
        ld: ET.Element,
        action_name: str,
        *,
        comment: str | None,
        codesys: bool,
    ) -> None:
        ns = self.profile.namespace
        rail_id = self._id()
        rail = ET.SubElement(ld, _q(ns, "leftPowerRail"), {"localId": str(rail_id)})
        self._position(rail)
        ET.SubElement(rail, _q(ns, "connectionPointOut"), {"formalParameter": "none"})
        if comment:
            self._comment(ld, comment)
        block_id = self._id()
        block = ET.SubElement(
            ld,
            _q(ns, "block"),
            {"localId": str(block_id), "typeName": action_name},
        )
        self._position(block)
        inputs = ET.SubElement(block, _q(ns, "inputVariables"))
        enable = ET.SubElement(inputs, _q(ns, "variable"), {"formalParameter": "EN"})
        point_in = ET.SubElement(enable, _q(ns, "connectionPointIn"))
        ET.SubElement(point_in, _q(ns, "connection"), {"refLocalId": str(rail_id)})
        ET.SubElement(block, _q(ns, "inOutVariables"))
        outputs = ET.SubElement(block, _q(ns, "outputVariables"))
        enabled = ET.SubElement(outputs, _q(ns, "variable"), {"formalParameter": "ENO"})
        ET.SubElement(enabled, _q(ns, "connectionPointOut"))
        if codesys:
            self._codesys.append_call_type(block, "action")
        right = ET.SubElement(
            ld, _q(ns, "rightPowerRail"), {"localId": str(self._id())}
        )
        self._position(right)
        ET.SubElement(right, _q(ns, "connectionPointIn"))

    def _comment(
        self, ld: ET.Element, text: str, *, raw_rll: str | None = None
    ) -> None:
        ns = self.profile.namespace
        comment = ET.SubElement(
            ld,
            _q(ns, "comment"),
            {"localId": str(self._id()), "height": "0", "width": "0"},
        )
        self._position(comment)
        content = ET.SubElement(comment, _q(ns, "content"))
        xhtml = ET.SubElement(content, _q(XHTML_NAMESPACE, "xhtml"))
        xhtml.text = text
        if raw_rll:
            add_data = ET.SubElement(comment, _q(ns, "addData"))
            data = ET.SubElement(
                add_data,
                _q(ns, "data"),
                {"name": TWINFORGE_RLL_EXTENSION, "handleUnknown": "preserve"},
            )
            source = ET.SubElement(data, "RLL")
            source.text = raw_rll

    def _position(self, parent: ET.Element) -> None:
        ET.SubElement(
            parent, _q(self.profile.namespace, "position"), {"x": "0", "y": "0"}
        )

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
                    parsed = _parse_supported_rung(rung.text)
                    if parsed is None:
                        continue
                    comparisons = [
                        operand_text
                        for opcode, operand_text in parsed.tail_conditions
                        if opcode in _COMPARISON_TYPES
                    ]
                    if any(
                        self._comparison_uses_unsupported_type(
                            operand_text, tags_by_name
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
                                f"{rung.number if rung.number is not None else 'N'}_{index + 1}"
                            )
                            temp_name = _unique_portable_name(base, names)
                            names.add(temp_name)
                            temp_names.append(temp_name)
                            self._comparison_tags.setdefault(program.name, []).append(
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
                            _split_arguments(operand_text)
                            if opcode
                            in {
                                *_COMPARISON_TYPES,
                                *_VALUE_BLOCK_TYPES,
                            }
                            else [operand_text]
                        )
                        if opcode == "TON":
                            operands = [_split_arguments(operand_text)[0]]
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
                                portable = _unique_portable_name(operand, names)
                                names.add(portable)
                                self._generated_tags.append(
                                    Tag(
                                        name=portable,
                                        data_type="BOOL" if is_boolean else "REAL",
                                        description=(
                                            f"Portable surrogate for Rockwell operand {operand}"
                                        ),
                                        metadata={"plcopen_source_operand": operand},
                                    )
                                )
                                self._diagnostic(
                                    "raw_operand_rewritten",
                                    "raw Rockwell operand was replaced by an IEC-safe surrogate variable",
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
            preset_ms = _timer_member_integer(tag, "PRE")
            if preset_ms is None:
                self._diagnostic(
                    "timer_preset_missing",
                    "TIMER has no readable decorated PRE value; zero milliseconds was used",
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
                name = _unique_portable_name(f"{tag.name}_{suffix}", names)
                names.add(name)
                generated.append(name)
                self._generated_tags.append(
                    Tag(
                        name=name,
                        data_type=data_type,
                        description=f"TwinForge IEC timer {suffix} for {tag.name}",
                    )
                )
            self._timers[tag.name] = _TimerExport(
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
                    parsed = _parse_supported_rung(rung.text)
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
                        name = _unique_portable_name(f"{base}_{suffix}", names)
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
                                "plcopen_derived_type": (
                                    self._codesys.library_type("R_TRIG")
                                    if self.profile is PLCopenProfile.CODESYS
                                    else "R_TRIG"
                                ),
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
                    self._oneshots[id(rung)] = _OneShotExport(
                        instance_name=generated[0],
                        input_name=generated[1],
                        pulse_name=generated[2],
                        executed_name=generated[3],
                    )

    def _comparison_uses_unsupported_type(
        self, operand_text: str, tags_by_name: dict[str, Tag]
    ) -> bool:
        for operand in _split_arguments(operand_text):
            root_name = operand.split(".", 1)[0]
            tag = tags_by_name.get(root_name)
            if tag is None:
                continue
            if self._tag_export_type(tag) == "TIMER" and operand == f"{root_name}.ACC":
                continue
            if self._tag_export_type(tag) not in _PRIMITIVE_TYPES:
                return True
        return False

    def _comparison_operands(self, operands: list[str]) -> list[str]:
        if not any(operand.endswith(".ACC") for operand in operands):
            return [self._portable_operand(operand) for operand in operands]
        converted: list[str] = []
        for operand in operands:
            if operand.endswith(".ACC"):
                timer = self._timers.get(operand[:-4])
                converted.append(timer.elapsed_name if timer is not None else operand)
            elif _NUMERIC_LITERAL.fullmatch(operand):
                converted.append(_milliseconds_time_literal(int(float(operand))))
            else:
                converted.append(f"DINT_TO_TIME({self._portable_operand(operand)})")
        return converted

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

    def _portable_operand(self, operand: str) -> str:
        return self._operand_names.get(operand, operand)

    def _id(self) -> int:
        value = self._next_local_id
        self._next_local_id += 1
        return value

    def _diagnostic(
        self,
        code: str,
        message: str,
        object_name: str | None,
        *,
        raw_value: str | None = None,
    ) -> None:
        self.diagnostics.append(
            ConversionDiagnostic(
                severity=DiagnosticSeverity.WARNING,
                code=code,
                message=message,
                object_name=object_name,
                raw_value=raw_value,
            )
        )
