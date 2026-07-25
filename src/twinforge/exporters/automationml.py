from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from twinforge.model import Controller, Module, Tag


CAEX_NAMESPACE = "http://www.dke.de/CAEX"
AUTOMATIONML_VERSION = "2.1"
CAEX_SCHEMA_VERSION = "3.0"
AUTOMATIONML_BASE_ALIAS = "AutomationMLBaseLibraries"
TWINFORGE_INTERFACE_LIBRARY = "TwinForgeInterfaceClassLib"
TWINFORGE_ROLE_LIBRARY = "TwinForgeRoleClassLib"
TWINFORGE_ATTRIBUTE_LIBRARY = "TwinForgeAttributeTypeLib"
TWINFORGE_SYSTEM_UNIT_LIBRARY = "TwinForgeSystemUnitClassLib"
ROCKWELL_SYSTEM_UNIT_LIBRARY = "RockwellSystemUnitClassLib"

_BASE_INTERFACE_PATH = (
    f"{AUTOMATIONML_BASE_ALIAS}@AutomationMLInterfaceClassLib/"
    "AutomationMLBaseInterface"
)
_BASE_SIGNAL_PATH = f"{_BASE_INTERFACE_PATH}/Communication/SignalInterface"
_BASE_PLCOPEN_PATH = (
    f"{_BASE_INTERFACE_PATH}/ExternalDataConnector/PLCopenXMLInterface"
)
_BASE_RESOURCE_ROLE_PATH = (
    f"{AUTOMATIONML_BASE_ALIAS}@AutomationMLBaseRoleClassLib/"
    "AutomationMLBaseRole/Resource"
)
_BASE_DIRECTION_TYPE_PATH = (
    f"{AUTOMATIONML_BASE_ALIAS}@AutomationMLBaseAttributeTypeLib/Direction"
)
_BASE_REF_URI_TYPE_PATH = (
    f"{AUTOMATIONML_BASE_ALIAS}@AutomationMLBaseAttributeTypeLib/refURI"
)
_ATTRIBUTE_TYPES = {
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

_ID_NAMESPACE = uuid.UUID("88c16573-13ec-55cb-a5e4-18537fd58938")
_LOCAL_ALIAS = re.compile(
    r"^Local:(?P<slot>\d+):(?P<direction>[IOC])[.:](?P<member>.+)$",
    re.IGNORECASE,
)
_LOCAL_OPERAND = re.compile(
    r"Local:\d+:[IOC][.:][A-Za-z0-9_.]+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AutomationMLExportResult:
    xml: str
    destination: Path | None = None


class AutomationMLValidationError(ValueError):
    pass


class AutomationMLValidationUnavailable(RuntimeError):
    pass


class AutomationMLExporter:
    """Export the current vendor-neutral model as AutomationML 2.1 CAEX."""

    def export(
        self,
        controller: Controller,
        *,
        project_name: str | None = None,
        plcopen_path: str | Path | None = None,
        base_library_path: str | Path | None = None,
        destination: str | Path | None = None,
        last_writing_time: datetime | None = None,
    ) -> AutomationMLExportResult:
        if base_library_path is None:
            raise ValueError(
                "AutomationML 2.1 base_library_path is required"
            )
        name = project_name or controller.name or "TwinForgeProject"
        writing_time = last_writing_time or datetime.now(timezone.utc)
        destination_path = Path(destination) if destination is not None else None
        root = ET.Element(
            _q("CAEXFile"),
            {
                "SchemaVersion": CAEX_SCHEMA_VERSION,
                "FileName": (
                    destination_path.name
                    if destination_path is not None
                    else f"{name}.aml"
                ),
            },
        )
        ET.SubElement(root, _q("SuperiorStandardVersion")).text = (
            f"AutomationML {AUTOMATIONML_VERSION}"
        )
        ET.SubElement(
            root,
            _q("SourceDocumentInformation"),
            {
                "OriginName": "TwinForge",
                "OriginID": str(_id("source", "TwinForge")),
                "OriginVersion": "0.1.0",
                "LastWritingDateTime": writing_time.isoformat(),
                "OriginProjectID": controller.name,
                "OriginProjectTitle": name,
                "OriginVendor": "TwinForge",
            },
        )
        ET.SubElement(
            root,
            _q("ExternalReference"),
            {
                "Alias": AUTOMATIONML_BASE_ALIAS,
                "Path": str(base_library_path).replace("\\", "/"),
            },
        )

        hierarchy = ET.SubElement(
            root,
            _q("InstanceHierarchy"),
            {
                "Name": f"InstanceHierarchy: {name}",
                "ID": str(_id("hierarchy", name)),
            },
        )
        ET.SubElement(hierarchy, _q("Version")).text = "1.0.0"
        system = _internal_element(
            hierarchy,
            name,
            f"system/{name}",
            system_unit_path=(
                f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/AutomationSystem"
            ),
        )
        plc = _internal_element(
            system,
            controller.name or "PLC",
            f"system/{name}/controller/{controller.name}",
            system_unit_path=(
                f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/Controller"
            ),
        )
        _attribute(plc, "AssetType", "PLCController")
        _attribute(plc, "CatalogNumber", controller.identity.product_name)
        if controller.identity.vendor is not None:
            _attribute(plc, "Manufacturer", controller.identity.vendor.name)
        if plcopen_path is not None:
            _attribute(plc, "PLCopenDocument", str(plcopen_path).replace("\\", "/"))
            plcopen_interface = _external_interface(
                plc,
                "PLCopenXML",
                f"system/{name}/controller/{controller.name}/plcopen",
                class_path=_BASE_PLCOPEN_PATH,
            )
            _interface_attribute(
                plcopen_interface,
                "refURI",
                str(plcopen_path).replace("\\", "/"),
                "xs:anyURI",
                _BASE_REF_URI_TYPE_PATH,
            )

        module_interfaces: dict[tuple[int, str], str] = {}
        requested_interfaces: dict[int, dict[str, list[str]]] = {}
        for tag in controller.tags.values():
            target = _alias_target(tag)
            if target is not None:
                requested_interfaces.setdefault(target[0], {}).setdefault(
                    target[1], []
                ).append(tag.name)
        logic_references: dict[int, dict[str, list[str]]] = {}
        for program in controller.iter_programs():
            for routine in program.iter_routines():
                for rung in routine.ladder_rungs:
                    for match in _LOCAL_OPERAND.finditer(rung.text or ""):
                        target = _operand_target(match.group())
                        if target is None:
                            continue
                        reference = (
                            f"{program.name}/{routine.name}/"
                            f"rung {rung.number}"
                        )
                        references = logic_references.setdefault(
                            target[0], {}
                        ).setdefault(target[1], [])
                        if reference not in references:
                            references.append(reference)
        for chassis in controller.iter_chassis():
            chassis_element = _internal_element(
                plc,
                chassis.name,
                f"system/{name}/chassis/{chassis.name}",
                system_unit_path=(
                    f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/Chassis"
                ),
            )
            _attribute(chassis_element, "AssetType", "Chassis")
            for module in chassis.iter_modules():
                self._module(
                    chassis_element,
                    module,
                    f"system/{name}/chassis/{chassis.name}",
                    module_interfaces,
                    controller_catalog=controller.identity.product_name,
                    requested_interfaces=requested_interfaces,
                    logic_references=logic_references,
                )
            _role_requirement(chassis_element, "Chassis")

        signals = _internal_element(
            plc,
            "Signals",
            f"system/{name}/signals",
            system_unit_path=(
                f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/SignalCollection"
            ),
        )
        linked_tags: list[tuple[Tag, tuple[int, str]]] = []
        for tag in controller.tags.values():
            target = _alias_target(tag)
            if target is None:
                continue
            if target in module_interfaces:
                linked_tags.append((tag, target))
        _attribute(
            signals, "LinkedSignalCount", len(linked_tags), "xs:integer"
        )
        for tag, target in linked_tags:
            interface_id = module_interfaces[target]
            signal = _internal_element(
                signals,
                tag.name,
                f"system/{name}/signals/{tag.name}",
                system_unit_path=_signal_system_unit_path(
                    target[1],
                    tag.engineering_unit is not None
                    or tag.engineering_range is not None,
                ),
            )
            asset_type = (
                "AnalogProcessSignal"
                if tag.engineering_unit is not None
                or tag.engineering_range is not None
                else "DigitalSignal"
            )
            _attribute(signal, "AssetType", asset_type)
            _attribute(signal, "TagName", tag.name)
            _attribute(signal, "IOAddress", tag.alias_for)
            if tag.engineering_unit is not None:
                _attribute(
                    signal,
                    "EngineeringUnit",
                    tag.engineering_unit.symbol,
                )
            if tag.engineering_range is not None:
                _attribute(
                    signal,
                    "LowerRangeValue",
                    _number(tag.engineering_range.lower),
                    "xs:double",
                )
                _attribute(
                    signal,
                    "UpperRangeValue",
                    _number(tag.engineering_range.upper),
                    "xs:double",
                )
                _attribute(
                    signal,
                    "RangeSource",
                    tag.engineering_range.source_operand,
                )
            _attribute(signal, "Description", tag.description)
            signal_interface = _external_interface(
                signal,
                "Signal",
                f"system/{name}/signals/{tag.name}/interface",
                class_path=_signal_interface_path(
                    tag.engineering_unit is not None
                    or tag.engineering_range is not None
                ),
            )
            _interface_attribute(
                signal_interface,
                "Direction",
                _opposite_direction(target[1]),
                "xs:string",
                _BASE_DIRECTION_TYPE_PATH,
            )
            ET.SubElement(
                plc,
                _q("InternalLink"),
                {
                    "Name": f"{tag.name}_to_IO",
                    "RefPartnerSideA": signal_interface.attrib["ID"],
                    "RefPartnerSideB": interface_id,
                },
            )
            _role_requirement(signal, asset_type)
        _role_requirement(signals, "SignalCollection")
        _role_requirement(plc, "Controller")
        _role_requirement(system, "AutomationSystem")

        _class_libraries(root, controller)
        ET.indent(root, space="  ")
        ET.register_namespace("", CAEX_NAMESPACE)
        xml = ET.tostring(root, encoding="unicode", xml_declaration=True)
        if destination_path is not None:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.write_text(xml, encoding="utf-8")
        return AutomationMLExportResult(xml=xml, destination=destination_path)

    def _module(
        self,
        parent: ET.Element,
        module: Module,
        path: str,
        interfaces: dict[tuple[int, str], str],
        *,
        controller_catalog: str | None,
        requested_interfaces: dict[int, dict[str, list[str]]],
        logic_references: dict[int, dict[str, list[str]]],
    ) -> None:
        module_path = f"{path}/module/{module.slot}/{module.name}"
        module_class = _module_system_unit_class(
            module, controller_catalog
        )
        element = _internal_element(
            parent,
            module.name,
            module_path,
            system_unit_path=(
                f"{ROCKWELL_SYSTEM_UNIT_LIBRARY}/{module.catalog}"
                if module.catalog
                else f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/{module_class}"
            ),
        )
        asset_type = (
            "Controller"
            if controller_catalog
            and module.catalog.casefold() == controller_catalog.casefold()
            else "IOModule"
        )
        _attribute(element, "AssetType", asset_type)
        _attribute(element, "Slot", module.slot, "xs:integer")
        _attribute(element, "CatalogNumber", module.catalog)
        if module.identity.vendor is not None:
            _attribute(element, "Manufacturer", module.identity.vendor.name)
        if module.capability is not None:
            _attribute(
                element,
                "NominalChannelCount",
                module.capability.nominal_channel_count,
                "xs:integer",
            )
            _attribute(
                element,
                "ConfiguredChannelCount",
                module.capability.configured_channel_count,
                "xs:integer",
            )
            _attribute(
                element,
                "UnavailableByConfigurationCount",
                module.capability.unavailable_by_configuration_count,
                "xs:integer",
            )
            _attribute(
                element,
                "CapabilitySource",
                module.capability.source,
            )
        members: set[str] = set()
        if module.slot is not None:
            members.update(requested_interfaces.get(module.slot, {}))
            members.update(logic_references.get(module.slot, {}))
        if module.capability is None:
            members.update(module.engineering_units)
        elif module.capability.signal_type.value == "Digital":
            direction = (
                "i"
                if module.capability.direction.value == "Input"
                else "o"
            )
            members.update(
                f"{direction}.data.{number}"
                for number in range(
                    module.capability.nominal_channel_count
                )
            )
        elif module.capability.configured_channel_count is not None:
            direction = (
                "i"
                if module.capability.direction.value == "Input"
                else "o"
            )
            members.update(
                f"{direction}.ch{number}data"
                for number in range(
                    module.capability.configured_channel_count
                )
            )
        ordered_members = sorted(members, key=_natural_key)
        for member in ordered_members:
            unit = _member_unit(module, member)
            engineering_range = module.engineering_ranges.get(member)
            signal_type = (
                "Analog"
                if unit is not None or engineering_range is not None
                else "Digital"
            )
            _attribute(element, f"{member}.SignalType", signal_type)
            if unit is not None:
                _attribute(
                    element, f"{member}.EngineeringUnit", unit.symbol
                )
                _attribute(
                    element,
                    f"{member}.SourceOperand",
                    unit.source_operand,
                )
            elif module.slot is not None:
                _attribute(
                    element,
                    f"{member}.SourceOperand",
                    _member_operand(module.slot, member),
                )
            if engineering_range is not None:
                _attribute(
                    element,
                    f"{member}.LowerRangeValue",
                    _number(engineering_range.lower),
                    "xs:double",
                )
                _attribute(
                    element,
                    f"{member}.UpperRangeValue",
                    _number(engineering_range.upper),
                    "xs:double",
                )
            assigned_tags = (
                requested_interfaces.get(module.slot, {}).get(member, [])
                if module.slot is not None
                else []
            )
            direct_references = (
                logic_references.get(module.slot, {}).get(member, [])
                if module.slot is not None
                else []
            )
            if assigned_tags:
                _attribute(
                    element,
                    f"{member}.AssignedTags",
                    ", ".join(sorted(assigned_tags)),
                )
            if direct_references:
                _attribute(
                    element,
                    f"{member}.LogicReferences",
                    ", ".join(sorted(direct_references)),
                )
            if _is_physical_data_member(member):
                _attribute(
                    element,
                    f"{member}.AssignmentStatus",
                    (
                        "Assigned"
                        if assigned_tags or direct_references
                        else "Spare"
                    ),
                )
        for member in ordered_members:
            unit = _member_unit(module, member)
            engineering_range = module.engineering_ranges.get(member)
            interface = _external_interface(
                element,
                member,
                f"{module_path}/interface/{member}",
                class_path=_signal_interface_path(
                    unit is not None or engineering_range is not None
                ),
            )
            _interface_attribute(
                interface,
                "Direction",
                _member_direction(member),
                "xs:string",
                _BASE_DIRECTION_TYPE_PATH,
            )
            if module.slot is not None:
                interfaces[(module.slot, member)] = interface.attrib["ID"]
        for child in module.child_modules:
            self._module(
                element,
                child,
                module_path,
                interfaces,
                controller_catalog=controller_catalog,
                requested_interfaces=requested_interfaces,
                logic_references=logic_references,
            )
        _role_requirement(element, asset_type)


def _internal_element(
    parent: ET.Element,
    name: str,
    identity_path: str,
    *,
    system_unit_path: str | None = None,
) -> ET.Element:
    attributes = {
        "Name": name,
        "ID": str(_id("element", identity_path)),
    }
    if system_unit_path is not None:
        attributes["RefBaseSystemUnitPath"] = system_unit_path
    return ET.SubElement(
        parent,
        _q("InternalElement"),
        attributes,
    )


def _external_interface(
    parent: ET.Element,
    name: str,
    identity_path: str,
    *,
    class_path: str | None = None,
) -> ET.Element:
    interface_id = str(_id("interface", identity_path))
    attributes = {"Name": name, "ID": interface_id}
    if class_path is not None:
        attributes["RefBaseClassPath"] = class_path
    interface = ET.SubElement(
        parent,
        _q("ExternalInterface"),
        attributes,
    )
    return interface


def _attribute(
    parent: ET.Element,
    name: str,
    value: object | None,
    data_type: str = "xs:string",
) -> None:
    if value is None or value == "":
        return
    attributes = {"Name": name, "AttributeDataType": data_type}
    attribute_type = _ATTRIBUTE_TYPES.get(name.rsplit(".", 1)[-1])
    if attribute_type is not None:
        attributes["RefAttributeType"] = (
            f"{TWINFORGE_ATTRIBUTE_LIBRARY}/{attribute_type}"
        )
    attribute = ET.SubElement(
        parent,
        _q("Attribute"),
        attributes,
    )
    ET.SubElement(attribute, _q("Value")).text = str(value)


def _interface_attribute(
    parent: ET.Element,
    name: str,
    value: str,
    data_type: str,
    attribute_type_path: str,
) -> None:
    attribute = ET.SubElement(
        parent,
        _q("Attribute"),
        {
            "Name": name,
            "AttributeDataType": data_type,
            "RefAttributeType": attribute_type_path,
        },
    )
    ET.SubElement(attribute, _q("Value")).text = value


def _role_requirement(parent: ET.Element, role_name: str) -> None:
    ET.SubElement(
        parent,
        _q("RoleRequirements"),
        {
            "RefBaseRoleClassPath": (
                f"{TWINFORGE_ROLE_LIBRARY}/{role_name}"
            )
        },
    )


def _class_libraries(root: ET.Element, controller: Controller) -> None:
    interface_library = ET.SubElement(
        root, _q("InterfaceClassLib"), {"Name": TWINFORGE_INTERFACE_LIBRARY}
    )
    ET.SubElement(interface_library, _q("Description")).text = (
        "TwinForge vendor-neutral automation interfaces"
    )
    ET.SubElement(interface_library, _q("Version")).text = "0.1.0"
    for name in ("AnalogSignalInterface", "DigitalSignalInterface"):
        ET.SubElement(
            interface_library,
            _q("InterfaceClass"),
            {"Name": name, "RefBaseClassPath": _BASE_SIGNAL_PATH},
        )

    role_library = ET.SubElement(
        root, _q("RoleClassLib"), {"Name": TWINFORGE_ROLE_LIBRARY}
    )
    ET.SubElement(role_library, _q("Description")).text = (
        "TwinForge vendor-neutral automation roles"
    )
    ET.SubElement(role_library, _q("Version")).text = "0.1.0"
    for name in (
        "AutomationSystem",
        "Controller",
        "Chassis",
        "IOModule",
        "AnalogProcessSignal",
        "DigitalSignal",
        "SignalCollection",
    ):
        ET.SubElement(
            role_library,
            _q("RoleClass"),
            {"Name": name, "RefBaseClassPath": _BASE_RESOURCE_ROLE_PATH},
        )

    system_unit_library = ET.SubElement(
        root,
        _q("SystemUnitClassLib"),
        {"Name": TWINFORGE_SYSTEM_UNIT_LIBRARY},
    )
    ET.SubElement(system_unit_library, _q("Description")).text = (
        "TwinForge vendor-neutral automation equipment templates"
    )
    ET.SubElement(system_unit_library, _q("Version")).text = "0.1.0"
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
            system_unit_library,
            _q("SystemUnitClass"),
            attributes,
        )
        ET.SubElement(
            system_unit,
            _q("SupportedRoleClass"),
            {
                "RefRoleClassPath": (
                    f"{TWINFORGE_ROLE_LIBRARY}/{role_name}"
                )
            },
        )

    rockwell_library = ET.SubElement(
        root,
        _q("SystemUnitClassLib"),
        {"Name": ROCKWELL_SYSTEM_UNIT_LIBRARY},
    )
    ET.SubElement(rockwell_library, _q("Description")).text = (
        "Rockwell catalog templates captured from the source project"
    )
    ET.SubElement(rockwell_library, _q("Version")).text = "0.1.0"
    catalog_classes: dict[str, tuple[str, str]] = {}
    for chassis in controller.iter_chassis():
        for module in chassis.iter_modules():
            if not module.catalog:
                continue
            class_name = _module_system_unit_class(
                module, controller.identity.product_name
            )
            role_name = (
                "Controller" if class_name == "Controller" else "IOModule"
            )
            catalog_classes[module.catalog] = (class_name, role_name)
    for catalog, (base_name, role_name) in sorted(
        catalog_classes.items(), key=lambda item: _natural_key(item[0])
    ):
        system_unit = ET.SubElement(
            rockwell_library,
            _q("SystemUnitClass"),
            {
                "Name": catalog,
                "RefBaseClassPath": (
                    f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/{base_name}"
                ),
            },
        )
        _attribute(system_unit, "CatalogNumber", catalog)
        ET.SubElement(
            system_unit,
            _q("SupportedRoleClass"),
            {
                "RefRoleClassPath": (
                    f"{TWINFORGE_ROLE_LIBRARY}/{role_name}"
                )
            },
        )

    attribute_library = ET.SubElement(
        root,
        _q("AttributeTypeLib"),
        {"Name": TWINFORGE_ATTRIBUTE_LIBRARY},
    )
    ET.SubElement(attribute_library, _q("Description")).text = (
        "TwinForge automation attribute semantics"
    )
    ET.SubElement(attribute_library, _q("Version")).text = "0.1.0"
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
    }
    for name, data_type in definitions.items():
        ET.SubElement(
            attribute_library,
            _q("AttributeType"),
            {"Name": name, "AttributeDataType": data_type},
        )


