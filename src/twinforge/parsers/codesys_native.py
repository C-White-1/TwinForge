"""Lossless inventory parser for CODESYS native ``.export`` archives.

The format is an internal, profile-dependent object archive.  TwinForge only
interprets structures for which the archive carries sufficient evidence and
retains the original XML for every parsed object.
"""

from dataclasses import dataclass, field
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .codesys_native_profiles import (
    CodesysNativeProfile,
    codesys_native_profile,
)

_VARIABLE = re.compile(r"\b(?:[A-Za-z_]\w*\.)+[A-Za-z_]\w*\b")


@dataclass(frozen=True)
class CodesysVisualizationAction:
    """A named visualization input action preserved from the archive."""

    kind: str
    properties: dict[str, str] = field(default_factory=dict)
    raw_xml: str = ""


@dataclass(frozen=True)
class CodesysVisualizationElement:
    """One visual element and its evidence-bearing archive representation."""

    element_id: int | None
    identifier: str | None
    element_type: str | None
    properties: dict[str, str]
    property_names: dict[str, str]
    numeric_properties: dict[str, str]
    bindings: tuple[str, ...]
    actions: tuple[CodesysVisualizationAction, ...]
    raw_xml: str


@dataclass(frozen=True)
class CodesysVisualization:
    """A CODESYS visualization object."""

    name: str
    width: int | None
    height: int | None
    elements: tuple[CodesysVisualizationElement, ...]
    raw_xml: str


@dataclass(frozen=True)
class CodesysVisualizationManager:
    """Selected, explicitly named visualization-manager settings."""

    style: str | None
    numpad: str | None
    raw_xml: str


@dataclass(frozen=True)
class CodesysNativeExport:
    """Parsed inventory plus the complete source archive."""

    profile: str | None
    profile_mappings_applied: bool
    visualizations: tuple[CodesysVisualization, ...]
    managers: tuple[CodesysVisualizationManager, ...]
    source_xml: str


class CodesysNativeExportParser:
    """Read a CODESYS native export without pretending it is a stable schema."""

    def parse(self, source: str | bytes | Path) -> CodesysNativeExport:
        """Parse XML text, bytes, or a filesystem path."""
        text = _source_text(source)
        root = ET.fromstring(text)
        profile_name = _named_value(root, "ProfileName")
        profile = codesys_native_profile(profile_name)
        visualizations: list[CodesysVisualization] = []
        managers: list[CodesysVisualizationManager] = []

        for entry in root.findall(".//List2[@Name='EntryList']/Single"):
            meta = entry.find("./Single[@Name='MetaObject']")
            name = _named_value(meta, "Name") if meta is not None else None
            visual_list = entry.find(
                "./Single[@Name='Object']/Single[@Name='VisualElemList']/"
                "List[@Name='VisualElementList']"
            )
            if visual_list is not None and name:
                visualizations.append(
                    _parse_visualization(entry, name, visual_list, profile)
                )
            elif name == "Visualization Manager":
                managers.append(_parse_manager(entry))

        return CodesysNativeExport(
            profile=profile_name,
            profile_mappings_applied=profile is not None,
            visualizations=tuple(visualizations),
            managers=tuple(managers),
            source_xml=text,
        )


def _source_text(source: str | bytes | Path) -> str:
    if isinstance(source, bytes):
        return source.decode("utf-8-sig")
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8-sig")
    if source.lstrip().startswith("<"):
        return source
    return Path(source).read_text(encoding="utf-8-sig")


def _parse_visualization(
    entry: ET.Element,
    name: str,
    visual_list: ET.Element,
    profile: CodesysNativeProfile | None,
) -> CodesysVisualization:
    return CodesysVisualization(
        name=name,
        width=_named_int(entry, "Width"),
        height=_named_int(entry, "Height"),
        elements=tuple(
            _parse_element(item, profile)
            for item in visual_list.findall("./Single")
        ),
        raw_xml=ET.tostring(entry, encoding="unicode"),
    )


