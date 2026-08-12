"""Generate AutomationML role, interface, system-unit, and attribute libraries."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from twinforge.model import Controller, Module

from .automationml_elements import attribute, q
from .automationml_types import (
    BASE_RESOURCE_ROLE_PATH,
    BASE_SIGNAL_PATH,
    ROCKWELL_SYSTEM_UNIT_LIBRARY,
    TWINFORGE_ATTRIBUTE_LIBRARY,
    TWINFORGE_INTERFACE_LIBRARY,
    TWINFORGE_ROLE_LIBRARY,
    TWINFORGE_SYSTEM_UNIT_LIBRARY,
)


def append_class_libraries(
    root: ET.Element,
    controller: Controller,
) -> None:
    """Append all class libraries required by generated TwinForge instances."""

    _append_interface_library(root)
    _append_role_library(root)
    _append_system_unit_library(root)
    _append_catalog_library(root, controller)
    _append_attribute_library(root)


def module_system_unit_class(
    module: Module,
    controller_catalog: str | None,
) -> str:
    """Choose the vendor-neutral base class supported by module evidence."""

    if (
        controller_catalog
        and module.catalog.casefold() == controller_catalog.casefold()
    ):
        return "Controller"
    connection_types = {
        (connection.connection_type or "").casefold()
        for connection in module.connections
    }
    analog = bool(module.engineering_units or module.engineering_ranges)
    if connection_types == {"input"}:
        return "AnalogInputModule" if analog else "DigitalInputModule"
    if connection_types == {"output"}:
        return "AnalogOutputModule" if analog else "DigitalOutputModule"
    return "IOModule"


def _append_interface_library(root: ET.Element) -> None:
    library = ET.SubElement(
        root,
        q("InterfaceClassLib"),
        {"Name": TWINFORGE_INTERFACE_LIBRARY},
    )
    ET.SubElement(library, q("Description")).text = (
        "TwinForge vendor-neutral automation interfaces"
    )
    ET.SubElement(library, q("Version")).text = "0.1.0"
    for name in (
        "AnalogSignalInterface",
        "DigitalSignalInterface",
        "CommunicationPointInterface",
    ):
        ET.SubElement(
            library,
            q("InterfaceClass"),
            {"Name": name, "RefBaseClassPath": BASE_SIGNAL_PATH},
        )


def _append_role_library(root: ET.Element) -> None:
    library = ET.SubElement(
        root,
        q("RoleClassLib"),
        {"Name": TWINFORGE_ROLE_LIBRARY},
    )
    ET.SubElement(library, q("Description")).text = (
        "TwinForge vendor-neutral automation roles"
    )
    ET.SubElement(library, q("Version")).text = "0.1.0"
    for name in (
        "AutomationSystem",
        "Controller",
        "Chassis",
        "IOModule",
        "AnalogProcessSignal",
        "DigitalSignal",
        "SignalCollection",
        "CommunicationGateway",
    ):
        ET.SubElement(
            library,
            q("RoleClass"),
            {"Name": name, "RefBaseClassPath": BASE_RESOURCE_ROLE_PATH},
        )


def _append_system_unit_library(root: ET.Element) -> None:
    library = ET.SubElement(
        root,
        q("SystemUnitClassLib"),
        {"Name": TWINFORGE_SYSTEM_UNIT_LIBRARY},
    )
    ET.SubElement(library, q("Description")).text = (
        "TwinForge vendor-neutral automation equipment templates"
    )
    ET.SubElement(library, q("Version")).text = "0.1.0"
    system_units = {
        "AutomationSystem": (None, "AutomationSystem"),
        "Controller": (None, "Controller"),
        "Chassis": (None, "Chassis"),
        "IOModule": (None, "IOModule"),
        "DigitalInputModule": ("IOModule", "IOModule"),
        "DigitalOutputModule": ("IOModule", "IOModule"),
        "AnalogInputModule": ("IOModule", "IOModule"),
        "AnalogOutputModule": ("IOModule", "IOModule"),
        "SignalCollection": (None, "SignalCollection"),
        "CommunicationGateway": (None, "CommunicationGateway"),
        "ProcessSignal": (None, "DigitalSignal"),
        "DigitalInputSignal": ("ProcessSignal", "DigitalSignal"),
        "DigitalOutputSignal": ("ProcessSignal", "DigitalSignal"),
        "AnalogInputSignal": ("ProcessSignal", "AnalogProcessSignal"),
        "AnalogOutputSignal": ("ProcessSignal", "AnalogProcessSignal"),
    }
    for class_name, (base_name, role_name) in system_units.items():
        attributes = {"Name": class_name}
        if base_name is not None:
            attributes["RefBaseClassPath"] = (
                f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/{base_name}"
            )
        system_unit = ET.SubElement(
            library,
            q("SystemUnitClass"),
            attributes,
        )
        ET.SubElement(
            system_unit,
            q("SupportedRoleClass"),
            {
                "RefRoleClassPath": (
                    f"{TWINFORGE_ROLE_LIBRARY}/{role_name}"
                )
            },
        )


def _append_catalog_library(
    root: ET.Element,
    controller: Controller,
) -> None:
    library = ET.SubElement(
        root,
        q("SystemUnitClassLib"),
        {"Name": ROCKWELL_SYSTEM_UNIT_LIBRARY},
    )
    ET.SubElement(library, q("Description")).text = (
        "Rockwell catalog templates captured from the source project"
    )
    ET.SubElement(library, q("Version")).text = "0.1.0"
    catalog_classes: dict[str, tuple[str, str]] = {}
    for chassis in controller.iter_chassis():
        for module in chassis.iter_modules():
            if not module.catalog:
                continue
            class_name = module_system_unit_class(
                module,
                controller.identity.product_name,
            )
            role_name = (
                "Controller" if class_name == "Controller" else "IOModule"
            )
            catalog_classes[module.catalog] = (class_name, role_name)
    for catalog, (base_name, role_name) in sorted(
        catalog_classes.items(),
        key=lambda item: _natural_key(item[0]),
    ):
        system_unit = ET.SubElement(
            library,
            q("SystemUnitClass"),
            {
                "Name": catalog,
                "RefBaseClassPath": (
                    f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/{base_name}"
                ),
            },
        )
        attribute(system_unit, "CatalogNumber", catalog)
        ET.SubElement(
            system_unit,
            q("SupportedRoleClass"),
            {
                "RefRoleClassPath": (
                    f"{TWINFORGE_ROLE_LIBRARY}/{role_name}"
                )
            },
        )


def _append_attribute_library(root: ET.Element) -> None:
    library = ET.SubElement(
        root,
        q("AttributeTypeLib"),
        {"Name": TWINFORGE_ATTRIBUTE_LIBRARY},
    )
    ET.SubElement(library, q("Description")).text = (
        "TwinForge automation attribute semantics"
    )
    ET.SubElement(library, q("Version")).text = "0.1.0"
    definitions = {
        "AssetType": "xs:string",
        "AssignedTags": "xs:string",
        "AssignmentStatus": "xs:string",
        "CapabilitySource": "xs:string",
        "CatalogNumber": "xs:string",
        "ChannelNumber": "xs:integer",
        "Count": "xs:integer",
        "Description": "xs:string",
        "DocumentURI": "xs:anyURI",
        "EngineeringUnit": "xs:string",
        "IOAddress": "xs:string",
        "LogicReferences": "xs:string",
        "Manufacturer": "xs:string",
        "RangeValue": "xs:double",
        "SignalType": "xs:string",
        "SlotNumber": "xs:integer",
        "TagName": "xs:string",
        "Protocol": "xs:string",
        "EndpointReference": "xs:string",
        "TagPath": "xs:string",
        "BindingEvidence": "xs:string",
    }
    for name, data_type in definitions.items():
        ET.SubElement(
            library,
            q("AttributeType"),
            {"Name": name, "AttributeDataType": data_type},
        )


def _natural_key(value: str) -> tuple[object, ...]:
    return tuple(
        int(part) if part.isdigit() else part.casefold()
        for part in re.split(r"(\d+)", value)
    )