def _signal_interface_path(analog: bool) -> str:
    name = "AnalogSignalInterface" if analog else "DigitalSignalInterface"
    return f"{TWINFORGE_INTERFACE_LIBRARY}/{name}"


def _signal_system_unit_path(member: str, analog: bool) -> str:
    direction = _member_direction(member)
    prefix = "Analog" if analog else "Digital"
    suffix = "InputSignal" if direction == "In" else "OutputSignal"
    return f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/{prefix}{suffix}"


def _module_system_unit_class(
    module: Module,
    controller_catalog: str | None,
) -> str:
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


def _member_unit(module: Module, member: str):
    unit = module.engineering_units.get(member)
    if unit is not None:
        return unit
    if member.startswith("o."):
        return module.engineering_units.get(f"i.{member[2:]}")
    return None


def _member_direction(member: str) -> str:
    direction = member.partition(".")[0].casefold()
    if direction == "i":
        return "In"
    if direction == "o":
        return "Out"
    return "InOut"


def _opposite_direction(member: str) -> str:
    direction = _member_direction(member)
    if direction == "In":
        return "Out"
    if direction == "Out":
        return "In"
    return direction


def _alias_target(tag: Tag) -> tuple[int, str] | None:
    if not tag.alias_for:
        return None
    return _operand_target(tag.alias_for)


