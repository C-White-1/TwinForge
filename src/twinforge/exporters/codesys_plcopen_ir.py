"""CODESYS PLCopen XML export for vendor-neutral executable IR."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

from twinforge.ir import (
    IRDirection,
    IRParameter,
    IRReusableUnit,
    IRUnitKind,
    IRVariable,
)

from .codesys_st import emit_codesys_st_routine, emit_codesys_st_unit
from .iec_st import IECRequirement, IECSTDiagnostic
from .plcopen_codesys import CODESYS_NAMESPACE, CodesysProfileSupport
from .plcopen_types import PLCOPEN_CODESYS_NAMESPACE
from .plcopen_xml import qualified_name as q


XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
_ELEMENTARY_TYPES = {
    "BOOL",
    "BYTE",
    "DATE",
    "DINT",
    "DWORD",
    "INT",
    "LINT",
    "LREAL",
    "LWORD",
    "REAL",
    "SINT",
    "STRING",
    "TIME",
    "TIME_OF_DAY",
    "TOD",
    "UDINT",
    "UINT",
    "ULINT",
    "USINT",
    "WORD",
    "WSTRING",
}


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
        }
        return not self.requirements and not any(
            item.code in blocking for item in self.diagnostics
        )


@dataclass(frozen=True)
class CodesysArgumentBinding:
    """Bind one reusable-unit parameter to a program-local variable."""

    parameter_name: str
    variable_name: str
    dimensions: str | None = None
    initial_value: str | None = None


@dataclass(frozen=True)
class CodesysProjectIntegration:
    """Explicit program, call, and task configuration for one IR unit."""

    bindings: tuple[CodesysArgumentBinding, ...]
    program_name: str = "PLC_PRG"
    task_name: str = "MainTask"
    instance_name: str = "fbInstance"
    interval_ms: int = 20
    priority: int = 1


class CodesysIRPLCopenExporter:
    """Build importable CODESYS PLCopen POUs from executable IR."""

    def __init__(self) -> None:
        self._profile = CodesysProfileSupport(PLCOPEN_CODESYS_NAMESPACE)

    def export(
        self,
        unit: IRReusableUnit,
        *,
        destination: str | Path | None = None,
        project_name: str = "TwinForgeIR",
        creation_time: datetime | None = None,
        integration: CodesysProjectIntegration | None = None,
    ) -> CodesysPLCopenIRResult:
        """Serialize a reusable unit and optional scheduled program call."""

        self._profile.reset()
        emission = emit_codesys_st_unit(unit)
        root = self._build(
            unit,
            project_name=project_name,
            creation_time=creation_time,
            integration=integration,
        )
        ET.indent(root, space="  ")
        xml = ET.tostring(root, encoding="unicode", xml_declaration=True)
        if destination is not None:
            Path(destination).write_text(xml, encoding="utf-8")
        return CodesysPLCopenIRResult(
            xml=xml,
            diagnostics=emission.diagnostics,
            requirements=emission.requirements,
        )

    def _build(
        self,
        unit: IRReusableUnit,
        *,
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
            self._program(wrapper, unit, integration)
        wrapper = ET.SubElement(
            resource_add_data,
            q(ns, "data"),
            self._pou_wrapper_attributes(),
        )
        self._pou(wrapper, unit)
        application_id = self._profile.object_id("Application")
        self._profile.append_object_id_data(
            resource_add_data,
            application_id,
        )
        self._project_structure(
            add_data,
            unit,
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
        unit: IRReusableUnit,
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
        instance = ET.SubElement(
            local_variables,
            q(ns, "variable"),
            {"name": integration.instance_name},
        )
        instance_type = ET.SubElement(instance, q(ns, "type"))
        self._data_type(instance_type, unit.name, None)
        parameters = {item.name: item for item in unit.parameters}
        for binding in integration.bindings:
            parameter = parameters[binding.parameter_name]
            variable = ET.SubElement(
                local_variables,
                q(ns, "variable"),
                {"name": binding.variable_name},
            )
            type_element = ET.SubElement(variable, q(ns, "type"))
            self._data_type(
                type_element,
                parameter.data_type,
                binding.dimensions,
            )
            if binding.initial_value is not None:
                initial = ET.SubElement(
                    variable,
                    q(ns, "initialValue"),
                )
                ET.SubElement(
                    initial,
                    q(ns, "simpleValue"),
                    {"value": binding.initial_value},
                )

        body = ET.SubElement(pou, q(ns, "body"))
        st = ET.SubElement(body, q(ns, "ST"))
        text = ET.SubElement(st, q(XHTML_NAMESPACE, "xhtml"))
        text.text = self._program_call(unit, integration)
        self._profile.append_object_id(
            pou,
            self._profile.object_id(
                f"Application/program/{integration.program_name}"
            ),
        )

    @staticmethod
    def _program_call(
        unit: IRReusableUnit,
        integration: CodesysProjectIntegration,
    ) -> str:
        parameters = {item.name: item for item in unit.parameters}
        arguments = []
        for binding in integration.bindings:
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
        return f"{integration.instance_name}(\n{joined}\n);"

    def _pou(self, parent: ET.Element, unit: IRReusableUnit) -> None:
        ns = PLCOPEN_CODESYS_NAMESPACE
        pou = ET.SubElement(
            parent,
            q(ns, "pou"),
            {
                "name": unit.name,
                "pouType": (
                    "functionBlock"
                    if unit.kind is IRUnitKind.FUNCTION_BLOCK
                    else "function"
                ),
            },
        )
        interface = ET.SubElement(pou, q(ns, "interface"))
        self._parameters(interface, unit.parameters)
        self._variables(interface, unit.variables)
        body = ET.SubElement(pou, q(ns, "body"))
        st = ET.SubElement(body, q(ns, "ST"))
        text = ET.SubElement(st, q(XHTML_NAMESPACE, "xhtml"))
        text.text = self._body_text(unit)
        self._profile.append_object_id(
            pou,
            self._profile.object_id(f"Application/pou/{unit.name}"),
        )

    def _parameters(
        self,
        interface: ET.Element,
        parameters: tuple[IRParameter, ...],
    ) -> None:
        groups = (
            (IRDirection.INPUT, "inputVars"),
            (IRDirection.OUTPUT, "outputVars"),
            (IRDirection.INOUT, "inOutVars"),
            (IRDirection.UNKNOWN, "localVars"),
        )
        for direction, element_name in groups:
            members = [
                item
                for item in parameters
                if item.direction is direction
            ]
            ordinary = [
                item for item in members if not item.generic_dimensions
            ]
            generic = [
                item for item in members if item.generic_dimensions
            ]
            if ordinary:
                variable_list = ET.SubElement(
                    interface,
                    q(PLCOPEN_CODESYS_NAMESPACE, element_name),
                )
                for parameter in ordinary:
                    self._variable(variable_list, parameter)
            for parameter in generic:
                self._generic_array_parameter(interface, parameter)

    def _variables(
        self,
        interface: ET.Element,
        variables: tuple[IRVariable, ...],
    ) -> None:
        if not variables:
            return
        local_variables = ET.SubElement(
            interface,
            q(PLCOPEN_CODESYS_NAMESPACE, "localVars"),
        )
        for variable in variables:
            self._variable(local_variables, variable)

    def _variable(
        self,
        parent: ET.Element,
        declaration: IRParameter | IRVariable,
    ) -> None:
        ns = PLCOPEN_CODESYS_NAMESPACE
        variable = ET.SubElement(
            parent,
            q(ns, "variable"),
            {"name": declaration.name},
        )
        type_element = ET.SubElement(variable, q(ns, "type"))
        self._data_type(
            type_element,
            declaration.data_type,
            declaration.dimensions,
        )

    def _generic_array_parameter(
        self,
        interface: ET.Element,
        parameter: IRParameter,
    ) -> None:
        ns = PLCOPEN_CODESYS_NAMESPACE
        # Native CODESYS exports encode variable-length InOut arrays as an
        # input pointer plus attributes that reconstruct the original scope.
        variables = ET.SubElement(interface, q(ns, "inputVars"))
        variable = ET.SubElement(
            variables,
            q(ns, "variable"),
            {"name": parameter.name},
        )
        type_element = ET.SubElement(variable, q(ns, "type"))
        pointer = ET.SubElement(type_element, q(ns, "pointer"))
        base_type = ET.SubElement(pointer, q(ns, "baseType"))
        self._data_type(base_type, parameter.data_type, None)

        add_data = ET.SubElement(variable, q(ns, "addData"))
        data = ET.SubElement(
            add_data,
            q(ns, "data"),
            {
                "name": f"{CODESYS_NAMESPACE}/attributes",
                "handleUnknown": "implementation",
            },
        )
        attributes = ET.SubElement(data, q(ns, "Attributes"))
        dimension_count = len((parameter.dimensions or "").split(","))
        array_shape = ", ".join("*" for _ in range(dimension_count))
        scope = {
            IRDirection.INPUT: "Input",
            IRDirection.OUTPUT: "Output",
            IRDirection.INOUT: "Inout",
            IRDirection.UNKNOWN: "Local",
        }[parameter.direction]
        values = (
            ("variable_length_array_original_scope", scope),
            (
                "variable_length_array",
                f"ARRAY[{array_shape}] OF {parameter.data_type}",
            ),
            ("Dimensions", str(dimension_count)),
        )
        for name, value in values:
            ET.SubElement(
                attributes,
                q(ns, "Attribute"),
                {"Name": name, "Value": value},
            )

    def _data_type(
        self,
        parent: ET.Element,
        data_type: str | None,
        dimensions: str | None,
    ) -> None:
        ns = PLCOPEN_CODESYS_NAMESPACE
        if dimensions is not None:
            array = ET.SubElement(parent, q(ns, "array"))
            for dimension in dimensions.split(","):
                length = int(dimension)
                ET.SubElement(
                    array,
                    q(ns, "dimension"),
                    {"lower": "0", "upper": str(max(length - 1, 0))},
                )
            base_type = ET.SubElement(array, q(ns, "baseType"))
            self._data_type(base_type, data_type, None)
            return
        if data_type is not None and data_type.upper() in _ELEMENTARY_TYPES:
            ET.SubElement(parent, q(ns, data_type.upper()))
            return
        ET.SubElement(
            parent,
            q(ns, "derived"),
            {"name": data_type or "TF_UNRESOLVED_TYPE"},
        )

    @staticmethod
    def _body_text(unit: IRReusableUnit) -> str:
        if not unit.routines:
            return ""
        bodies = []
        for routine in unit.routines:
            emission = emit_codesys_st_routine(routine)
            if len(unit.routines) > 1:
                bodies.append(f"(* Routine: {routine.name} *)\n")
            bodies.append(emission.text)
        return "\n".join(item.rstrip() for item in bodies)

    def _project_structure(
        self,
        add_data: ET.Element,
        unit: IRReusableUnit,
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
        ET.SubElement(
            application,
            q(ns, "Object"),
            {
                "Name": unit.name,
                "ObjectId": self._profile.object_id(
                    f"Application/pou/{unit.name}"
                ),
            },
        )
