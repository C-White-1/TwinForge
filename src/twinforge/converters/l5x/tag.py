from __future__ import annotations

import xml.etree.ElementTree as ET

from twinforge.converters.diagnostics import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import (
    CompositeTagValue,
    ConsumedTagConfiguration,
    MessageTagConfiguration,
    ProducedTagConfiguration,
    Tag,
    TagValue,
)
from twinforge.parsers.l5x.capture import CapturedSection

from .source_extension import captured_to_source_extension
from .decorated_value import parse_composite_value, parse_scalar_value


_KNOWN_TAG_TYPES = {"Base", "Alias", "Produced", "Consumed"}


def convert_tag(
    section: CapturedSection,
    *,
    diagnostics: list[ConversionDiagnostic] | None = None,
) -> Tag:
    """Convert safe tag metadata while preserving every data representation."""

    if section.tag != "Tag":
        raise ValueError(f"expected a Tag section, got {section.tag!r}")

    name = section.attributes.get("Name", "")
    tag_type = section.attributes.get("TagType")
    if not name:
        _emit(
            diagnostics,
            DiagnosticSeverity.ERROR,
            "tag_missing_name",
            "tag is missing its Name attribute",
            None,
        )
    if tag_type is not None and tag_type not in _KNOWN_TAG_TYPES:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "unknown_tag_type",
            f"tag {name!r} uses unknown tag type {tag_type!r}",
            name,
            "TagType",
            tag_type,
        )
    if tag_type == "Alias" and "AliasFor" not in section.attributes:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "alias_target_missing",
            f"alias tag {name!r} does not specify AliasFor",
            name,
            "AliasFor",
        )
    if tag_type == "Base" and "DataType" not in section.attributes:
        _emit(
            diagnostics,
            DiagnosticSeverity.WARNING,
            "base_tag_data_type_missing",
            f"base tag {name!r} does not specify DataType",
            name,
            "DataType",
        )

    return Tag(
        name=name,
        tag_type=tag_type,
        data_type=section.attributes.get("DataType"),
        dimensions=section.attributes.get("Dimensions"),
        radix=section.attributes.get("Radix"),
        constant=_optional_bool(section, "Constant", diagnostics),
        alias_for=section.attributes.get("AliasFor"),
        external_access=section.attributes.get("ExternalAccess"),
        permission_set=section.attributes.get("PermissionSet"),
        description=_description(section),
        initial_value=_initial_value(section, diagnostics),
        composite_initial_value=_composite_initial_value(section, diagnostics),
        message_configuration=_message_configuration(section),
        produced_configuration=_produced_configuration(section),
        consumed_configuration=_consumed_configuration(section),
        source_extensions=[captured_to_source_extension(section)],
    )


def _produced_configuration(
    section: CapturedSection,
) -> ProducedTagConfiguration | None:
    items = section.elements.get("ProduceInfo", [])
    if not items:
        return None
    attributes = items[0].attributes
    return ProducedTagConfiguration(
        produce_count=_logix_int(attributes.get("ProduceCount")),
        minimum_rpi=_logix_float(attributes.get("MinimumRPI")),
        maximum_rpi=_logix_float(attributes.get("MaximumRPI")),
        default_rpi=_logix_float(attributes.get("DefaultRPI")),
        plc_mapping_file=_logix_int(attributes.get("PLCMappingFile")),
        plc2_mapping=_logix_int(attributes.get("PLC2Mapping")),
        programmatically_send_event_trigger=_lexical_bool(
            attributes.get("ProgrammaticallySendEventTrigger")
        ),
        unicast_permitted=_lexical_bool(
            attributes.get("UnicastPermitted")
        ),
        raw_attributes={**attributes, **items[0].extra_attributes},
    )


def _consumed_configuration(
    section: CapturedSection,
) -> ConsumedTagConfiguration | None:
    items = section.elements.get("ConsumeInfo", [])
    if not items:
        return None
    attributes = items[0].attributes
    return ConsumedTagConfiguration(
        producer=attributes.get("Producer"),
        remote_tag=attributes.get("RemoteTag"),
        remote_file=_logix_int(attributes.get("RemoteFile")),
        rpi=_logix_float(attributes.get("RPI")),
        programmatically_send_event_trigger=_lexical_bool(
            attributes.get("ProgrammaticallySendEventTrigger")
        ),
        raw_attributes={**attributes, **items[0].extra_attributes},
    )


