# src/twinforge/parsers/l5x/parser.py

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from twinforge.converters.l5x import (
    convert_controller,
    element_to_source_extension,
)
from twinforge.converters import ConversionDiagnostic
from twinforge.model import Plant
from twinforge.parsers.l5x.capture import ReportMode, capture_section
from twinforge.schema.l5x import (
    CONTROLLER_ATTRIBUTES,
    CONTROLLER_ELEMENTS,
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
