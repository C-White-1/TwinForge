"""CODESYS-specific PLCopen XML extensions.

Nothing in this module is required by the PLCopen 2.01 standard profile.
Keeping the target adapter isolated prevents CODESYS project metadata from
becoming an assumption for future targets such as OpenPLC.
"""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence

from twinforge.model import Controller, Program, Tag, Task

from .plcopen_xml import qualified_name as q


CODESYS_NAMESPACE = "http://www.3s-software.com/plcopenxml"
CODESYS_ID_NAMESPACE = uuid.UUID("012486d2-49b8-5be4-aeca-4a70ed56cfa8")

TaskEmitter = Callable[[ET.Element, Task], None]
VariableEmitter = Callable[[ET.Element, Sequence[Tag]], ET.Element | None]
ProgramEmitter = Callable[[ET.Element, Program], None]


class CodesysProfileSupport:
    """Generate target metadata while generic callbacks emit IEC content."""

    def __init__(self, namespace: str) -> None:
        self.namespace = namespace
        self._ids: dict[str, str] = {}

    def reset(self) -> None:
        """Reset per-document caches without changing target configuration."""

        self._ids.clear()

    def object_id(self, path: str) -> str:
        """Return a deterministic CODESYS object ID for a logical path."""

        if path not in self._ids:
            self._ids[path] = str(uuid.uuid5(CODESYS_ID_NAMESPACE, path))
        return self._ids[path]

    @staticmethod
    def library_type(type_name: str) -> str:
        """Qualify a type supplied by the CODESYS Standard library."""

        return f"Standard.{type_name}"

    def emit_application(
        self,
        root: ET.Element,
        controller: Controller,
        generated_tags: Sequence[Tag],
        *,
        needs_standard_library: bool,
        emit_task: TaskEmitter,
        emit_variables: VariableEmitter,
        emit_program: ProgramEmitter,
    ) -> None:
        """Wrap generic controller content in a CODESYS application object."""

        ns = self.namespace
        add_data = ET.SubElement(root, q(ns, "addData"))
        application = ET.SubElement(
            add_data,
            q(ns, "data"),
            {
                "name": f"{CODESYS_NAMESPACE}/application",
                "handleUnknown": "implementation",
            },
        )
        resource = ET.SubElement(
            application,
            q(ns, "resource"),
            {"name": "Application"},
        )
        for task in controller.iter_tasks():
            emit_task(resource, task)
        global_variables = emit_variables(
            resource,
            [*controller.tags.values(), *generated_tags],
        )
        if global_variables is not None:
            self.append_object_id(
                global_variables,
                self.object_id("Application/ControllerTags"),
            )

        resource_add_data = ET.SubElement(resource, q(ns, "addData"))
        for program in controller.iter_programs():
            wrapper = ET.SubElement(
                resource_add_data,
                q(ns, "data"),
                {
                    "name": f"{CODESYS_NAMESPACE}/pou",
                    "handleUnknown": "implementation",
                },
            )
            emit_program(wrapper, program)
        if needs_standard_library:
            self.append_standard_library(resource_add_data)
        self.append_object_id_data(
            resource_add_data,
            self.object_id("Application"),
        )
        self.append_project_structure(
            add_data,
            controller,
            has_global_variables=global_variables is not None,
            needs_standard_library=needs_standard_library,
        )

    def append_task_settings(
        self,
        task_element: ET.Element,
        task: Task,
    ) -> None:
        """Append CODESYS scheduling metadata and a deterministic object ID."""

        ns = self.namespace
        add_data = ET.SubElement(task_element, q(ns, "addData"))
        data = ET.SubElement(
            add_data,
            q(ns, "data"),
            {
                "name": f"{CODESYS_NAMESPACE}/tasksettings",
                "handleUnknown": "implementation",
            },
        )
        settings = {
            "KindOfTask": codesys_task_kind(task.task_type),
            "WithinSPSTimeSlicing": "true",
        }
        if task.rate is not None:
            settings.update(
                {"Interval": f"t#{task.rate}ms", "IntervalUnit": "ms"}
            )
        task_settings = ET.SubElement(data, "TaskSettings", settings)
        ET.SubElement(
            task_settings,
            "Watchdog",
            {
                "Enabled": "false",
                "TimeUnit": "ms",
                "Sensitivity": "1",
            },
        )
        self.append_object_id_data(
            add_data,
            self.object_id(f"Application/task/{task.name}"),
        )

    def append_call_type(
        self,
        block: ET.Element,
        call_type_name: str = "functionblock",
    ) -> None:
        """Mark a block or action call using the CODESYS extension."""

        ns = self.namespace
        add_data = ET.SubElement(block, q(ns, "addData"))
        data = ET.SubElement(
            add_data,
            q(ns, "data"),
            {
                "name": f"{CODESYS_NAMESPACE}/fbdcalltype",
                "handleUnknown": "implementation",
            },
        )
        call_type = ET.SubElement(data, "CallType", {"xmlns": ""})
        call_type.text = call_type_name

    def append_object_id(self, parent: ET.Element, object_id: str) -> None:
        """Append an object ID in a new PLCopen ``addData`` container."""

        add_data = ET.SubElement(parent, q(self.namespace, "addData"))
        self.append_object_id_data(add_data, object_id)

    def append_object_id_data(
        self,
        add_data: ET.Element,
        object_id: str,
    ) -> None:
        """Append an object ID to an existing ``addData`` container."""

        ns = self.namespace
        data = ET.SubElement(
            add_data,
            q(ns, "data"),
            {
                "name": f"{CODESYS_NAMESPACE}/objectid",
                "handleUnknown": "discard",
            },
        )
        value = ET.SubElement(data, q(ns, "ObjectId"))
        value.text = object_id

    def append_project_structure(
        self,
        add_data: ET.Element,
        controller: Controller,
        *,
        has_global_variables: bool,
        needs_standard_library: bool,
    ) -> None:
        """Describe CODESYS navigator objects independently of IEC content."""

        ns = self.namespace
        data = ET.SubElement(
            add_data,
            q(ns, "data"),
            {
                "name": f"{CODESYS_NAMESPACE}/projectstructure",
                "handleUnknown": "discard",
            },
        )
        structure = ET.SubElement(data, q(ns, "ProjectStructure"))
        application = ET.SubElement(
            structure,
            q(ns, "Object"),
            {
                "Name": "Application",
                "ObjectId": self.object_id("Application"),
            },
        )
        if needs_standard_library:
            self._append_structure_object(
                application,
                "Library Manager",
                "Application/Library Manager",
            )
        for program in controller.iter_programs():
            program_object = self._append_structure_object(
                application,
                program.name,
                f"Application/program/{program.name}",
            )
            for routine in program.iter_routines():
                if routine is program.main_routine:
                    continue
                self._append_structure_object(
                    program_object,
                    routine.name,
                    (
                        f"Application/program/{program.name}/action/"
                        f"{routine.name}"
                    ),
                )
        for task in controller.iter_tasks():
            self._append_structure_object(
                application,
                task.name,
                f"Application/task/{task.name}",
            )
        if has_global_variables:
            self._append_structure_object(
                application,
                "ControllerTags",
                "Application/ControllerTags",
            )

    def append_standard_library(self, parent: ET.Element) -> None:
        """Add the CODESYS Standard library used by TON and R_TRIG blocks."""

        ns = self.namespace
        data = ET.SubElement(
            parent,
            q(ns, "data"),
            {
                "name": f"{CODESYS_NAMESPACE}/libraries",
                "handleUnknown": "implementation",
            },
        )
        libraries = ET.SubElement(data, q(ns, "Libraries"))
        ET.SubElement(
            libraries,
            q(ns, "Library"),
            {
                "Name": "#Standard",
                "Namespace": "Standard",
                "HideWhenReferencedAsDependency": "false",
                "PublishSymbolsInContainer": "false",
                "SystemLibrary": "false",
                "LinkAllContent": "false",
                "DefaultResolution": "Standard, * (System)",
            },
        )
        redirections = ET.SubElement(
            libraries,
            q(ns, "PlaceholderRedirections"),
        )
        ET.SubElement(
            redirections,
            q(ns, "PlaceholderRedirection"),
            {
                "Placeholder": "Standard",
                "Redirection": "Standard, 3.5.22.0 (System)",
            },
        )
        self.append_object_id(
            libraries,
            self.object_id("Application/Library Manager"),
        )

    def _append_structure_object(
        self,
        parent: ET.Element,
        name: str,
        path: str,
    ) -> ET.Element:
        return ET.SubElement(
            parent,
            q(self.namespace, "Object"),
            {"Name": name, "ObjectId": self.object_id(path)},
        )


def codesys_task_kind(task_type: str | None) -> str:
    """Map a Logix task category to CODESYS scheduling terminology."""

    if task_type and task_type.lower() == "continuous":
        return "Freewheeling"
    if task_type and task_type.lower() == "event":
        return "Event"
    return "Cyclic"