def _operand_target(operand: str) -> tuple[int, str] | None:
    match = _LOCAL_ALIAS.fullmatch(operand)
    if match is None:
        return None
    member = (
        f"{match.group('direction')}."
        f"{match.group('member').lstrip('.')}"
    ).casefold()
    return int(match.group("slot")), member


def _id(kind: str, name: str) -> uuid.UUID:
    return uuid.uuid5(_ID_NAMESPACE, f"{kind}:{name}")


def _number(value: float) -> str:
    return f"{value:g}"


def _natural_key(value: str) -> tuple[object, ...]:
    return tuple(
        int(part) if part.isdigit() else part.casefold()
        for part in re.split(r"(\d+)", value)
    )


def _member_operand(slot: int, member: str) -> str:
    direction, _, path = member.partition(".")
    data_bit = re.fullmatch(r"data\.(\d+)", path, re.IGNORECASE)
    if data_bit is not None:
        path = f"Data.{data_bit.group(1)}"
    else:
        channel = re.fullmatch(
            r"ch(\d+)(data|fault)", path, re.IGNORECASE
        )
        if channel is not None:
            path = (
                f"Ch{channel.group(1)}"
                f"{channel.group(2).capitalize()}"
            )
    return f"Local:{slot}:{direction.upper()}.{path}"


