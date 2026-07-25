"""Reusable CAEX element primitives independent of hierarchy policy."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from .automationml_identity import deterministic_id
from .automationml_types import (
    CAEX_NAMESPACE,
    TWINFORGE_ATTRIBUTE_LIBRARY,
    TWINFORGE_ROLE_LIBRARY,
)


ATTRIBUTE_TYPES = {
    "AssetType": "AssetType",
    "AssignedTags": "AssignedTags",
    "AssignmentStatus": "AssignmentStatus",
    "CatalogNumber": "CatalogNumber",
    "CapabilitySource": "CapabilitySource",
    "Channel": "ChannelNumber",
    "ConfiguredChannelCount": "Count",
    "Description": "Description",
    "EngineeringUnit": "EngineeringUnit",
    "IOAddress": "IOAddress",
    "LinkedSignalCount": "Count",
    "LogicReferences": "LogicReferences",
    "LowerRangeValue": "RangeValue",
    "Manufacturer": "Manufacturer",
    "NominalChannelCount": "Count",
    "PLCopenDocument": "DocumentURI",
    "RangeSource": "IOAddress",
    "SignalType": "SignalType",
    "Slot": "SlotNumber",
    "SourceOperand": "IOAddress",
    "TagName": "TagName",
    "UpperRangeValue": "RangeValue",
    "UnavailableByConfigurationCount": "Count",
}


def q(name: str) -> str:
    """Return an ElementTree expanded CAEX name."""

    return f"{{{CAEX_NAMESPACE}}}{name}"


def internal_element(
    parent: ET.Element,
    name: str,
    identity_path: str,
    *,
    system_unit_path: str | None = None,
) -> ET.Element:
    """Append an identified CAEX internal element."""

    attributes = {
        "Name": name,
        "ID": str(deterministic_id("element", identity_path)),
    }
    if system_unit_path is not None:
        attributes["RefBaseSystemUnitPath"] = system_unit_path
    return ET.SubElement(parent, q("InternalElement"), attributes)


def external_interface(
    parent: ET.Element,
    name: str,
    identity_path: str,
    *,
    class_path: str | None = None,
) -> ET.Element:
    """Append an identified CAEX external interface."""

    attributes = {
        "Name": name,
        "ID": str(deterministic_id("interface", identity_path)),
    }
    if class_path is not None:
        attributes["RefBaseClassPath"] = class_path
    return ET.SubElement(parent, q("ExternalInterface"), attributes)


def attribute(
    parent: ET.Element,
    name: str,
    value: object | None,
    data_type: str = "xs:string",
) -> None:
    """Append a typed attribute when source evidence provides a value."""

    if value is None or value == "":
        return
    attributes = {"Name": name, "AttributeDataType": data_type}
    attribute_type = ATTRIBUTE_TYPES.get(name.rsplit(".", 1)[-1])
    if attribute_type is not None:
        attributes["RefAttributeType"] = (
            f"{TWINFORGE_ATTRIBUTE_LIBRARY}/{attribute_type}"
        )
    attribute_element = ET.SubElement(
        parent,
        q("Attribute"),
        attributes,
    )
    ET.SubElement(attribute_element, q("Value")).text = str(value)


def interface_attribute(
    parent: ET.Element,
    name: str,
    value: str,
    data_type: str,
    attribute_type_path: str,
) -> None:
    """Append an attribute whose type is defined by an interface library."""

    attribute_element = ET.SubElement(
        parent,
        q("Attribute"),
        {
            "Name": name,
            "AttributeDataType": data_type,
            "RefAttributeType": attribute_type_path,
        },
    )
    ET.SubElement(attribute_element, q("Value")).text = value


def role_requirement(parent: ET.Element, role_name: str) -> None:
    """Assign a TwinForge role to an instance."""

    ET.SubElement(
        parent,
        q("RoleRequirements"),
        {
            "RefBaseRoleClassPath": (
                f"{TWINFORGE_ROLE_LIBRARY}/{role_name}"
            )
        },
    )
