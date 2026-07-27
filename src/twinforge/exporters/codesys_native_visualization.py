"""Source-backed export of neutral visualizations to CODESYS native XML."""

from dataclasses import dataclass
import xml.etree.ElementTree as ET

from twinforge.converters.codesys_visualization import (
    convert_codesys_visualization,
)
from twinforge.model import (
    SourceNode,
    VisualizationBindingRole,
    VisualizationControl,
    VisualizationDocument,
    VisualizationInteraction,
    VisualizationInteractionKind,
)
from twinforge.parsers.codesys_native import CodesysNativeExportParser
from twinforge.parsers.codesys_native_profiles import codesys_native_profile


class CodesysNativeVisualizationExportError(ValueError):
    """Raised when a requested native mutation is not evidence-supported."""


@dataclass(frozen=True)
class CodesysNativeVisualizationExportResult:
    """A generated native archive and its exact target profile."""

    xml: str
    profile: str


class CodesysNativeVisualizationExporter:
    """Update verified fields in a captured CODESYS native archive."""

    def export(
        self,
        document: VisualizationDocument,
    ) -> CodesysNativeVisualizationExportResult:
        """Export a source-backed document or reject unsafe synthesis."""
        root = _source_root(document)
        source_xml = ET.tostring(root, encoding="unicode")
        parsed = CodesysNativeExportParser().parse(source_xml)
        profile = codesys_native_profile(parsed.profile)
        if profile is None:
            raise CodesysNativeVisualizationExportError(
                "native export requires an exact verified CODESYS profile"
            )
        original = convert_codesys_visualization(parsed)
        _validate_shape(original, document)
        _set_named_value(root, "VisuStyle", document.theme)

        reverse_names = {
            name: property_id
            for property_id, name in profile.property_names.items()
        }
        for new_canvas, old_canvas in zip(
            document.canvases,
            original.canvases,
            strict=True,
        ):
            entry = _visualization_entry(root, new_canvas.name)
            items = _visual_items(entry)
            by_identifier = {
                _named_value(item, "VisualElementIdentifier"): item
                for item in items
            }
            old_controls = {
                control.identifier: control
                for control in old_canvas.controls
            }
            for control in new_canvas.controls:
                item = by_identifier.get(control.identifier)
                if item is None:
                    raise CodesysNativeVisualizationExportError(
                        f"source control not found: {control.identifier}"
                    )
                _update_control(
                    item,
                    old_controls[control.identifier],
                    control,
                    reverse_names,
                )

        xml = ET.tostring(root, encoding="unicode")
        ET.fromstring(xml)
        return CodesysNativeVisualizationExportResult(
            xml=xml,
            profile=profile.name,
        )


def _source_root(document: VisualizationDocument) -> ET.Element:
    extension = next(
        (
            extension
            for extension in document.source_extensions
            if extension.format == "codesys-native"
            and extension.root.name == "ExportFile"
        ),
        None,
    )
    if extension is None:
        raise CodesysNativeVisualizationExportError(
            "native export requires a retained CODESYS ExportFile source"
        )
    return _element(extension.root)


def _validate_shape(
    original: VisualizationDocument,
    requested: VisualizationDocument,
) -> None:
    if len(original.canvases) != len(requested.canvases):
        raise CodesysNativeVisualizationExportError(
            "adding or removing native canvases is not supported"
        )
    for old, new in zip(original.canvases, requested.canvases, strict=True):
        if old.name != new.name:
            raise CodesysNativeVisualizationExportError(
                "renaming native canvases is not supported"
            )
        if (old.width, old.height) != (new.width, new.height):
            raise CodesysNativeVisualizationExportError(
                "changing native canvas size is not yet supported"
            )
        old_ids = [control.identifier for control in old.controls]
        new_ids = [control.identifier for control in new.controls]
        if old_ids != new_ids:
            raise CodesysNativeVisualizationExportError(
                "adding, removing, reordering, or renaming controls "
                "is not supported"
            )


def _update_control(
    item: ET.Element,
    old: VisualizationControl,
    new: VisualizationControl,
    property_ids: dict[str, str],
) -> None:
    if old.kind is not new.kind or old.source_type != new.source_type:
        raise CodesysNativeVisualizationExportError(
            f"changing control type is not supported: {new.identifier}"
        )
    values = {
        "x": new.geometry.x,
        "y": new.geometry.y,
        "width": new.geometry.width,
        "height": new.geometry.height,
        "text": new.text or "",
    }
    for name, value in values.items():
        if value is None:
            raise CodesysNativeVisualizationExportError(
                f"{new.identifier} requires verified {name} evidence"
            )
        _set_member(item, property_ids[name], str(value))
    x = new.geometry.x
    y = new.geometry.y
    width = new.geometry.width
    height = new.geometry.height
    if x is None or y is None or width is None or height is None:
        raise CodesysNativeVisualizationExportError(
            f"{new.identifier} requires complete verified geometry"
        )
    center_x = x + width // 2
    center_y = y + height // 2
    _set_member(item, property_ids["center_x"], str(center_x))
    _set_member(item, property_ids["center_y"], str(center_y))

    if len(old.interactions) != len(new.interactions):
        raise CodesysNativeVisualizationExportError(
            "adding or removing interactions is not yet supported"
        )
    for old_action, new_action in zip(
        old.interactions,
        new.interactions,
        strict=True,
    ):
        if old_action.kind is not new_action.kind:
            raise CodesysNativeVisualizationExportError(
                "changing interaction kind is not yet supported"
            )
        _update_interaction(item, new_action)
    _validate_bindings(old, new)


