from __future__ import annotations

from twinforge.converters.diagnostics import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import Controller, Datatype, DatatypeMember
from twinforge.parsers.l5x.capture import CapturedSection

from .conversion_value import optional_int
from .source_extension import captured_to_source_extension


def convert_datatype(
    section: CapturedSection,
    *,
    diagnostics: list[ConversionDiagnostic] | None = None,
) -> Datatype:
    if section.tag != "DataType":
        raise ValueError(f"expected a DataType section, got {section.tag!r}")

    datatype = Datatype(
        name=section.attributes.get("Name", ""),
        family=section.attributes.get("Family"),
        classification=section.attributes.get("Class"),
        description=_description(section),
        source_extensions=[captured_to_source_extension(section)],
    )
    if not datatype.name:
        _emit(
            diagnostics,
            DiagnosticSeverity.ERROR,
            "datatype_missing_name",
            "data type is missing its Name attribute",
        )

    member_names: set[str] = set()
    for members in section.elements.get("Members", []):
        for member_section in members.elements.get("Member", []):
            member = _convert_member(member_section, datatype.name, diagnostics)
            if member is None:
                continue
            if member.name in member_names:
                _emit(
                    diagnostics,
                    DiagnosticSeverity.ERROR,
                    "duplicate_datatype_member",
                    f"data type {datatype.name!r} contains duplicate member {member.name!r}",
                    datatype.name,
                    "Name",
                    member.name,
                )
                continue
            member_names.add(member.name)
            datatype.members.append(member)
    return datatype


def resolve_datatype_references(controller: Controller) -> None:
    """Link names to controller-defined types; leave atomic/external names unresolved."""

    for datatype in controller.datatypes.values():
        for member in datatype.members:
            if member.data_type_name:
                member.data_type = controller.get_datatype(member.data_type_name)

    for tag in controller.tags.values():
        if tag.data_type:
            tag.data_type_definition = controller.get_datatype(tag.data_type)
    for program in controller.programs.values():
        for tag in program.tags.values():
            if tag.data_type:
                tag.data_type_definition = controller.get_datatype(tag.data_type)

    for instruction in controller.add_on_instructions.values():
        for parameter in instruction.parameters.values():
            data_type = parameter.effective_data_type
            if data_type:
                parameter.data_type_definition = controller.get_datatype(
                    data_type
                )
        for tag in instruction.local_tags.values():
            if tag.data_type:
                tag.data_type_definition = controller.get_datatype(
                    tag.data_type
                )


def _convert_member(
    section: CapturedSection,
    datatype_name: str,
    diagnostics: list[ConversionDiagnostic] | None,
) -> DatatypeMember | None:
    name = section.attributes.get("Name")
    if not name:
        _emit(
            diagnostics,
            DiagnosticSeverity.ERROR,
            "datatype_member_missing_name",
            f"data type {datatype_name!r} contains a member without a name",
            datatype_name,
        )
        return None
    data_type_name = section.attributes.get("DataType")
    if not data_type_name:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "datatype_member_type_missing",
            f"member {name!r} does not specify DataType",
            datatype_name,
            "DataType",
        )
    return DatatypeMember(
        name=name,
        data_type_name=data_type_name,
        dimension=section.attributes.get("Dimension"),
        radix=section.attributes.get("Radix"),
        hidden=_optional_bool(section, "Hidden", diagnostics, datatype_name),
        external_access=section.attributes.get("ExternalAccess"),
        description=_description(section),
        target=section.attributes.get("Target"),
        bit_number=optional_int(
            section.attributes.get("BitNumber"),
            "BitNumber",
            section,
            diagnostics,
        ),
        source_extensions=[captured_to_source_extension(section)],
    )


def _description(section: CapturedSection) -> str | None:
    descriptions = section.elements.get("Description", [])
    if not descriptions or descriptions[0].text is None:
        return None
    return descriptions[0].text.strip()


def _optional_bool(
    section: CapturedSection,
    field: str,
    diagnostics: list[ConversionDiagnostic] | None,
    object_name: str,
) -> bool | None:
    value = section.attributes.get(field)
    if value == "true":
        return True
    if value == "false":
        return False
    if value is not None:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "invalid_boolean",
            f"{field} must be 'true' or 'false', got {value!r}",
            object_name,
            field,
            value,
        )
    return None


def _emit(
    diagnostics: list[ConversionDiagnostic] | None,
    severity: DiagnosticSeverity,
    code: str,
    message: str,
    object_name: str | None = None,
    field: str | None = None,
    raw_value: str | None = None,
) -> None:
    if diagnostics is None:
        return
    diagnostics.append(
        ConversionDiagnostic(
            severity=severity,
            code=code,
            message=message,
            object_name=object_name,
            field=field,
            raw_value=raw_value,
        )
    )
