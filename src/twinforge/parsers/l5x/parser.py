# src/twinforge/parsers/l5x/parser.py

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from twinforge.converters.l5x import (
    convert_add_on_instruction,
    convert_controller,
    convert_module,
    convert_program,
    convert_tag,
    element_to_source_extension,
)
from twinforge.converters import ConversionDiagnostic
from twinforge.model import (
    AddOnInstruction,
    Plant,
    Program,
    SoftwareComponent,
    SoftwareComponentKind,
)
from twinforge.parsers.l5x.capture import ReportMode, capture_section
from twinforge.parsers.l5x.document import (
    L5XDocument,
    L5XTargetType,
)
from twinforge.schema.l5x import (
    CONTROLLER_ATTRIBUTES,
    CONTROLLER_ELEMENTS,
    MODULE_ATTRIBUTES,
    MODULE_ELEMENTS,
    PROGRAM_ATTRIBUTES,
    PROGRAM_ELEMENTS,
    TAG_ATTRIBUTES,
    TAG_ELEMENTS,
)
from twinforge.schema.l5x.add_on_instructions import (
    AOI_ATTRIBUTES,
    AOI_ELEMENTS,
)


class L5XParser:
    def __init__(self) -> None:
        self.diagnostics: list[ConversionDiagnostic] = []

    def parse(
        self,
        filename: str | Path,
        *,
        report_mode: ReportMode | None = "summary",
        report_depth: int | None = 2,
    ) -> Plant:

        self.diagnostics = []
        tree = ET.parse(filename)
        root = tree.getroot()

        controller_element = root.find("Controller")
        if controller_element is None:
            raise ValueError("L5X file does not contain a Controller element.")

        controller_section = capture_section(
            controller_element,
            CONTROLLER_ATTRIBUTES,
            CONTROLLER_ELEMENTS,
        )

        #
        # Temporary
        #
        # Report exactly what was captured from the L5X.
        #
        if report_mode is not None:
            controller_section.report(
                CONTROLLER_ATTRIBUTES,
                CONTROLLER_ELEMENTS,
                mode=report_mode,
                max_depth=report_depth,
            )

        controller = convert_controller(
            controller_section,
            diagnostics=self.diagnostics,
        )
        plant = Plant(
            name=root.attrib.get("TargetName", controller.name or Path(filename).stem),
            source_extensions=[element_to_source_extension(root)],
        )
        plant.add_controller(controller)
        return plant

    def parse_document(
        self,
        filename: str | Path,
        *,
        report_mode: ReportMode | None = None,
        report_depth: int | None = 2,
    ) -> L5XDocument:
        """Dispatch any supported standalone L5X export by ``TargetType``."""

        self.diagnostics = []
        tree = ET.parse(filename)
        root = tree.getroot()
        target_type = _target_type(root)
        element = _target_element(root, target_type)
        attributes, elements = _target_spec(target_type)
        section = capture_section(element, attributes, elements)
        if report_mode is not None:
            section.report(
                attributes,
                elements,
                mode=report_mode,
                max_depth=report_depth,
            )

        target = _convert_target(
            target_type,
            section,
            self.diagnostics,
        )
        software_component = _software_component(target)
        return L5XDocument(
            target_type=target_type,
            target_name=root.attrib.get(
                "TargetName",
                getattr(target, "name", Path(filename).stem),
            ),
            target=target,
            source_path=Path(filename).resolve(),
            context_controller_names=tuple(
                dict.fromkeys(
                    controller.attrib["Name"]
                    for controller in root.iter("Controller")
                    if "Name" in controller.attrib
                )
            ),
            software_component=software_component,
            diagnostics=tuple(self.diagnostics),
            context_controller_tags=_context_controller_tags(
                root,
                target_type,
                self.diagnostics,
            ),
            source_extensions=(element_to_source_extension(root),),
        )


def _context_controller_tags(
    root: ET.Element,
    target_type: L5XTargetType,
    diagnostics: list[ConversionDiagnostic],
):
    """Convert controller-scope context tags accompanying component exports."""

    if target_type is L5XTargetType.CONTROLLER:
        return ()
    return tuple(
        convert_tag(
            capture_section(tag, TAG_ATTRIBUTES, TAG_ELEMENTS),
            diagnostics=diagnostics,
        )
        for controller in root.findall("Controller")
        for tags in controller.findall("Tags")
        for tag in tags.findall("Tag")
    )


def _target_type(root: ET.Element) -> L5XTargetType:
    raw = root.attrib.get("TargetType")
    try:
        return L5XTargetType(raw)
    except ValueError as error:
        raise ValueError(f"unsupported L5X TargetType {raw!r}") from error


def _target_element(
    root: ET.Element,
    target_type: L5XTargetType,
) -> ET.Element:
    candidates = [
        element
        for element in root.iter(target_type.value)
        if element.attrib.get("Use") == "Target"
    ]
    if len(candidates) != 1:
        raise ValueError(
            f"L5X {target_type.value} export requires exactly one "
            f"Use='Target' element; found {len(candidates)}"
        )
    return candidates[0]


def _target_spec(target_type: L5XTargetType):
    return {
        L5XTargetType.CONTROLLER: (
            CONTROLLER_ATTRIBUTES,
            CONTROLLER_ELEMENTS,
        ),
        L5XTargetType.MODULE: (MODULE_ATTRIBUTES, MODULE_ELEMENTS),
        L5XTargetType.PROGRAM: (PROGRAM_ATTRIBUTES, PROGRAM_ELEMENTS),
        L5XTargetType.ADD_ON_INSTRUCTION: (
            AOI_ATTRIBUTES,
            AOI_ELEMENTS,
        ),
    }[target_type]


def _convert_target(
    target_type: L5XTargetType,
    section,
    diagnostics: list[ConversionDiagnostic],
):
    if target_type is L5XTargetType.CONTROLLER:
        return convert_controller(section, diagnostics=diagnostics)
    if target_type is L5XTargetType.MODULE:
        return convert_module(section, diagnostics=diagnostics)
    if target_type is L5XTargetType.PROGRAM:
        return convert_program(section, diagnostics=diagnostics)
    return convert_add_on_instruction(section, diagnostics=diagnostics)


def _software_component(target) -> SoftwareComponent | None:
    if isinstance(target, Program):
        return SoftwareComponent(
            name=target.name,
            kind=SoftwareComponentKind.PROGRAM,
            implementation=target,
            source_extensions=list(target.source_extensions),
        )
    if isinstance(target, AddOnInstruction):
        return SoftwareComponent(
            name=target.name,
            kind=SoftwareComponentKind.FUNCTION_BLOCK,
            implementation=target,
            vendor=target.vendor,
            revision=target.revision,
            source_extensions=list(target.source_extensions),
        )
    return None
