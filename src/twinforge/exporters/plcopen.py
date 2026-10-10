from __future__ import annotations

from collections.abc import Sequence
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from twinforge.converters import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import (
    Controller, Expression, LadderOperation, LadderParallel, LadderRung, LadderSeries, Program, Tag, Task,
)
from twinforge.model.expression import ASSIGNMENT_OPERATOR

from .plcopen_codesys import CodesysProfileSupport
from .plcopen_instructions import (
    ConditionInstruction,
    OutputInstruction,
    PLCopenInstructionRegistry,
    build_instruction_registry,
)
from .plcopen_rll import (
    COMPARISON_TYPES as _COMPARISON_TYPES,
    SUPPORTED_RLL_INSTRUCTIONS as PLCOPEN_SUPPORTED_RLL_INSTRUCTIONS,
    VALUE_BLOCK_TYPES as _VALUE_BLOCK_TYPES,
    parse_jsr as _parse_jsr,
    parse_supported_rung as _parse_supported_rung,
    split_arguments as _split_arguments,
)
from .plcopen_operands import (
    PLCopenOneShotExport,
    PLCopenOperandPlan,
    PLCopenOperandPlanner,
)
from .plcopen_library import emit_function_block_pou
from .plcopen_network import ENCODINGS as NETWORK_ENCODINGS
from .plcopen_network import FUNCTION_BLOCK_TYPES as NETWORK_FUNCTIONS
from .plcopen_network import describe as describe_network
from .plcopen_network import unsupported_reason as network_unsupported_reason
from .plcopen_project import PLCopenProjectOrchestrator
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
from .plcopen_variables import PLCopenVariableEmitter
from .plcopen_xml import (
    milliseconds_duration as _milliseconds_duration,
    milliseconds_time_literal as _milliseconds_time_literal,
    qualified_name as _q,
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
# A connection source: an element's localId, or (block localId, output pin).
ConnectionRef = int | tuple[int, str]

_NOP_INSTRUCTION = re.compile(r"\s*NOP\s*\(\s*\)\s*;\s*")


class PLCopenExporter:
    def __init__(
        self, profile: PLCopenProfile | str = PLCopenProfile.STANDARD_201, *, include_unverified_blocks: bool = False,
    ):
        self.profile = PLCopenProfile(profile)
        # Also export TwinForge-generated blocks whose behaviour is not yet
        # verified against the vendor (plcopen_library); off by default.
        self._include_unverified_blocks = include_unverified_blocks
        self.diagnostics: list[ConversionDiagnostic] = []
        self._next_local_id = 1
        self._codesys = CodesysProfileSupport(PLCOPEN_CODESYS_NAMESPACE)
        self._operands = PLCopenOperandPlan.empty()
        # Per network rung: timer instance -> (block localId, input points).
        self._network_blocks: dict[str, tuple[int, dict[str, ET.Element]]] = {}

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
        trigger_type = (
            self._codesys.library_type("R_TRIG")
            if self.profile is PLCopenProfile.CODESYS
            else "R_TRIG"
        )
        self._operands = PLCopenOperandPlanner(
            rising_trigger_type=trigger_type,
            include_unverified_blocks=self._include_unverified_blocks,
        ).prepare(controller)
        self.diagnostics.extend(self._operands.diagnostics)
        target_application = (
            self._codesys_application
            if self.profile is PLCopenProfile.CODESYS
            else None
        )
        return PLCopenProjectOrchestrator(
            namespace=self.profile.namespace,
            emit_program=lambda parent, program: self._program(
                parent,
                program,
            ),
            emit_task=lambda parent, task: self._task(parent, task),
            emit_global_variables=lambda parent, tags: self._variables(
                parent,
                "globalVars",
                tags,
            ),
            emit_target_application=target_application,
            emit_function_blocks=self._emit_generated_blocks,
        ).build(
            controller,
            self._operands.generated_tags,
            project_name=project_name or controller.name or "TwinForge",
            creation_time=creation_time or datetime.now(timezone.utc),
        )

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

    def _codesys_application(
        self,
        root: ET.Element,
        controller: Controller,
        generated_tags: Sequence[Tag],
    ) -> None:
        """Delegate CODESYS project wrapping to the target adapter."""

        self._codesys.emit_application(
            root,
            controller,
            generated_tags,
            needs_standard_library=bool(
                self._operands.timers or self._operands.oneshots
                or any(block.standard for block in self._operands.function_block_instances.values())
            ),
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
            function_blocks=self._operands.generated_blocks,
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
                *self._operands.comparison_tags.get(program.name, ()),
                *self._operands.oneshot_tags.get(program.name, ()),
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
                self._codesys.object_id(f"Application/program/{program.name}"),
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
        ns = self.profile.namespace
        timer_type = (
            self._codesys.library_type("TON")
            if self.profile is PLCopenProfile.CODESYS
            else "TON"
        )
        instances = self._operands.function_block_instances
        codesys = self.profile is PLCopenProfile.CODESYS

        def function_block_type(tag: Tag) -> str | None:
            if tag.name not in instances:
                return None
            block = instances[tag.name]
            return self._codesys.library_type(block.type_name) if codesys and block.standard else block.type_name

        return PLCopenVariableEmitter(
            namespace=ns,
            tag_export_type=self._tag_export_type,
            timer_type=timer_type,
            report_diagnostic=self._diagnostic,
            function_block_type=function_block_type,
            declared_name=lambda tag: self._operands.tag_names.get(tag.name, tag.name),
        ).emit(parent, list_name, tags, attributes=attributes)

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
        # A structured network with no Logix RLL text (Control Expert,
        # Machine Expert - Basic): emit it directly as an LD connection graph.
        if rung.text is None and rung.network is not None:
            self._network_rung(ld, rung, program_name)
            return
        # Instruction List that could not become a ladder network: keep the IL
        # itself, readable, in the comment.
        if rung.text is None and rung.network is None and rung.instruction_list:
            il_text = "; ".join(line.strip() for line in rung.instruction_list if line.strip())
            self._diagnostic(
                "instruction_list_rung_not_converted",
                "Instruction List rung has no ladder-expressible network; its IL is kept as a comment",
                program_name,
                raw_value=il_text,
            )
            self._comment(ld, f"Instruction List: {il_text}")
            return
        # Neither form.
        if rung.text is None and rung.network is None:
            self._diagnostic(
                "rung_without_exportable_logic",
                "rung has neither Logix RLL text nor a ladder network; kept as a comment",
                program_name,
            )
            self._comment(ld, rung.comment or "Rung with no exportable logic")
            return
        if rung.text and _NOP_INSTRUCTION.fullmatch(rung.text):
            self._comment(
                ld,
                rung.comment or "Rockwell NOP (intentional no operation)",
                raw_rll=rung.text,
            )
            return
        if id(rung) in self._operands.unsupported_comparison_rungs:
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
        if any(operand not in self._operands.timers for operand in timer_operands):
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
        registry = self._instruction_registry()
        condition_ids = [condition_id]
        for opcode, operand in parsed.prefix_conditions:
            condition_ids = [
                registry.emit_condition(
                    ConditionInstruction(
                        ld=ld,
                        opcode=opcode,
                        operand=operand,
                        condition_ids=tuple(condition_ids),
                    )
                )
            ]
        if parsed.branches:
            branch_start_ids = tuple(condition_ids)
            condition_ids = []
            for branch in parsed.branches:
                branch_condition = branch_start_ids[0]
                for opcode, operand in branch:
                    branch_condition = registry.emit_condition(
                        ConditionInstruction(
                            ld=ld,
                            opcode=opcode,
                            operand=operand,
                            condition_ids=(branch_condition,),
                        )
                    )
                condition_ids.append(branch_condition)
        comparison_index = 0
        for opcode, operand in parsed.tail_conditions:
            auxiliary: object | None = None
            if opcode == "ONS":
                auxiliary = self._operands.oneshots[id(rung)]
            elif opcode in _COMPARISON_TYPES:
                temp_name = self._operands.comparison_temps[id(rung)][comparison_index]
                comparison_index += 1
                auxiliary = temp_name
            condition_ids = [
                registry.emit_condition(
                    ConditionInstruction(
                        ld=ld,
                        opcode=opcode,
                        operand=operand,
                        condition_ids=tuple(condition_ids),
                        auxiliary=auxiliary,
                    )
                )
            ]
        execution_ids = condition_ids
        execution_from_block = False
        for opcode, operand in parsed.outputs:
            emission = registry.emit_output(
                OutputInstruction(
                    ld=ld,
                    opcode=opcode,
                    operand=operand,
                    execution_ids=tuple(execution_ids),
                    input_from_block=execution_from_block,
                )
            )
            execution_ids = list(emission.execution_ids)
            execution_from_block = emission.execution_from_block

        right_id = self._id()
        right = ET.SubElement(ld, _q(ns, "rightPowerRail"), {"localId": str(right_id)})
        self._position(right)
        ET.SubElement(right, _q(ns, "connectionPointIn"))

    def _emit_generated_blocks(self, pous: ET.Element) -> None:
        """TwinForge-generated function block definitions the project uses."""
        for block in self._operands.generated_blocks:
            emit_function_block_pou(pous, block, self.profile.namespace)

    def _network_rung(self, ld: ET.Element, rung: LadderRung, program_name: str) -> None:
        assert rung.network is not None
        reason = network_unsupported_reason(rung.network, self._operands.function_block_instances)
        if reason is not None:
            text = describe_network(rung.network)
            self._diagnostic(
                "unsupported_network_rung",
                f"rung was emitted as a non-executable comment: {reason}",
                program_name,
                raw_value=text,
            )
            self._comment(ld, f"Unsupported ladder network: {text}")
            return
        ns = self.profile.namespace
        rail_id = self._id()
        rail = ET.SubElement(ld, _q(ns, "leftPowerRail"), {"localId": str(rail_id)})
        self._position(rail)
        ET.SubElement(rail, _q(ns, "connectionPointOut"), {"formalParameter": "none"})
        if rung.comment:
            self._comment(ld, rung.comment)
        # One TC6 block per function block instance per rung, shared by its
        # input pins and every reader of its outputs.
        self._network_blocks = {}
        self._emit_series(ld, rung.network, [rail_id])
        right = ET.SubElement(ld, _q(ns, "rightPowerRail"), {"localId": str(self._id())})
        self._position(right)
        ET.SubElement(right, _q(ns, "connectionPointIn"))

    def _emit_series(
        self, ld: ET.Element, series: LadderSeries, inputs: list[ConnectionRef],
    ) -> list[ConnectionRef]:
        """Emit one series left to right; return the sources its end is wired from.

        A parallel section's output is every branch's output together (a
        wired OR); an empty branch is a bare wire, so it passes its input on.
        A function block input pin ends its branch; a block output reference
        starts one from that block's output pin.
        """
        current: list[ConnectionRef] = list(inputs)
        for element in series.elements:
            if isinstance(element, LadderParallel):
                joined: list[ConnectionRef] = []
                for branch in element.branches:
                    for source in self._emit_series(ld, branch, current):
                        if source not in joined:
                            joined.append(source)
                current = joined
                continue
            if element.expression is not None:  # COMPARISON / ASSIGNMENT
                current = self._emit_expression(ld, element.expression, current)
                continue
            if element.operation is LadderOperation.FUNCTION_BLOCK_INPUT:
                instance, _, pin = (element.operand or "").rpartition(".")
                _, pins = self._network_block(ld, instance)
                for source in current:
                    self._condition_connection(pins[pin], source)
                current = []
                continue
            if element.operation is LadderOperation.BLOCK_OUTPUT_REFERENCE:
                instance, _, pin = (element.operand or "").rpartition(".")
                block_id, _ = self._network_block(ld, instance)
                current = [(block_id, pin)]
                continue
            encoding = NETWORK_ENCODINGS[element.operation]
            operand = element.operand or ""
            if encoding.element == "contact":
                current = [self._contact(ld, "XIO" if encoding.negated else "XIC", operand, current,
                                         edge=encoding.edge)]
            else:
                opcode = {"set": "OTL", "reset": "OTU"}.get(encoding.storage or "", "OTE")
                current = [self._coil(ld, opcode, operand, current, negated=encoding.negated)]
        return current

    def _emit_expression(
        self, ld: ET.Element, expression: Expression, chain: list[ConnectionRef],
    ) -> list[ConnectionRef]:
        """Emit a COMPARISON or ASSIGNMENT as single IEC functions chained by EN/ENO.

        Each nested arithmetic node is one function writing its typed
        temporary; an assignment's top-level arithmetic (or MOVE) writes the
        target itself. A comparison writes its BOOL temporary and the rung
        continues through a contact on it, wired from the comparison's ENO so
        the function runs before the contact reads its result. Power reaching
        the expression is its EN, so nothing executes unless the rung allows.
        """
        left, right = expression.left, expression.right
        assert left is not None and right is not None
        if expression.operator == ASSIGNMENT_OPERATOR:
            target = self._portable_operand(left.text)
            if right.kind == "binary":
                assert right.left is not None and right.right is not None and right.operator is not None
                first, chain = self._expression_value(ld, right.left, chain)
                second, chain = self._expression_value(ld, right.right, chain)
                return [self._function_call(ld, NETWORK_FUNCTIONS[right.operator], [first, second], target, chain)]
            return [self._function_call(ld, "MOVE", [self._expression_leaf(right)], target, chain)]
        first, chain = self._expression_value(ld, left, chain)
        second, chain = self._expression_value(ld, right, chain)
        assert expression.operator is not None
        result = self._operands.expression_temps[id(expression)]
        enabled = self._function_call(ld, NETWORK_FUNCTIONS[expression.operator], [first, second], result, chain)
        return [self._contact(ld, "XIC", result, [enabled])]

    def _expression_value(
        self, ld: ET.Element, node: Expression, chain: list[ConnectionRef],
    ) -> tuple[str, list[ConnectionRef]]:
        """The text an input reads for `node`, emitting its functions first if needed."""
        if node.kind != "binary":
            return self._expression_leaf(node), chain
        assert node.left is not None and node.right is not None and node.operator is not None
        first, chain = self._expression_value(ld, node.left, chain)
        second, chain = self._expression_value(ld, node.right, chain)
        result = self._operands.expression_temps[id(node)]
        return result, [self._function_call(ld, NETWORK_FUNCTIONS[node.operator], [first, second], result, chain)]

    def _expression_leaf(self, node: Expression) -> str:
        return node.text if node.kind == "literal" else self._portable_operand(node.text)

    def _function_call(
        self, ld: ET.Element, type_name: str, inputs: list[str], destination: str, chain: list[ConnectionRef],
    ) -> ConnectionRef:
        """One IEC standard function: EN from `chain`, inputs from inVariables,
        result written to `destination`. Returns its ENO."""
        ns = self.profile.namespace
        input_ids: list[int] = []
        for text in inputs:
            local_id = self._id()
            variable = ET.SubElement(ld, _q(ns, "inVariable"), {"localId": str(local_id)})
            self._position(variable)
            ET.SubElement(variable, _q(ns, "connectionPointOut"))
            ET.SubElement(variable, _q(ns, "expression")).text = text
            input_ids.append(local_id)
        block_id = self._id()
        block = ET.SubElement(ld, _q(ns, "block"), {"localId": str(block_id), "typeName": type_name})
        self._position(block)
        block_inputs = ET.SubElement(block, _q(ns, "inputVariables"))
        enable = ET.SubElement(block_inputs, _q(ns, "variable"), {"formalParameter": "EN"})
        enable_point = ET.SubElement(enable, _q(ns, "connectionPointIn"))
        for source in chain:
            self._condition_connection(enable_point, source)
        for input_id in input_ids:
            variable = ET.SubElement(block_inputs, _q(ns, "variable"), {"formalParameter": ""})
            self._condition_connection(ET.SubElement(variable, _q(ns, "connectionPointIn")), input_id)
        ET.SubElement(block, _q(ns, "inOutVariables"))
        outputs = ET.SubElement(block, _q(ns, "outputVariables"))
        enabled = ET.SubElement(outputs, _q(ns, "variable"), {"formalParameter": "ENO"})
        ET.SubElement(enabled, _q(ns, "connectionPointOut"))
        result = ET.SubElement(outputs, _q(ns, "variable"), {"formalParameter": ""})
        result_point = ET.SubElement(result, _q(ns, "connectionPointOut"))
        ET.SubElement(result_point, _q(ns, "expression")).text = destination
        return (block_id, "ENO")

    def _network_block(self, ld: ET.Element, instance: str) -> tuple[int, dict[str, ET.Element]]:
        """The rung's TC6 block for a function block instance, created on first use.

        Its wired inputs are connected by the instance's input-pin sinks; its
        constant inputs (a timer's PT, a counter's PV) come from inVariables;
        output references read its outputs. Returns the block localId and its
        input connection points.
        """
        if instance in self._network_blocks:
            return self._network_blocks[instance]
        ns = self.profile.namespace
        interface = self._operands.function_block_instances[instance]
        constant_ids: dict[str, int] = {}
        for pin, literal in interface.constants:
            constant_ids[pin] = self._id()
            constant = ET.SubElement(ld, _q(ns, "inVariable"), {"localId": str(constant_ids[pin])})
            self._position(constant)
            ET.SubElement(constant, _q(ns, "connectionPointOut"))
            ET.SubElement(constant, _q(ns, "expression")).text = literal
        block_id = self._id()
        block = ET.SubElement(ld, _q(ns, "block"), {
            "localId": str(block_id), "typeName": interface.type_name,
            "instanceName": self._operands.tag_names.get(instance, instance),
        })
        self._position(block)
        inputs = ET.SubElement(block, _q(ns, "inputVariables"))
        pins: dict[str, ET.Element] = {}
        for parameter in interface.inputs:
            variable = ET.SubElement(inputs, _q(ns, "variable"), {"formalParameter": parameter})
            pins[parameter] = ET.SubElement(variable, _q(ns, "connectionPointIn"))
            if parameter in constant_ids:
                self._condition_connection(pins[parameter], constant_ids[parameter])
        ET.SubElement(block, _q(ns, "inOutVariables"))
        outputs = ET.SubElement(block, _q(ns, "outputVariables"))
        for parameter in interface.outputs:
            variable = ET.SubElement(outputs, _q(ns, "variable"), {"formalParameter": parameter})
            ET.SubElement(variable, _q(ns, "connectionPointOut"))
        if self.profile is PLCopenProfile.CODESYS:
            self._codesys.append_call_type(block)
        self._network_blocks[instance] = (block_id, pins)
        return self._network_blocks[instance]

    def _instruction_registry(self) -> PLCopenInstructionRegistry:
        """Bind supported opcodes to their focused emission strategies."""

        return build_instruction_registry(
            comparison_opcodes=frozenset(_COMPARISON_TYPES),
            value_opcodes=frozenset(_VALUE_BLOCK_TYPES),
            emit_contact=self._contact,
            emit_comparison=self._comparison,
            emit_oneshot=self._oneshot_block,
            emit_coil=self._coil,
            emit_timer=self._timer_block,
            emit_timer_reset=self._timer_reset_block,
            emit_value=self._value_block,
        )

    def _contact(
        self,
        ld: ET.Element,
        opcode: str,
        operand: str,
        condition_ids: Sequence[ConnectionRef],
        *,
        edge: str | None = None,
    ) -> int:
        ns = self.profile.namespace
        local_id = self._id()
        attributes = {"localId": str(local_id)}
        if opcode == "XIO":
            attributes["negated"] = "true"
        if edge is not None:
            attributes["edge"] = edge
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
        condition_ids: Sequence[ConnectionRef],
        *,
        formal_parameter: str | None = None,
        negated: bool = False,
    ) -> int:
        ns = self.profile.namespace
        local_id = self._id()
        attributes = {"localId": str(local_id)}
        if negated:
            attributes["negated"] = "true"
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
        timer = self._operands.timers[timer_name]
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
        timer = self._operands.timers[timer_name]
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
        oneshot: PLCopenOneShotExport,
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
        condition_id: ConnectionRef,
        *,
        formal_parameter: str | None = None,
    ) -> None:
        if isinstance(condition_id, tuple):  # a block's named output pin
            condition_id, formal_parameter = condition_id
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

    def _comparison_operands(self, operands: list[str]) -> list[str]:
        return self._operands.comparison_operands(operands)

    def _tag_export_type(self, tag: Tag) -> str:
        return self._operands.tag_export_type(tag)

    def _portable_operand(self, operand: str) -> str:
        return self._operands.portable_operand(operand)

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
