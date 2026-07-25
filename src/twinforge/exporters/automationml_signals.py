"""Generate module I/O interfaces, process signals, and their CAEX links."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from twinforge.model import Controller, EngineeringUnitEvidence, Module, Tag

from .automationml_class_libraries import module_system_unit_class
from .automationml_elements import (
    attribute,
    external_interface,
    interface_attribute,
    internal_element,
    q,
    role_requirement,
)
from .automationml_types import (
    BASE_DIRECTION_TYPE_PATH,
    ROCKWELL_SYSTEM_UNIT_LIBRARY,
    TWINFORGE_INTERFACE_LIBRARY,
    TWINFORGE_SYSTEM_UNIT_LIBRARY,
)


_LOCAL_ADDRESS = re.compile(
    r"^Local:(?P<slot>\d+):(?P<direction>[IOC])[.:](?P<member>.+)$",
    re.IGNORECASE,
)
_LOCAL_OPERAND = re.compile(
    r"Local:\d+:[IOC][.:][A-Za-z0-9_.]+",
    re.IGNORECASE,
)


class SignalIOBuilder:
    """Build signal and I/O content from resolved controller evidence."""

    def __init__(self, controller: Controller, system_name: str) -> None:
        self.controller = controller
        self.system_name = system_name
        self.module_interfaces: dict[tuple[int, str], str] = {}
        self.requested_interfaces = self._requested_interfaces()
        self.logic_references = self._logic_references()

    def append_module(
        self,
        parent: ET.Element,
        module: Module,
        path: str,
    ) -> None:
        """Append a module, its evidenced point population, and child modules."""

        module_path = f"{path}/module/{module.slot}/{module.name}"
        module_class = module_system_unit_class(
            module,
            self.controller.identity.product_name,
        )
        element = internal_element(
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
            "Controller" if module_class == "Controller" else "IOModule"
        )
        attribute(element, "AssetType", asset_type)
        attribute(element, "Slot", module.slot, "xs:integer")
        attribute(element, "CatalogNumber", module.catalog)
        if module.identity.vendor is not None:
            attribute(element, "Manufacturer", module.identity.vendor.name)
        self._append_capability_attributes(element, module)

        members = self._module_members(module)
        for member in members:
            self._append_member_attributes(element, module, member)
        for member in members:
            self._append_member_interface(
                element,
                module,
                member,
                module_path,
            )
        for child in module.child_modules:
            self.append_module(element, child, module_path)
        role_requirement(element, asset_type)

    def append_signals(self, plc: ET.Element) -> None:
        """Append alias-backed signals and link them to module interfaces."""

        name = self.system_name
        signals = internal_element(
            plc,
            "Signals",
            f"system/{name}/signals",
            system_unit_path=(
                f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/SignalCollection"
            ),
        )
        linked_tags: list[tuple[Tag, tuple[int, str]]] = []
        for tag in self.controller.tags.values():
            target = alias_target(tag)
            if target is not None and target in self.module_interfaces:
                linked_tags.append((tag, target))
        attribute(
            signals,
            "LinkedSignalCount",
            len(linked_tags),
            "xs:integer",
        )
        for tag, target in linked_tags:
            self._append_signal(plc, signals, tag, target)
        role_requirement(signals, "SignalCollection")

    def _append_signal(
        self,
        plc: ET.Element,
        signals: ET.Element,
        tag: Tag,
        target: tuple[int, str],
    ) -> None:
        name = self.system_name
        analog = (
            tag.engineering_unit is not None
            or tag.engineering_range is not None
        )
        signal = internal_element(
            signals,
            tag.name,
            f"system/{name}/signals/{tag.name}",
            system_unit_path=signal_system_unit_path(target[1], analog),
        )
        asset_type = "AnalogProcessSignal" if analog else "DigitalSignal"
        attribute(signal, "AssetType", asset_type)
        attribute(signal, "TagName", tag.name)
        attribute(signal, "IOAddress", tag.alias_for)
        if tag.engineering_unit is not None:
            attribute(
                signal,
                "EngineeringUnit",
                tag.engineering_unit.symbol,
            )
        if tag.engineering_range is not None:
            attribute(
                signal,
                "LowerRangeValue",
                number(tag.engineering_range.lower),
                "xs:double",
            )
            attribute(
                signal,
                "UpperRangeValue",
                number(tag.engineering_range.upper),
                "xs:double",
            )
            attribute(
                signal,
                "RangeSource",
                tag.engineering_range.source_operand,
            )
        attribute(signal, "Description", tag.description)
        signal_interface = external_interface(
            signal,
            "Signal",
            f"system/{name}/signals/{tag.name}/interface",
            class_path=signal_interface_path(analog),
        )
        interface_attribute(
            signal_interface,
            "Direction",
            opposite_direction(target[1]),
            "xs:string",
            BASE_DIRECTION_TYPE_PATH,
        )
        ET.SubElement(
            plc,
            q("InternalLink"),
            {
                "Name": f"{tag.name}_to_IO",
                "RefPartnerSideA": signal_interface.attrib["ID"],
                "RefPartnerSideB": self.module_interfaces[target],
            },
        )
        role_requirement(signal, asset_type)

    def _append_capability_attributes(
        self,
        element: ET.Element,
        module: Module,
    ) -> None:
        capability = module.capability
        if capability is None:
            return
        attribute(
            element,
            "NominalChannelCount",
            capability.nominal_channel_count,
            "xs:integer",
        )
        attribute(
            element,
            "ConfiguredChannelCount",
            capability.configured_channel_count,
            "xs:integer",
        )
        attribute(
            element,
            "UnavailableByConfigurationCount",
            capability.unavailable_by_configuration_count,
            "xs:integer",
        )
        attribute(element, "CapabilitySource", capability.source)

    def _module_members(self, module: Module) -> list[str]:
        members: set[str] = set()
        if module.slot is not None:
            members.update(self.requested_interfaces.get(module.slot, {}))
            members.update(self.logic_references.get(module.slot, {}))
        if module.capability is None:
            members.update(module.engineering_units)
        elif module.capability.signal_type.value == "Digital":
            direction = (
                "i"
                if module.capability.direction.value == "Input"
                else "o"
            )
            members.update(
                f"{direction}.data.{index}"
                for index in range(
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
                f"{direction}.ch{index}data"
                for index in range(
                    module.capability.configured_channel_count
                )
            )
        return sorted(members, key=natural_key)

    def _append_member_attributes(
        self,
        element: ET.Element,
        module: Module,
        member: str,
    ) -> None:
        unit = member_unit(module, member)
        engineering_range = module.engineering_ranges.get(member)
        signal_type = (
            "Analog"
            if unit is not None or engineering_range is not None
            else "Digital"
        )
        attribute(element, f"{member}.SignalType", signal_type)
        if unit is not None:
            attribute(element, f"{member}.EngineeringUnit", unit.symbol)
            attribute(
                element,
                f"{member}.SourceOperand",
                unit.source_operand,
            )
        elif module.slot is not None:
            attribute(
                element,
                f"{member}.SourceOperand",
                member_operand(module.slot, member),
            )
        if engineering_range is not None:
            attribute(
                element,
                f"{member}.LowerRangeValue",
                number(engineering_range.lower),
                "xs:double",
            )
            attribute(
                element,
                f"{member}.UpperRangeValue",
                number(engineering_range.upper),
                "xs:double",
            )
        assigned_tags, direct_references = self._member_assignments(
            module,
            member,
        )
        if assigned_tags:
            attribute(
                element,
                f"{member}.AssignedTags",
                ", ".join(sorted(assigned_tags)),
            )
        if direct_references:
            attribute(
                element,
                f"{member}.LogicReferences",
                ", ".join(sorted(direct_references)),
            )
        if is_physical_data_member(member):
            attribute(
                element,
                f"{member}.AssignmentStatus",
                (
                    "Assigned"
                    if assigned_tags or direct_references
                    else "Spare"
                ),
            )

    def _append_member_interface(
        self,
        element: ET.Element,
        module: Module,
        member: str,
        module_path: str,
    ) -> None:
        unit = member_unit(module, member)
        engineering_range = module.engineering_ranges.get(member)
        interface = external_interface(
            element,
            member,
            f"{module_path}/interface/{member}",
            class_path=signal_interface_path(
                unit is not None or engineering_range is not None
            ),
        )
        interface_attribute(
            interface,
            "Direction",
            member_direction(member),
            "xs:string",
            BASE_DIRECTION_TYPE_PATH,
        )
        if module.slot is not None:
            self.module_interfaces[(module.slot, member)] = (
                interface.attrib["ID"]
            )

    def _member_assignments(
        self,
        module: Module,
        member: str,
    ) -> tuple[list[str], list[str]]:
        if module.slot is None:
            return [], []
        return (
            self.requested_interfaces.get(module.slot, {}).get(member, []),
            self.logic_references.get(module.slot, {}).get(member, []),
        )

    def _requested_interfaces(self) -> dict[int, dict[str, list[str]]]:
        requested: dict[int, dict[str, list[str]]] = {}
        for tag in self.controller.tags.values():
            target = alias_target(tag)
            if target is not None:
                requested.setdefault(target[0], {}).setdefault(
                    target[1],
                    [],
                ).append(tag.name)
        return requested

    def _logic_references(self) -> dict[int, dict[str, list[str]]]:
        references_by_slot: dict[int, dict[str, list[str]]] = {}
        for program in self.controller.iter_programs():
            for routine in program.iter_routines():
                for rung in routine.ladder_rungs:
                    for match in _LOCAL_OPERAND.finditer(rung.text or ""):
                        target = operand_target(match.group())
                        if target is None:
                            continue
                        reference = (
                            f"{program.name}/{routine.name}/"
                            f"rung {rung.number}"
                        )
                        references = references_by_slot.setdefault(
                            target[0],
                            {},
                        ).setdefault(target[1], [])
                        if reference not in references:
                            references.append(reference)
        return references_by_slot


def signal_interface_path(analog: bool) -> str:
    """Return the TwinForge interface class for a signal category."""

    name = "AnalogSignalInterface" if analog else "DigitalSignalInterface"
    return f"{TWINFORGE_INTERFACE_LIBRARY}/{name}"


def signal_system_unit_path(member: str, analog: bool) -> str:
    """Return the directional signal SystemUnitClass path."""

    direction = member_direction(member)
    prefix = "Analog" if analog else "Digital"
    suffix = "InputSignal" if direction == "In" else "OutputSignal"
    return f"{TWINFORGE_SYSTEM_UNIT_LIBRARY}/{prefix}{suffix}"


def member_unit(
    module: Module,
    member: str,
) -> EngineeringUnitEvidence | None:
    """Resolve explicit unit evidence, including Rockwell output mirroring."""

    unit = module.engineering_units.get(member)
    if unit is not None:
        return unit
    if member.startswith("o."):
        return module.engineering_units.get(f"i.{member[2:]}")
    return None


def member_direction(member: str) -> str:
    """Map an L5X member prefix to an AutomationML direction."""

    direction = member.partition(".")[0].casefold()
    if direction == "i":
        return "In"
    if direction == "o":
        return "Out"
    return "InOut"


def opposite_direction(member: str) -> str:
    """Return the process-signal side opposite a module interface."""

    direction = member_direction(member)
    if direction == "In":
        return "Out"
    if direction == "Out":
        return "In"
    return direction


def alias_target(tag: Tag) -> tuple[int, str] | None:
    """Resolve an alias tag to a normalized local slot/member tuple."""

    return operand_target(tag.alias_for) if tag.alias_for else None


def operand_target(operand: str) -> tuple[int, str] | None:
    """Resolve a Rockwell local I/O operand without inventing a mapping."""

    match = _LOCAL_ADDRESS.fullmatch(operand)
    if match is None:
        return None
    member = (
        f"{match.group('direction')}."
        f"{match.group('member').lstrip('.')}"
    ).casefold()
    return int(match.group("slot")), member


def number(value: float) -> str:
    """Format a numeric CAEX value deterministically."""

    return f"{value:g}"


def natural_key(value: str) -> tuple[object, ...]:
    """Sort channel names numerically rather than lexicographically."""

    return tuple(
        int(part) if part.isdigit() else part.casefold()
        for part in re.split(r"(\d+)", value)
    )


def member_operand(slot: int, member: str) -> str:
    """Reconstruct the canonical Rockwell operand represented by a member."""

    direction, _, path = member.partition(".")
    data_bit = re.fullmatch(r"data\.(\d+)", path, re.IGNORECASE)
    if data_bit is not None:
        path = f"Data.{data_bit.group(1)}"
    else:
        channel = re.fullmatch(
            r"ch(\d+)(data|fault)",
            path,
            re.IGNORECASE,
        )
        if channel is not None:
            path = (
                f"Ch{channel.group(1)}"
                f"{channel.group(2).capitalize()}"
            )
    return f"Local:{slot}:{direction.upper()}.{path}"


def is_physical_data_member(member: str) -> bool:
    """Return whether a member represents an assignable physical data point."""

    _, _, path = member.partition(".")
    return bool(
        re.fullmatch(
            r"(?:data\.\d+|ch\d+data)",
            path,
            re.IGNORECASE,
        )
    )
