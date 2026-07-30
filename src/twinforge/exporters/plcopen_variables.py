"""Emit PLCopen variable declarations from vendor-neutral tags."""

from __future__ import annotations

from collections.abc import Callable, Iterable
import xml.etree.ElementTree as ET

from twinforge.model import Tag

from .plcopen_operands import PLCOPEN_PRIMITIVE_TYPES
from .plcopen_xml import (
    plcopen_scalar_value,
    qualified_name,
    variable_add_data,
)


XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
TWINFORGE_ALIAS_EXTENSION = "https://twinforge.dev/plcopenxml/rockwell-alias"
TWINFORGE_ONS_EXTENSION = "https://twinforge.dev/plcopenxml/rockwell-ons"
TWINFORGE_ENGINEERING_UNIT_EXTENSION = (
    "https://twinforge.dev/plcopenxml/engineering-unit"
)

TagExportType = Callable[[Tag], str]
DiagnosticReporter = Callable[..., None]


class PLCopenVariableEmitter:
    """Serialize supported scalar tags without target-specific decisions."""

    def __init__(
        self,
        *,
        namespace: str,
        tag_export_type: TagExportType,
        timer_type: str,
        report_diagnostic: DiagnosticReporter,
    ) -> None:
        self._namespace = namespace
        self._tag_export_type = tag_export_type
        self._timer_type = timer_type
        self._report_diagnostic = report_diagnostic

    def emit(
        self,
        parent: ET.Element,
        list_name: str,
        tags: Iterable[Tag],
        *,
        attributes: dict[str, str] | None = None,
    ) -> ET.Element | None:
        """Append one variable list, preserving evidence and source order."""

        supported = self._supported_tags(tags)
        if not supported:
            return None
        variable_list = ET.SubElement(
            parent,
            qualified_name(self._namespace, list_name),
            attributes if attributes is not None else {},
        )
        for tag in supported:
            self._variable(variable_list, tag)
        return variable_list

    def _supported_tags(self, tags: Iterable[Tag]) -> list[Tag]:
        supported: list[Tag] = []
        for tag in tags:
            data_type = self._tag_export_type(tag)
            if tag.alias_for:
                self._report_diagnostic(
                    "alias_exported_as_surrogate",
                    "Rockwell alias was exported as a portable variable "
                    "without an I/O binding",
                    tag.name,
                    raw_value=tag.alias_for,
                )
            derived_type = tag.metadata.get("plcopen_derived_type")
            if (
                data_type not in PLCOPEN_PRIMITIVE_TYPES
                and data_type != "TIMER"
                and derived_type is None
            ):
                self._report_diagnostic(
                    "unsupported_variable_type",
                    "variable is preserved in the source model but not "
                    "declared in this PLCopen milestone",
                    tag.name,
                    raw_value=tag.data_type,
                )
                continue
            if tag.dimensions:
                self._report_diagnostic(
                    "array_variable_not_exported",
                    "array variable export is not implemented",
                    tag.name,
                    raw_value=tag.dimensions,
                )
                continue
            supported.append(tag)
        return supported

    def _variable(self, parent: ET.Element, tag: Tag) -> None:
        variable = ET.SubElement(
            parent,
            qualified_name(self._namespace, "variable"),
            {"name": tag.name},
        )
        self._type(variable, tag)
        self._initial_value(variable, tag)
        self._source_operand(variable, tag)
        self._oneshot_storage(variable, tag)
        self._engineering_unit(variable, tag)
        self._documentation(variable, tag)

    def _type(self, variable: ET.Element, tag: Tag) -> None:
        type_element = ET.SubElement(
            variable,
            qualified_name(self._namespace, "type"),
        )
        derived_type = tag.metadata.get("plcopen_derived_type")
        if derived_type is not None:
            ET.SubElement(
                type_element,
                qualified_name(self._namespace, "derived"),
                {"name": str(derived_type)},
            )
        elif self._tag_export_type(tag) == "TIMER":
            ET.SubElement(
                type_element,
                qualified_name(self._namespace, "derived"),
                {"name": self._timer_type},
            )
        else:
            ET.SubElement(
                type_element,
                qualified_name(
                    self._namespace,
                    self._tag_export_type(tag),
                ),
            )

    def _initial_value(self, variable: ET.Element, tag: Tag) -> None:
        if tag.initial_value is None:
            return
        initial_value = ET.SubElement(
            variable,
            qualified_name(self._namespace, "initialValue"),
        )
        ET.SubElement(
            initial_value,
            qualified_name(self._namespace, "simpleValue"),
            {"value": plcopen_scalar_value(tag)},
        )

    def _source_operand(self, variable: ET.Element, tag: Tag) -> None:
        source_operand = tag.alias_for or tag.metadata.get(
            "plcopen_source_operand"
        )
        if not source_operand:
            return
        data = self._extension(variable, TWINFORGE_ALIAS_EXTENSION)
        alias_for = ET.SubElement(data, "AliasFor", {"xmlns": ""})
        alias_for.text = source_operand

    def _oneshot_storage(self, variable: ET.Element, tag: Tag) -> None:
        storage_operand = tag.metadata.get("rockwell_ons_storage")
        if not storage_operand:
            return
        data = self._extension(variable, TWINFORGE_ONS_EXTENSION)
        storage = ET.SubElement(data, "StorageOperand", {"xmlns": ""})
        storage.text = str(storage_operand)

    def _engineering_unit(self, variable: ET.Element, tag: Tag) -> None:
        if tag.engineering_unit is None:
            return
        data = self._extension(
            variable,
            TWINFORGE_ENGINEERING_UNIT_EXTENSION,
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
            unit.set("SourceOperand", tag.engineering_unit.source_operand)
        if tag.engineering_unit.inherited_from:
            unit.set("InheritedFrom", tag.engineering_unit.inherited_from)
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

    def _documentation(self, variable: ET.Element, tag: Tag) -> None:
        if not tag.description:
            return
        documentation = ET.SubElement(
            variable,
            qualified_name(self._namespace, "documentation"),
        )
        xhtml = ET.SubElement(
            documentation,
            qualified_name(XHTML_NAMESPACE, "xhtml"),
        )
        xhtml.text = tag.description

    def _extension(self, variable: ET.Element, name: str) -> ET.Element:
        add_data = variable_add_data(variable, self._namespace)
        return ET.SubElement(
            add_data,
            qualified_name(self._namespace, "data"),
            {"name": name, "handleUnknown": "preserve"},
        )
