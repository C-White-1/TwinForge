"""CODESYS PLCopen XML export for vendor-neutral executable IR."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

from twinforge.ir import (
    IRDirection,
    IRReusableUnit,
    IRRoutineRole,
)
from twinforge.structured_text import SourceSpan

from .codesys_st import (
    adapt_codesys_runtime,
    emit_codesys_st_routine,
    emit_codesys_st_unit,
)
from .codesys_ir_integration import (
    CodesysArgumentBinding as CodesysArgumentBinding,
    CodesysProgramCall,
    CodesysProgramVariable,
    CodesysProjectIntegration,
    codesys_parameter_initial_value as codesys_parameter_initial_value,
    codesys_program_variable_name as codesys_program_variable_name,
)
from .codesys_ir_lifecycle import CodesysIRLifecycleEmitter
from .codesys_ir_pou import (
    CodesysIRInterfaceEmitter,
    CodesysIRPOUEmitter,
)
from .iec_st import IECRequirement, IECSTDiagnostic
from .plcopen_codesys import CODESYS_NAMESPACE, CodesysProfileSupport
from .plcopen_types import PLCOPEN_CODESYS_NAMESPACE
from .plcopen_xml import qualified_name as q


XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
@dataclass(frozen=True)
class CodesysPLCopenIRResult:
    """Serialized CODESYS PLCopen document and executable diagnostics."""

    xml: str
    diagnostics: tuple[IECSTDiagnostic, ...]
    requirements: tuple[IECRequirement, ...]

    @property
    def complete(self) -> bool:
        """Return whether the target document has no blocking IR issue."""

        blocking = {
            "unsupported_expression",
            "unsupported_statement",
            "write_to_input_parameter",
            "unknown_data_type",
            "multiple_routines_require_lifecycle_mapping",
            "prescan_mapping_required",
            "postscan_mapping_required",
            "enable_in_false_mapping_required",
            "aoi_enable_interface_unavailable",
            "unknown_scan_mode_routine",
        }
        return not self.requirements and not any(
            item.code in blocking for item in self.diagnostics
        )


class CodesysIRPLCopenExporter:
    """Build importable CODESYS PLCopen POUs from executable IR."""

    def __init__(self) -> None:
        self._profile = CodesysProfileSupport(PLCOPEN_CODESYS_NAMESPACE)
        self._interface = CodesysIRInterfaceEmitter()
        self._lifecycle = CodesysIRLifecycleEmitter(
            object_id=self._profile.object_id
        )

    def export(
        self,
        unit: IRReusableUnit,
        *,
        additional_units: tuple[IRReusableUnit, ...] = (),
        destination: str | Path | None = None,
        project_name: str = "TwinForgeIR",
        creation_time: datetime | None = None,
        integration: CodesysProjectIntegration | None = None,
    ) -> CodesysPLCopenIRResult:
        """Serialize reusable units and an optional scheduled program call."""

        self._profile.reset()
        unit = adapt_codesys_runtime(unit)
        additional_units = tuple(
            adapt_codesys_runtime(item) for item in additional_units
        )
        emission = emit_codesys_st_unit(unit)
        additional_emissions = tuple(
            emit_codesys_st_unit(item) for item in additional_units
        )
        prescan = self._lifecycle.mapped_prescan(unit)
        prescan_emission = (
            emit_codesys_st_routine(prescan)
            if prescan is not None
            else None
        )
        root = self._build(
            unit,
            additional_units=additional_units,
            project_name=project_name,
            creation_time=creation_time,
            integration=integration,
        )
        ET.indent(root, space="  ")
        xml = ET.tostring(root, encoding="unicode", xml_declaration=True)
        if destination is not None:
            Path(destination).write_text(xml, encoding="utf-8")
        diagnostics = list(emission.diagnostics)
        requirements = set(emission.requirements)
        for additional_emission in additional_emissions:
            diagnostics.extend(additional_emission.diagnostics)
            requirements.update(additional_emission.requirements)
        if prescan_emission is not None:
            diagnostics = [
                item
                for item in diagnostics
                if item.code != "prescan_mapping_required"
            ]
            diagnostics.append(
                IECSTDiagnostic(
                    "codesys_prescan_mapped_to_fb_init",
                    "mapped enabled AOI Prescan logic to the CODESYS "
                    "FB_Init lifecycle method",
                    SourceSpan(0, 0),
                )
            )
            requirements.update(prescan_emission.requirements)
        return CodesysPLCopenIRResult(
            xml=xml,
            diagnostics=tuple(diagnostics),
            requirements=tuple(
                sorted(requirements, key=lambda item: item.value)
            ),
        )

    def _build(
        self,
        unit: IRReusableUnit,
        *,
        additional_units: tuple[IRReusableUnit, ...],
        project_name: str,
        creation_time: datetime | None,
        integration: CodesysProjectIntegration | None,
    ) -> ET.Element:
        ns = PLCOPEN_CODESYS_NAMESPACE
        ET.register_namespace("", ns)
        timestamp = (creation_time or datetime.now(timezone.utc)).isoformat()
        root = ET.Element(q(ns, "project"))
        ET.SubElement(
            root,
            q(ns, "fileHeader"),
            {
                "companyName": "TwinForge",
                "productName": "TwinForge",
                "productVersion": "0.1.0",
                "creationDateTime": timestamp,
            },
        )
        header = ET.SubElement(
            root,
            q(ns, "contentHeader"),
            {"name": project_name},
        )
        coordinate = ET.SubElement(header, q(ns, "coordinateInfo"))
        for language in ("fbd", "ld", "sfc"):
            element = ET.SubElement(coordinate, q(ns, language))
            ET.SubElement(
                element,
                q(ns, "scaling"),
                {"x": "1", "y": "1"},
            )

        types = ET.SubElement(root, q(ns, "types"))
        ET.SubElement(types, q(ns, "dataTypes"))
        ET.SubElement(types, q(ns, "pous"))
        instances = ET.SubElement(root, q(ns, "instances"))
        ET.SubElement(instances, q(ns, "configurations"))

        add_data = ET.SubElement(root, q(ns, "addData"))
        application = ET.SubElement(
            add_data,
            q(ns, "data"),
            {
                "name": f"{CODESYS_NAMESPACE}/application",
                "handleUnknown": "implementation",
            },
        )
        resource = ET.SubElement(
            application,
            q(ns, "resource"),
            {"name": "Application"},
        )
        if integration is not None:
            self._task(resource, integration)
        resource_add_data = ET.SubElement(resource, q(ns, "addData"))
        if integration is not None:
            wrapper = self._pou_wrapper(resource_add_data)
            self._program(
                wrapper,
                (unit, *additional_units),
                integration,
            )
        units = (unit, *additional_units)
        for reusable_unit in units:
            wrapper = ET.SubElement(
                resource_add_data,
                q(ns, "data"),
                self._pou_wrapper_attributes(),
            )
            self._pou(wrapper, reusable_unit)
        if any(self._needs_wall_clock_library(item) for item in units):
            self._wall_clock_libraries(resource_add_data)
        application_id = self._profile.object_id("Application")
        self._profile.append_object_id_data(
            resource_add_data,
            application_id,
        )
        self._project_structure(
            add_data,
            units,
            application_id,
            integration,
        )
        return root

    @staticmethod
    def _pou_wrapper_attributes() -> dict[str, str]:
        return {
            "name": f"{CODESYS_NAMESPACE}/pou",
            "handleUnknown": "implementation",
        }

    def _pou_wrapper(self, parent: ET.Element) -> ET.Element:
        return ET.SubElement(
            parent,
            q(PLCOPEN_CODESYS_NAMESPACE, "data"),
            self._pou_wrapper_attributes(),
        )

    def _task(
        self,
        resource: ET.Element,
        integration: CodesysProjectIntegration,
    ) -> None:
        ns = PLCOPEN_CODESYS_NAMESPACE
        task = ET.SubElement(
            resource,
            q(ns, "task"),
            {
                "name": integration.task_name,
                "interval": f"PT{integration.interval_ms / 1000:g}S",
                "priority": str(integration.priority),
            },
        )
        instance = ET.SubElement(
            task,
            q(ns, "pouInstance"),
            {"name": integration.program_name, "typeName": ""},
        )
        documentation = ET.SubElement(
            instance,
            q(ns, "documentation"),
        )
        ET.SubElement(documentation, q(XHTML_NAMESPACE, "xhtml"))
        add_data = ET.SubElement(task, q(ns, "addData"))
        data = ET.SubElement(
            add_data,
            q(ns, "data"),
            {
                "name": f"{CODESYS_NAMESPACE}/tasksettings",
                "handleUnknown": "implementation",
            },
        )
        settings = ET.SubElement(
            data,
            q(ns, "TaskSettings"),
            {
                "KindOfTask": "Cyclic",
                "Interval": f"t#{integration.interval_ms}ms",
                "IntervalUnit": "ms",
                "WithinSPSTimeSlicing": "true",
            },
        )
        ET.SubElement(
            settings,
            q(ns, "Watchdog"),
            {
                "Enabled": "false",
                "TimeUnit": "ms",
                "Sensitivity": "1",
            },
        )
        self._profile.append_object_id_data(
            add_data,
            self._profile.object_id(
                f"Application/task/{integration.task_name}"
            ),
        )

    def _program(
        self,
        parent: ET.Element,
        units: tuple[IRReusableUnit, ...],
        integration: CodesysProjectIntegration,
    ) -> None:
        ns = PLCOPEN_CODESYS_NAMESPACE
        pou = ET.SubElement(
            parent,
            q(ns, "pou"),
            {"name": integration.program_name, "pouType": "program"},
        )
        interface = ET.SubElement(pou, q(ns, "interface"))
        local_variables = ET.SubElement(
            interface,
            q(ns, "localVars"),
        )
        units_by_name = {item.name: item for item in units}
        calls = self._program_calls(units[0], integration)
        declared_names: set[str] = set()
        for call in calls:
            call_unit = units_by_name.get(call.unit_name)
            if call_unit is None:
                raise ValueError(
                    f"program call references unknown unit {call.unit_name!r}"
                )
            self._declare_program_variable(
                local_variables,
                CodesysProgramVariable(
                    call.instance_name,
                    call.unit_name,
                ),
                declared_names,
            )
            parameters = {item.name: item for item in call_unit.parameters}
            for binding in call.bindings:
                parameter = parameters.get(binding.parameter_name)
                if parameter is None:
                    raise ValueError(
                        f"{call.unit_name!r} has no parameter "
                        f"{binding.parameter_name!r}"
                    )
                self._declare_program_variable(
                    local_variables,
                    CodesysProgramVariable(
                        binding.variable_name,
                        parameter.data_type or "BOOL",
                        binding.dimensions,
                        binding.initial_value,
                    ),
                    declared_names,
                )
        for declaration in integration.program_variables:
            self._declare_program_variable(
                local_variables,
                declaration,
                declared_names,
            )

        body = ET.SubElement(pou, q(ns, "body"))
        st = ET.SubElement(body, q(ns, "ST"))
        text = ET.SubElement(st, q(XHTML_NAMESPACE, "xhtml"))
        statements = list(integration.statements_before_call)
        for call in calls:
            statements.extend(call.statements_before_call)
            statements.append(
                self._program_call(units_by_name[call.unit_name], call)
            )
            statements.extend(call.statements_after_call)
        statements.extend(integration.statements_after_call)
        text.text = "\n\n".join(
            statement.strip() for statement in statements if statement.strip()
        )
        self._profile.append_object_id(
            pou,
            self._profile.object_id(
                f"Application/program/{integration.program_name}"
            ),
        )

    def _declare_program_variable(
        self,
        parent: ET.Element,
        declaration: CodesysProgramVariable,
        declared_names: set[str],
    ) -> None:
        """Append one unique program-local declaration."""

        if declaration.name in declared_names:
            raise ValueError(
                f"duplicate program variable {declaration.name!r}"
            )
        declared_names.add(declaration.name)
        ns = PLCOPEN_CODESYS_NAMESPACE
        variable = ET.SubElement(
            parent,
            q(ns, "variable"),
            {"name": declaration.name},
        )
        type_element = ET.SubElement(variable, q(ns, "type"))
        self._interface.data_type(
            type_element,
            declaration.data_type,
            declaration.dimensions,
        )
        if declaration.initial_value is not None:
            initial = ET.SubElement(variable, q(ns, "initialValue"))
            ET.SubElement(
                initial,
                q(ns, "simpleValue"),
                {"value": declaration.initial_value},
            )

    @staticmethod
    def _program_calls(
        unit: IRReusableUnit,
        integration: CodesysProjectIntegration,
    ) -> tuple[CodesysProgramCall, ...]:
        """Return explicit calls or the backwards-compatible primary call."""

        if integration.calls:
            return integration.calls
        return (
            CodesysProgramCall(
                unit.name,
                integration.instance_name,
                integration.bindings,
            ),
        )

    @staticmethod
    def _program_call(
        unit: IRReusableUnit,
        call: CodesysProgramCall,
    ) -> str:
        parameters = {item.name: item for item in unit.parameters}
        arguments = []
        for binding in call.bindings:
            operator = (
                "=>"
                if parameters[binding.parameter_name].direction
                is IRDirection.OUTPUT
                else ":="
            )
            arguments.append(
                f"    {binding.parameter_name} {operator} "
                f"{binding.variable_name}"
            )
        joined = ",\n".join(arguments)
        return f"{call.instance_name}(\n{joined}\n);"

    def _pou(self, parent: ET.Element, unit: IRReusableUnit) -> None:
        CodesysIRPOUEmitter(
            interface_emitter=self._interface,
            body_text=self._body_text,
            emit_lifecycle=self._lifecycle.emit,
            object_id=self._profile.object_id,
            append_object_id=self._profile.append_object_id_data,
        ).emit(parent, unit)

    @staticmethod
    def _body_text(unit: IRReusableUnit) -> str:
        routines = tuple(
            routine
            for routine in unit.routines
            if routine.role
            not in {
                IRRoutineRole.PRESCAN,
                IRRoutineRole.POSTSCAN,
                IRRoutineRole.ENABLE_IN_FALSE,
                IRRoutineRole.UNKNOWN_LIFECYCLE,
            }
        )
        if not routines:
            return ""
        bodies = []
        for routine in routines:
            emission = emit_codesys_st_routine(routine)
            if len(routines) > 1:
                bodies.append(f"(* Routine: {routine.name} *)\n")
            bodies.append(emission.text)
        return "\n".join(item.rstrip() for item in bodies)

    def _project_structure(
        self,
        add_data: ET.Element,
        units: tuple[IRReusableUnit, ...],
        application_id: str,
        integration: CodesysProjectIntegration | None,
    ) -> None:
        ns = PLCOPEN_CODESYS_NAMESPACE
        data = ET.SubElement(
            add_data,
            q(ns, "data"),
            {
                "name": f"{CODESYS_NAMESPACE}/projectstructure",
                "handleUnknown": "discard",
            },
        )
        structure = ET.SubElement(data, q(ns, "ProjectStructure"))
        application = ET.SubElement(
            structure,
            q(ns, "Object"),
            {"Name": "Application", "ObjectId": application_id},
        )
        if any(self._needs_wall_clock_library(item) for item in units):
            ET.SubElement(
                application,
                q(ns, "Object"),
                {
                    "Name": "Library Manager",
                    "ObjectId": self._profile.object_id(
                        "Application/Library Manager"
                    ),
                },
            )
        if integration is not None:
            ET.SubElement(
                application,
                q(ns, "Object"),
                {
                    "Name": integration.program_name,
                    "ObjectId": self._profile.object_id(
                        f"Application/program/{integration.program_name}"
                    ),
                },
            )
            ET.SubElement(
                application,
                q(ns, "Object"),
                {
                    "Name": integration.task_name,
                    "ObjectId": self._profile.object_id(
                        f"Application/task/{integration.task_name}"
                    ),
                },
            )
        for unit in units:
            unit_object = ET.SubElement(
                application,
                q(ns, "Object"),
                {
                    "Name": unit.name,
                    "ObjectId": self._profile.object_id(
                        f"Application/pou/{unit.name}"
                    ),
                },
            )
            if self._lifecycle.has_mapped_prescan(unit):
                ET.SubElement(
                    unit_object,
                    q(ns, "Object"),
                    {
                        "Name": "FB_Init",
                        "ObjectId": self._lifecycle.method_object_id(unit),
                    },
                )

    @staticmethod
    def _needs_wall_clock_library(unit: IRReusableUnit) -> bool:
        return any(
            item.data_type in {"SysTime", "SysTypes.RTS_IEC_RESULT"}
            for item in unit.variables
        )

    def _wall_clock_libraries(self, parent: ET.Element) -> None:
        """Emit the libraries proven by native CODESYS RTC exports."""

        ns = PLCOPEN_CODESYS_NAMESPACE
        data = ET.SubElement(
            parent,
            q(ns, "data"),
            {
                "name": f"{CODESYS_NAMESPACE}/libraries",
                "handleUnknown": "implementation",
            },
        )
        libraries = ET.SubElement(data, q(ns, "Libraries"))
        definitions = (
            {
                "Name": "#SysTimeRtc",
                "Namespace": "SysTimeRtc",
                "DefaultResolution": "SysTimeRtc, * (System)",
            },
            {
                "Name": "SysTime, 3.5.17.0 (System)",
                "Namespace": "SysTime",
            },
            {
                "Name": "SysTypes2 Interfaces, * (System)",
                "Namespace": "SysTypes",
            },
        )
        defaults = {
            "HideWhenReferencedAsDependency": "false",
            "PublishSymbolsInContainer": "false",
            "SystemLibrary": "false",
            "LinkAllContent": "false",
        }
        for definition in definitions:
            ET.SubElement(
                libraries,
                q(ns, "Library"),
                {**definition, **defaults},
            )
        self._profile.append_object_id(
            libraries,
            self._profile.object_id("Application/Library Manager"),
        )
