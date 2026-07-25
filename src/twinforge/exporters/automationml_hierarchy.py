"""Construct the AutomationML CAEX document and instance hierarchy."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from twinforge.model import Controller

from .automationml_class_libraries import append_class_libraries
from .automationml_elements import (
    attribute,
    external_interface,
    interface_attribute,
    internal_element,
    q,
    role_requirement,
)
from .automationml_identity import deterministic_id
from .automationml_signals import SignalIOBuilder
from .automationml_types import (
    AUTOMATIONML_BASE_ALIAS,
    AUTOMATIONML_VERSION,
    BASE_PLCOPEN_PATH,
    BASE_REF_URI_TYPE_PATH,
    CAEX_SCHEMA_VERSION,
    TWINFORGE_SYSTEM_UNIT_LIBRARY,
)


def build_automationml_document(
    controller: Controller,
    *,
    project_name: str,
    file_name: str,
    plcopen_path: str | Path | None,
    base_library_path: str | Path,
    last_writing_time: datetime,
) -> ET.Element:
    """Build a complete CAEX tree without serialization or filesystem writes."""

    root = _document_root(
        controller,
        project_name=project_name,
        file_name=file_name,
        base_library_path=base_library_path,
        last_writing_time=last_writing_time,
    )
    _append_instance_hierarchy(
        root,
        controller,
        project_name=project_name,
        plcopen_path=plcopen_path,
    )
    append_class_libraries(root, controller)
    return root


def _document_root(
    controller: Controller,
    *,
    project_name: str,
    file_name: str,
    base_library_path: str | Path,
    last_writing_time: datetime,
) -> ET.Element:
    root = ET.Element(
        q("CAEXFile"),
        {
            "SchemaVersion": CAEX_SCHEMA_VERSION,
            "FileName": file_name,
        },
    )
    ET.SubElement(root, q("SuperiorStandardVersion")).text = (
        f"AutomationML {AUTOMATIONML_VERSION}"
    )
    ET.SubElement(
        root,
        q("SourceDocumentInformation"),
        {
            "OriginName": "TwinForge",
            "OriginID": str(deterministic_id("source", "TwinForge")),
            "OriginVersion": "0.1.0",
            "LastWritingDateTime": last_writing_time.isoformat(),
            "OriginProjectID": controller.name,
            "OriginProjectTitle": project_name,
            "OriginVendor": "TwinForge",
        },
    )
    ET.SubElement(
        root,
        q("ExternalReference"),
        {
            "Alias": AUTOMATIONML_BASE_ALIAS,
            "Path": str(base_library_path).replace("\\", "/"),
        },
    )
    return root


def _append_instance_hierarchy(
    root: ET.Element,
    controller: Controller,
    *,
    project_name: str,
    plcopen_path: str | Path | None,
) -> None:
    hierarchy = ET.SubElement(
        root,
        q("InstanceHierarchy"),
        {
            "Name": f"InstanceHierarchy: {project_name}",
            "ID": str(deterministic_id("hierarchy", project_name)),
        },
    )
    ET.SubElement(hierarchy, q("Version")).text = "1.0.0"
    system = internal_element(
        hierarchy,
        project_name,
        f"system/{project_name}",
        system_unit_path=(
            f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/AutomationSystem"
        ),
    )
    plc = internal_element(
        system,
        controller.name or "PLC",
        f"system/{project_name}/controller/{controller.name}",
        system_unit_path=f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/Controller",
    )
    attribute(plc, "AssetType", "PLCController")
    attribute(plc, "CatalogNumber", controller.identity.product_name)
    if controller.identity.vendor is not None:
        attribute(plc, "Manufacturer", controller.identity.vendor.name)
    if plcopen_path is not None:
        normalized_path = str(plcopen_path).replace("\\", "/")
        attribute(plc, "PLCopenDocument", normalized_path)
        plcopen_interface = external_interface(
            plc,
            "PLCopenXML",
            (
                f"system/{project_name}/controller/"
                f"{controller.name}/plcopen"
            ),
            class_path=BASE_PLCOPEN_PATH,
        )
        interface_attribute(
            plcopen_interface,
            "refURI",
            normalized_path,
            "xs:anyURI",
            BASE_REF_URI_TYPE_PATH,
        )

    signals = SignalIOBuilder(controller, project_name)
    for chassis in controller.iter_chassis():
        chassis_element = internal_element(
            plc,
            chassis.name,
            f"system/{project_name}/chassis/{chassis.name}",
            system_unit_path=f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/Chassis",
        )
        attribute(chassis_element, "AssetType", "Chassis")
        chassis_path = f"system/{project_name}/chassis/{chassis.name}"
        for module in chassis.iter_modules():
            signals.append_module(chassis_element, module, chassis_path)
        role_requirement(chassis_element, "Chassis")

    signals.append_signals(plc)
    role_requirement(plc, "Controller")
    role_requirement(system, "AutomationSystem")