def _update_interaction(
    item: ET.Element,
    interaction: VisualizationInteraction,
) -> None:
    if interaction.kind is VisualizationInteractionKind.TOGGLE:
        action = _configured_action(item, "Toggle")
        _set_action_member(action, interaction.operand)
        return
    if interaction.kind is VisualizationInteractionKind.VALUE_INPUT:
        action = _input_box_action(item)
        values = {
            "InputBoxVariable": interaction.operand,
            "Format": interaction.value_format,
            "InputBoxMin": interaction.minimum,
            "InputBoxMax": interaction.maximum,
            "InputBoxDialogTitle": interaction.prompt,
        }
        for name, value in values.items():
            _set_direct_named_value(action, name, value)
        return
    raise CodesysNativeVisualizationExportError(
        "unknown interactions cannot be generated"
    )


def _validate_bindings(
    old: VisualizationControl,
    new: VisualizationControl,
) -> None:
    old_values = {
        binding.expression
        for binding in old.bindings
        if binding.role is VisualizationBindingRole.VALUE
    }
    new_values = {
        binding.expression
        for binding in new.bindings
        if binding.role is VisualizationBindingRole.VALUE
    }
    if old_values != new_values:
        raise CodesysNativeVisualizationExportError(
            "changing display/value bindings is not yet supported"
        )
    action_operands = {
        interaction.operand
        for interaction in new.interactions
        if interaction.operand is not None
    }
    requested_action_bindings = {
        binding.expression
        for binding in new.bindings
        if binding.role is not VisualizationBindingRole.VALUE
    }
    if requested_action_bindings != action_operands:
        raise CodesysNativeVisualizationExportError(
            "command/input bindings must match interaction operands"
        )


def _visualization_entry(root: ET.Element, name: str) -> ET.Element:
    for entry in root.findall(".//List2[@Name='EntryList']/Single"):
        meta = entry.find("./Single[@Name='MetaObject']")
        if meta is not None and _named_value(meta, "Name") == name:
            return entry
    raise CodesysNativeVisualizationExportError(
        f"source visualization not found: {name}"
    )


def _visual_items(entry: ET.Element) -> list[ET.Element]:
    node = entry.find(
        "./Single[@Name='Object']/Single[@Name='VisualElemList']/"
        "List[@Name='VisualElementList']"
    )
    if node is None:
        raise CodesysNativeVisualizationExportError(
            "source visualization has no VisualElementList"
        )
    return node.findall("./Single")


def _set_member(item: ET.Element, property_id: str, value: str) -> None:
    for wrapper in item.findall(
        "./Single[@Name='VisualElemMemberList']/"
        "List[@Name='VisualElemMemberList']/Single"
    ):
        if _named_value(wrapper, "Id") == property_id:
            _set_direct_named_value(wrapper, "Value", value)
            return
    raise CodesysNativeVisualizationExportError(
        f"source control is missing property {property_id}"
    )


def _configured_action(item: ET.Element, kind: str) -> ET.Element:
    for action in item.findall(
        "./Array[@Name='ConfiguredComplexInputs']/Single"
    ):
        if _named_value(action, "Name") == kind:
            return action
    raise CodesysNativeVisualizationExportError(
        f"source control is missing {kind} action"
    )


def _set_action_member(action: ET.Element, operand: str | None) -> None:
    if operand is None:
        raise CodesysNativeVisualizationExportError(
            "Toggle action requires an operand"
        )
    wrapper = action.find(
        "./Single[@Name='VisualElemMemberList']/"
        "List[@Name='VisualElemMemberList']/Single"
    )
    if wrapper is None:
        wrapper = action
    _set_direct_named_value(wrapper, "Value", operand)


def _input_box_action(item: ET.Element) -> ET.Element:
    for action in item.findall(
        "./Dictionary[@Name='VisualElementInputActions']/"
        "Entry/Value/Array/Single"
    ):
        if action.find("./Single[@Name='InputBoxVariable']") is not None:
            return action
    raise CodesysNativeVisualizationExportError(
        "source control is missing InputBox action"
    )


def _set_direct_named_value(
    node: ET.Element,
    name: str,
    value: str | None,
) -> None:
    target = node.find(f"./Single[@Name='{name}']")
    if target is None:
        raise CodesysNativeVisualizationExportError(
            f"source archive is missing {name}"
        )
    target.text = value or ""


def _set_named_value(
    root: ET.Element,
    name: str,
    value: str | None,
) -> None:
    target = root.find(f".//Single[@Name='{name}']")
    if target is None:
        if value is None:
            return
        raise CodesysNativeVisualizationExportError(
            f"source archive is missing {name}"
        )
    target.text = value or ""


def _named_value(node: ET.Element, name: str) -> str | None:
    target = node.find(f".//Single[@Name='{name}']")
    return target.text if target is not None else None


def _element(node: SourceNode) -> ET.Element:
    element = ET.Element(node.name, node.attributes)
    element.text = node.text
    element.tail = node.tail
    element.extend(_element(child) for child in node.children)
    return element
