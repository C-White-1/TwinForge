"""Construct the target-neutral PLCopen project and controller hierarchy."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
import xml.etree.ElementTree as ET

from twinforge.model import Controller, Program, Tag, Task

from .plcopen_xml import qualified_name


ProgramEmitter = Callable[[ET.Element, Program], None]
TaskEmitter = Callable[[ET.Element, Task], None]
VariableEmitter = Callable[
    [ET.Element, Sequence[Tag]],
    ET.Element | None,
]
TargetApplicationEmitter = Callable[
    [ET.Element, Controller, Sequence[Tag]],
    None,
]


class PLCopenProjectOrchestrator:
    """Build project structure while delegating executable content emission."""

    def __init__(
        self,
        *,
        namespace: str,
        emit_program: ProgramEmitter,
        emit_task: TaskEmitter,
        emit_global_variables: VariableEmitter,
        emit_target_application: TargetApplicationEmitter | None = None,
    ) -> None:
        self._namespace = namespace
        self._emit_program = emit_program
        self._emit_task = emit_task
        self._emit_global_variables = emit_global_variables
        self._emit_target_application = emit_target_application

    def build(
        self,
        controller: Controller,
        generated_tags: Sequence[Tag],
        *,
        project_name: str,
        creation_time: datetime,
    ) -> ET.Element:
        """Return a complete PLCopen project in deterministic source order."""

        ET.register_namespace("", self._namespace)
        root = ET.Element(qualified_name(self._namespace, "project"))
        self._file_header(root, creation_time)
        self._content_header(root, project_name)

        types = ET.SubElement(
            root,
            qualified_name(self._namespace, "types"),
        )
        ET.SubElement(
            types,
            qualified_name(self._namespace, "dataTypes"),
        )
        pous = ET.SubElement(types, qualified_name(self._namespace, "pous"))
        instances = ET.SubElement(
            root,
            qualified_name(self._namespace, "instances"),
        )
        configurations = ET.SubElement(
            instances,
            qualified_name(self._namespace, "configurations"),
        )

        if self._emit_target_application is not None:
            self._emit_target_application(root, controller, generated_tags)
        else:
            for program in controller.iter_programs():
                self._emit_program(pous, program)
            self._standard_configuration(
                configurations,
                controller,
                generated_tags,
            )
        return root

    def _file_header(
        self,
        root: ET.Element,
        creation_time: datetime,
    ) -> None:
        ET.SubElement(
            root,
            qualified_name(self._namespace, "fileHeader"),
            {
                "companyName": "TwinForge",
                "productName": "TwinForge",
                "productVersion": "0.1.0",
                "creationDateTime": creation_time.isoformat(),
            },
        )

    def _content_header(self, root: ET.Element, name: str) -> None:
        header = ET.SubElement(
            root,
            qualified_name(self._namespace, "contentHeader"),
            {"name": name},
        )
        coordinate = ET.SubElement(
            header,
            qualified_name(self._namespace, "coordinateInfo"),
        )
        for language in ("fbd", "ld", "sfc"):
            element = ET.SubElement(
                coordinate,
                qualified_name(self._namespace, language),
            )
            ET.SubElement(
                element,
                qualified_name(self._namespace, "scaling"),
                {"x": "1", "y": "1"},
            )

    def _standard_configuration(
        self,
        configurations: ET.Element,
        controller: Controller,
        generated_tags: Sequence[Tag],
    ) -> None:
        configuration = ET.SubElement(
            configurations,
            qualified_name(self._namespace, "configuration"),
            {"name": controller.name or "PLC"},
        )
        resource = ET.SubElement(
            configuration,
            qualified_name(self._namespace, "resource"),
            {"name": "Application"},
        )
        for task in controller.iter_tasks():
            self._emit_task(resource, task)
        self._emit_global_variables(
            resource,
            [*controller.tags.values(), *generated_tags],
        )
