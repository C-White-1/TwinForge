"""CODESYS PLCopen POU, interface, and IEC datatype serialization."""

from __future__ import annotations

from collections.abc import Callable
import re
import xml.etree.ElementTree as ET

from twinforge.ir import (
    IRDirection,
    IRParameter,
    IRReusableUnit,
    IRUnitKind,
    IRVariable,
)

from .plcopen_codesys import CODESYS_NAMESPACE
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
_BOUNDED_STRING = re.compile(r"(W?STRING)\((\d+)\)\Z", re.IGNORECASE)

BodyTextProvider = Callable[[IRReusableUnit], str]
LifecycleEmitter = Callable[[ET.Element, IRReusableUnit], None]
ObjectIdProvider = Callable[[str], str]
ObjectIdAppender = Callable[[ET.Element, str], None]


class CodesysIRInterfaceEmitter:
    """Serialize reusable-unit parameters, locals, and IEC datatypes."""

    def emit(self, interface: ET.Element, unit: IRReusableUnit) -> None:
        """Append parameters and local variables in CODESYS source order."""

        self._parameters(interface, unit.parameters)
        self._variables(interface, unit.variables)

    def data_type(
        self,
        parent: ET.Element,
        data_type: str | None,
        dimensions: str | None,
    ) -> None:
        """Append one scalar, array, bounded-string, or derived type."""

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
            self.data_type(base_type, data_type, None)
            return
        if data_type is not None and data_type.upper() in _ELEMENTARY_TYPES:
            ET.SubElement(parent, q(ns, data_type.upper()))
            return
        bounded_string = (
            _BOUNDED_STRING.fullmatch(data_type)
            if data_type is not None
            else None
        )
        if bounded_string is not None:
            ET.SubElement(
                parent,
                q(ns, bounded_string.group(1).lower()),
                {"length": bounded_string.group(2)},
            )
            return
        ET.SubElement(
            parent,
            q(ns, "derived"),
            {"name": data_type or "TF_UNRESOLVED_TYPE"},
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
                item for item in parameters if item.direction is direction
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
        self.data_type(
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
        variables = ET.SubElement(interface, q(ns, "inputVars"))
        variable = ET.SubElement(
            variables,
            q(ns, "variable"),
            {"name": parameter.name},
        )
        type_element = ET.SubElement(variable, q(ns, "type"))
        pointer = ET.SubElement(type_element, q(ns, "pointer"))
        base_type = ET.SubElement(pointer, q(ns, "baseType"))
        self.data_type(base_type, parameter.data_type, None)

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


class CodesysIRPOUEmitter:
    """Serialize one reusable IR unit independently of project structure."""

    def __init__(
        self,
        *,
        interface_emitter: CodesysIRInterfaceEmitter,
        body_text: BodyTextProvider,
        emit_lifecycle: LifecycleEmitter,
        object_id: ObjectIdProvider,
        append_object_id: ObjectIdAppender,
    ) -> None:
        self._interface_emitter = interface_emitter
        self._body_text = body_text
        self._emit_lifecycle = emit_lifecycle
        self._object_id = object_id
        self._append_object_id = append_object_id

    def emit(self, parent: ET.Element, unit: IRReusableUnit) -> None:
        """Append one function or function-block POU."""

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
        self._interface_emitter.emit(interface, unit)
        body = ET.SubElement(pou, q(ns, "body"))
        st = ET.SubElement(body, q(ns, "ST"))
        text = ET.SubElement(st, q(XHTML_NAMESPACE, "xhtml"))
        text.text = self._body_text(unit)
        add_data = ET.SubElement(pou, q(ns, "addData"))
        self._emit_lifecycle(add_data, unit)
        self._append_object_id(
            add_data,
            self._object_id(f"Application/pou/{unit.name}"),
        )