def _message_configuration(
    section: CapturedSection,
) -> MessageTagConfiguration | None:
    for data in section.elements.get("Data", []):
        if data.attributes.get("Format") != "Message":
            continue
        parameters = data.elements.get("MessageParameters", [])
        if not parameters:
            continue
        attributes = parameters[0].attributes
        return MessageTagConfiguration(
            message_type=attributes.get("MessageType"),
            requested_length=_logix_int(attributes.get("RequestedLength")),
            connected_flag=_logix_int(attributes.get("ConnectedFlag")),
            connection_path=attributes.get("ConnectionPath"),
            communication_type_code=_logix_int(
                attributes.get("CommTypeCode")
            ),
            service_code=_logix_int(attributes.get("ServiceCode")),
            object_type=_logix_int(attributes.get("ObjectType")),
            target_object=_logix_int(attributes.get("TargetObject")),
            attribute_number=_logix_int(attributes.get("AttributeNumber")),
            local_index=_logix_int(attributes.get("LocalIndex")),
            local_element=attributes.get("LocalElement"),
            destination_tag=attributes.get("DestinationTag"),
            large_packet_usage=_lexical_bool(
                attributes.get("LargePacketUsage")
            ),
            raw_attributes=dict(attributes),
        )
    return None


def _logix_int(value: str | None) -> int | None:
    if value is None:
        return None
    if "#" in value:
        radix, digits = value.split("#", 1)
        return int(digits.replace("_", ""), int(radix))
    return int(value, 0)


def _logix_float(value: str | None) -> float | None:
    return float(value) if value is not None else None


def _lexical_bool(value: str | None) -> bool | None:
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def _description(section: CapturedSection) -> str | None:
    descriptions = section.elements.get("Description", [])
    if not descriptions or descriptions[0].text is None:
        return None
    return descriptions[0].text.strip()


def _initial_value(
    section: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> TagValue | None:
    for data in section.elements.get("Data", []):
        if data.attributes.get("Format") != "Decorated":
            continue
        for child in data.ordered_children:
            if not isinstance(child, ET.Element) or child.tag != "DataValue":
                continue
            lexical_value = child.attrib.get("Value")
            data_type = child.attrib.get("DataType") or section.attributes.get(
                "DataType"
            )
            if lexical_value is None or data_type is None:
                return None
            try:
                value = parse_scalar_value(data_type, lexical_value)
            except ValueError:
                _emit(
                    diagnostics,
                    DiagnosticSeverity.WARNING,
                    "invalid_scalar_tag_value",
                    (
                        f"tag {section.attributes.get('Name', '')!r} has an "
                        f"invalid {data_type} decorated value"
                    ),
                    section.attributes.get("Name"),
                    "Data",
                    lexical_value,
                )
                return None
            if value is None:
                return None
            return TagValue(
                value=value,
                data_type=data_type.upper(),
                lexical_value=lexical_value,
                radix=child.attrib.get("Radix")
                or section.attributes.get("Radix"),
            )
    return None


def _composite_initial_value(
    section: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> CompositeTagValue | None:
    """Promote one decorated composite while retaining its source vocabulary."""

    for data in section.elements.get("Data", []):
        if data.attributes.get("Format") != "Decorated":
            continue
        for child in data.ordered_children:
            if isinstance(child, ET.Element) and child.tag in {
                "Array",
                "Structure",
            }:
                return parse_composite_value(
                    child,
                    on_invalid=lambda data_type, lexical, element: _emit(
                        diagnostics,
                        DiagnosticSeverity.WARNING,
                        "invalid_composite_tag_value",
                        (
                            f"tag {section.attributes.get('Name', '')!r} has an "
                            f"invalid {data_type} composite member value"
                        ),
                        section.attributes.get("Name"),
                        element.attrib.get("Name") or element.attrib.get("Index"),
                        lexical,
                    ),
                )
    return None


def _optional_bool(
    section: CapturedSection,
    field: str,
    diagnostics: list[ConversionDiagnostic] | None,
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
            section.attributes.get("Name"),
            field,
            value,
        )
    return None


def _emit(
    diagnostics: list[ConversionDiagnostic] | None,
    severity: DiagnosticSeverity,
    code: str,
    message: str,
    object_name: str | None,
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