def _parse_element(
    item: ET.Element,
    profile: CodesysNativeProfile | None,
) -> CodesysVisualizationElement:
    numeric = _member_values(item)
    member_names = profile.property_names if profile is not None else {}
    properties = {
        friendly: numeric[key]
        for key, friendly in member_names.items()
        if key in numeric
    }
    raw = ET.tostring(item, encoding="unicode")
    bindings = tuple(
        value
        for value in dict.fromkeys(_VARIABLE.findall(raw))
        if not value.startswith(("System.", "VisuDialogs."))
    )
    return CodesysVisualizationElement(
        element_id=_named_int(item, "VisualElementId"),
        identifier=_named_value(item, "VisualElementIdentifier"),
        element_type=_named_value(item, "VisualElementName"),
        properties=properties,
        property_names={
            key: friendly
            for key, friendly in member_names.items()
            if key in numeric
        },
        numeric_properties=numeric,
        bindings=bindings,
        actions=_parse_actions(item),
        raw_xml=raw,
    )


def _parse_actions(item: ET.Element) -> tuple[CodesysVisualizationAction, ...]:
    actions: list[CodesysVisualizationAction] = []
    for node in item.findall(
        "./Array[@Name='ConfiguredComplexInputs']/Single"
    ):
        candidate = _named_value(node, "Name")
        if candidate is None:
            continue
        values = {
            child.get("Name", ""): (child.text or "")
            for child in node.iter()
            if child.get("Name") and child.text is not None
        }
        operand = _configured_action_operand(node)
        if operand is not None:
            values["Operand"] = operand
        actions.append(
            CodesysVisualizationAction(
                kind=candidate,
                properties=values,
                raw_xml=ET.tostring(node, encoding="unicode"),
            )
        )
    for node in item.findall(
        "./Dictionary[@Name='VisualElementInputActions']"
        "/Entry/Value/Array/Single"
    ):
        if _named_value(node, "InputBoxVariable") is None:
            continue
        actions.append(
            CodesysVisualizationAction(
                kind="InputBox",
                properties={
                    child.get("Name", ""): child.text or ""
                    for child in node.findall("./Single")
                    if child.get("Name")
                },
                raw_xml=ET.tostring(node, encoding="unicode"),
            )
        )
    return tuple(actions)


def _configured_action_operand(node: ET.Element) -> str | None:
    member = node.find(
        "./Single[@Name='VisualElemMemberList']/"
        "List[@Name='VisualElemMemberList']/Single/"
        "Single[@Name='Value']"
    )
    if member is None:
        member = node.find("./Single[@Name='Value']")
    return member.text if member is not None else None


def _member_values(node: ET.Element) -> dict[str, str]:
    values: dict[str, str] = {}
    for wrapper in node.findall(
        "./Single[@Name='VisualElemMemberList']/"
        "List[@Name='VisualElemMemberList']/Single"
    ):
        member_id = _named_value(wrapper, "Id")
        value_node = wrapper.find("./*[@Name='Value']")
        value = _member_value(value_node)
        if member_id is not None and value is not None:
            values[member_id] = value
    return values


def _member_value(node: ET.Element | None) -> str | None:
    """Expose scalar or structured member evidence deterministically."""

    if node is None:
        return None
    if not any(
        child.get("Name") is not None
        for child in node.iter()
        if child is not node
    ):
        return node.text or ""
    leaves: list[str] = []

    def visit(current: ET.Element, path: tuple[str, ...]) -> None:
        name = current.get("Name")
        next_path = (*path, name) if name else path
        children = list(current)
        if not children:
            if next_path:
                leaves.append(
                    f"{'.'.join(next_path)}="
                    f"{(current.text or '').strip()}"
                )
            return
        for child in children:
            visit(child, next_path)

    for child in node:
        visit(child, ())
    return "; ".join(leaves)


def _named_value(node: ET.Element, name: str) -> str | None:
    found = node.find(f".//*[@Name='{name}']")
    if found is None:
        return None
    return found.text or ""


def _named_int(node: ET.Element, name: str) -> int | None:
    value = _named_value(node, name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_manager(entry: ET.Element) -> CodesysVisualizationManager:
    return CodesysVisualizationManager(
        style=_named_value(entry, "VisuStyle"),
        numpad=_named_value(entry, "NumpadDialog"),
        raw_xml=ET.tostring(entry, encoding="unicode"),
    )
