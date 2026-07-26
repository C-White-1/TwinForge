"""Convert captured L5X AOIs into vendor-neutral reusable instructions."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from twinforge.converters.diagnostics import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import (
    AddOnInstruction,
    AddOnInstructionDependency,
    AddOnInstructionParameter,
    Tag,
    TagValue,
)
from twinforge.parsers.l5x.capture import CapturedSection

from .conversion_value import emit_diagnostic, optional_bool
from .program import convert_routine
from .source_extension import captured_to_source_extension
from .tag import parse_scalar_value


def convert_add_on_instruction(
    section: CapturedSection,
    *,
    diagnostics: list[ConversionDiagnostic] | None = None,
) -> AddOnInstruction:
    """Convert one specification-captured Add-On Instruction definition."""

    if section.tag != "AddOnInstructionDefinition":
        raise ValueError(
            "expected an AddOnInstructionDefinition section, "
            f"got {section.tag!r}"
        )
    instruction = AddOnInstruction(
        name=section.attributes.get("Name", ""),
        revision=section.attributes.get("Revision"),
        vendor=section.attributes.get("Vendor"),
        description=_child_text(section, "Description"),
        execute_prescan=optional_bool(
            section.attributes.get("ExecutePrescan"),
            "ExecutePrescan",
            section,
            diagnostics,
        ),
        execute_postscan=optional_bool(
            section.attributes.get("ExecutePostscan"),
            "ExecutePostscan",
            section,
            diagnostics,
        ),
        execute_enable_in_false=optional_bool(
            section.attributes.get("ExecuteEnableInFalse"),
            "ExecuteEnableInFalse",
            section,
            diagnostics,
        ),
        source_extensions=[captured_to_source_extension(section)],
    )
    for parameters in section.elements.get("Parameters", []):
        for parameter_section in parameters.elements.get("Parameter", []):
            parameter = _convert_parameter(
                parameter_section, diagnostics
            )
            if parameter.name in instruction.parameters:
                emit_diagnostic(
                    diagnostics,
                    DiagnosticSeverity.ERROR,
                    "duplicate_aoi_parameter",
                    (
                        f"AOI {instruction.name!r} contains duplicate "
                        f"parameter {parameter.name!r}"
                    ),
                    parameter_section,
                    "Name",
                    parameter.name,
                )
                continue
            instruction.add_parameter(parameter)
    for routines in section.elements.get("Routines", []):
        for routine_section in routines.elements.get("Routine", []):
            routine = convert_routine(
                routine_section, instruction.name, diagnostics
            )
            if routine is not None:
                instruction.add_routine(routine)
    for scan_modes in section.elements.get("ScanModeRoutine", []):
        for routine_section in scan_modes.elements.get("Routine", []):
            routine = convert_routine(
                routine_section,
                instruction.name,
                diagnostics,
            )
            if routine is not None:
                instruction.add_scan_mode_routine(routine)
    for local_tags in section.elements.get("LocalTags", []):
        for tag_section in local_tags.elements.get("LocalTag", []):
            tag = _convert_local_tag(tag_section, diagnostics)
            if tag.name in instruction.local_tags:
                emit_diagnostic(
                    diagnostics,
                    DiagnosticSeverity.ERROR,
                    "duplicate_aoi_local_tag",
                    (
                        f"AOI {instruction.name!r} contains duplicate "
                        f"local tag {tag.name!r}"
                    ),
                    tag_section,
                    "Name",
                    tag.name,
                )
                continue
            instruction.add_local_tag(tag)
    for dependencies in section.elements.get("Dependencies", []):
        for dependency in dependencies.elements.get("Dependency", []):
            instruction.dependencies.append(
                AddOnInstructionDependency(
                    dependency_type=dependency.attributes.get("Type", ""),
                    name=dependency.attributes.get("Name", ""),
                    source_extensions=[
                        captured_to_source_extension(dependency)
                    ],
                )
            )
    return instruction


def _convert_parameter(
    section: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> AddOnInstructionParameter:
    return AddOnInstructionParameter(
        name=section.attributes.get("Name", ""),
        data_type=section.attributes.get("DataType"),
        usage=section.attributes.get("Usage"),
        dimensions=section.attributes.get("Dimensions"),
        radix=section.attributes.get("Radix"),
        required=optional_bool(
            section.attributes.get("Required"),
            "Required",
            section,
            diagnostics,
        ),
        visible=optional_bool(
            section.attributes.get("Visible"),
            "Visible",
            section,
            diagnostics,
        ),
        constant=optional_bool(
            section.attributes.get("Constant"),
            "Constant",
            section,
            diagnostics,
        ),
        external_access=section.attributes.get("ExternalAccess"),
        alias_for=section.attributes.get("AliasFor"),
        description=_child_text(section, "Description"),
        default_value=_default_value(section, diagnostics),
        source_extensions=[captured_to_source_extension(section)],
    )


def _convert_local_tag(
    section: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> Tag:
    return Tag(
        name=section.attributes.get("Name", ""),
        tag_type="Base",
        data_type=section.attributes.get("DataType"),
        dimensions=section.attributes.get("Dimensions"),
        radix=section.attributes.get("Radix"),
        external_access=section.attributes.get("ExternalAccess"),
        description=_child_text(section, "Description"),
        initial_value=_default_value(section, diagnostics),
        source_extensions=[captured_to_source_extension(section)],
    )


def _default_value(
    section: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> TagValue | None:
    for data in section.elements.get("DefaultData", []):
        if data.attributes.get("Format") != "Decorated":
            continue
        for child in data.ordered_children:
            if not isinstance(child, ET.Element) or child.tag != "DataValue":
                continue
            lexical = child.attrib.get("Value")
            data_type = child.attrib.get("DataType") or section.attributes.get(
                "DataType"
            )
            if lexical is None or data_type is None:
                continue
            try:
                value = parse_scalar_value(data_type, lexical)
            except ValueError:
                emit_diagnostic(
                    diagnostics,
                    DiagnosticSeverity.WARNING,
                    "invalid_aoi_parameter_default",
                    (
                        f"AOI parameter {section.attributes.get('Name')!r} "
                        f"has invalid {data_type} default data"
                    ),
                    section,
                    "DefaultData",
                    lexical,
                )
                return None
            if value is None:
                return None
            return TagValue(
                value=value,
                data_type=data_type.upper(),
                lexical_value=lexical,
                radix=child.attrib.get("Radix")
                or section.attributes.get("Radix"),
            )
    return None


def _child_text(section: CapturedSection, name: str) -> str | None:
    children = section.elements.get(name, [])
    if not children or children[0].text is None:
        return None
    return children[0].text.strip()