def _is_physical_data_member(member: str) -> bool:
    _, _, path = member.partition(".")
    return bool(
        re.fullmatch(
            r"(?:data\.\d+|ch\d+data)",
            path,
            re.IGNORECASE,
        )
    )


def validate_automationml_xml(
    xml: str | bytes,
    schema_path: str | Path,
) -> None:
    try:
        import lxml.etree as etree
    except ImportError as error:
        raise AutomationMLValidationUnavailable(
            "CAEX XSD validation requires the optional 'lxml' package"
        ) from error
    schema = etree.XMLSchema(etree.parse(str(schema_path)))
    document = etree.fromstring(
        xml.encode("utf-8") if isinstance(xml, str) else xml
    )
    if not schema.validate(document):
        messages = "; ".join(
            f"line {entry.line}: {entry.message}"
            for entry in schema.error_log
        )
        raise AutomationMLValidationError(messages)


def validate_automationml_references(
    xml: str | bytes,
    document_path: str | Path,
) -> None:
    root = ET.fromstring(
        xml.encode("utf-8") if isinstance(xml, str) else xml
    )
    document = Path(document_path)
    available = _class_paths(root)
    for reference in root.findall(_q("ExternalReference")):
        path = (document.parent / reference.attrib["Path"]).resolve()
        if not path.exists():
            raise AutomationMLValidationError(
                f"external AML reference does not exist: {path}"
            )
        external = ET.parse(path).getroot()
        alias = reference.attrib["Alias"]
        available.update(
            f"{alias}@{class_path}"
            for class_path in _class_paths(external)
        )
    reference_attributes = (
        "RefBaseClassPath",
        "RefBaseRoleClassPath",
        "RefAttributeType",
    )
    unresolved = sorted(
        {
            element.attrib[name]
            for element in root.iter()
            for name in reference_attributes
            if name in element.attrib
            and element.attrib[name] not in available
        }
    )
    if unresolved:
        raise AutomationMLValidationError(
            "unresolved AutomationML class references: "
            + ", ".join(unresolved)
        )
    ids = [element.attrib["ID"] for element in root.iter() if "ID" in element.attrib]
    if len(ids) != len(set(ids)):
        raise AutomationMLValidationError("duplicate CAEX IDs found")
    known_ids = set(ids)
    for link in root.iter(_q("InternalLink")):
        for side in ("RefPartnerSideA", "RefPartnerSideB"):
            if link.attrib.get(side) not in known_ids:
                raise AutomationMLValidationError(
                    f"internal link {link.attrib.get('Name')!r} has "
                    f"unresolved endpoint {link.attrib.get(side)!r}"
                )
    for interface in root.iter(_q("ExternalInterface")):
        if interface.attrib.get("RefBaseClassPath") != _BASE_PLCOPEN_PATH:
            continue
        uri = interface.find(
            f"{_q('Attribute')}[@Name='refURI']/{_q('Value')}"
        )
        if uri is None or not uri.text:
            raise AutomationMLValidationError(
                "PLCopenXMLInterface is missing refURI"
            )
        target = (document.parent / uri.text).resolve()
        if not target.exists():
            raise AutomationMLValidationError(
                f"PLCopen XML reference does not exist: {target}"
            )


def _class_paths(root: ET.Element) -> set[str]:
    paths: set[str] = set()
    specifications = (
        ("InterfaceClassLib", "InterfaceClass"),
        ("RoleClassLib", "RoleClass"),
        ("SystemUnitClassLib", "SystemUnitClass"),
        ("AttributeTypeLib", "AttributeType"),
    )
    for library_name, class_name in specifications:
        for library in root.findall(_q(library_name)):
            prefix = library.attrib["Name"]
            for class_element in library.findall(_q(class_name)):
                _collect_class_paths(
                    class_element, class_name, prefix, paths
                )
    return paths


def _collect_class_paths(
    element: ET.Element,
    class_name: str,
    prefix: str,
    paths: set[str],
) -> None:
    path = f"{prefix}/{element.attrib['Name']}"
    paths.add(path)
    for child in element.findall(_q(class_name)):
        _collect_class_paths(child, class_name, path, paths)


def _q(name: str) -> str:
    return f"{{{CAEX_NAMESPACE}}}{name}"
