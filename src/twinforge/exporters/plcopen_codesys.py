"""CODESYS-specific PLCopen XML extensions.

Nothing in this module is required by the PLCopen 2.01 standard profile.
Keeping the target adapter isolated prevents CODESYS project metadata from
becoming an assumption for future targets such as OpenPLC.
"""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping, Sequence

from twinforge.model import Controller, Program, Tag, Task

from .plcopen_library import (
    XHTML_NAMESPACE, GeneratedFunctionBlock, append_block_documentation, emit_function_block_pou, method_object_id,
)
from .plcopen_xml import qualified_name as q


CODESYS_NAMESPACE = "http://www.3s-software.com/plcopenxml"
CODESYS_ID_NAMESPACE = uuid.UUID("012486d2-49b8-5be4-aeca-4a70ed56cfa8")

# Start flags (Machine Expert - Basic's %S13 first cycle, %S0 cold start,
# %S1 warm start) are set by a handler of the runtime's PrepareStart system
# event, which runs before the first scan of every start, including
# stop -> start but not an online change, and cleared by a program called
# last in the first task. PLCopen XML cannot bind the handler to the event:
# examples/CODESYS/scripts/bind_system_events.py does, by the handler's name
# (TF_On<Event>). See docs/experiments/codesys-first-cycle.md.
FIRST_CYCLE_HANDLER = "TF_OnPrepareStart"
END_OF_SCAN_PROGRAM = "TF_EndOfScan"
# Which data the last initialisation reset tells cold from warm: a RETAIN
# variable is re-initialised by download and Reset cold (cold), an ordinary
# one also by Reset warm and a runtime restart (warm). Both start TRUE and
# the handler clears them. They share a list of their own, in the form
# CODESYS exports a list mixing RETAIN and ordinary variables.
START_FLAGS_LIST = "TF_StartFlags"
NON_RETAIN_INIT = "TF_NonRetainInit"
RETAIN_INIT = "TF_RetainInit"
START_ROLES = ("first_cycle", "cold_start", "warm_start")
# Clocks and the real-time clock are set by a program called first in the
# first task, once per scan (docs/experiments/codesys-clocks-and-rtc.md).
START_OF_SCAN_PROGRAM = "TF_StartOfScan"
# Half the period of each clock, in milliseconds of TIME() (since the
# runtime started; it wraps after about 49.7 days, which gives one irregular
# half-period).
CLOCK_HALF_PERIODS = {"clock_10ms": 5, "clock_100ms": 50, "clock_1s": 500, "clock_1min": 30000}
# The real-time clock as the M221's BCD words, from the device's local time
# (SysTimeRtc: UTC seconds -> local seconds -> SYSTIMEDATE fields).
RTC_WORDS = ("rtc_day_of_week", "rtc_seconds", "rtc_hour_minute", "rtc_month_day", "rtc_century_year")
SCAN_ROLES = (*CLOCK_HALF_PERIODS, *RTC_WORDS, "rtc_hold")
RUNTIME_ROLES = (*START_ROLES, *SCAN_ROLES)
# As CODESYS writes it after Library Manager -> Add Library (V3.5 SP22 Patch 3).
RTC_LIBRARY = ("SysTimeRtc", "SysTimeRtc", "SysTimeRtc, * (System)")
# What a CODESYS project gains with a system-event handler, as CODESYS
# exports it (V3.5 SP22 Patch 3): (placeholder, namespace, default resolution).
SYSTEM_EVENT_LIBRARIES = (
    ("CmpEventMgr", "CmpEventMgr", "CmpEventMgr, 3.5.17.0 (System)"),
    ("Component Manager", "Component_Manager", "Component Manager, 3.5.21.0 (System)"),
    ("CmpApp", "CmpApp", "CmpApp, 3.5.21.0 (System)"),
    ("CmpIecTask", "CmpIecTask", "CmpIecTask, 3.5.21.0 (System)"),
)

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
        function_blocks: Sequence[GeneratedFunctionBlock] = (),
        referenced_libraries: Sequence[tuple[str, str]] = (),
        program_names: Mapping[str, str] | None = None,
        runtime_objects: Sequence[tuple[str, str]] = (),
    ) -> None:
        """Wrap generic controller content in a CODESYS application object.

        `referenced_libraries` are installed libraries the application
        references, as (CODESYS display name, namespace). `runtime_objects`
        are (role, qualified variable) pairs, a role from RUNTIME_ROLES: the
        source controller's objects this target reproduces (start flags: see
        FIRST_CYCLE_HANDLER; clocks and the real-time clock: see
        START_OF_SCAN_PROGRAM).
        """
        start_flags = [(role, name) for role, name in runtime_objects if role in START_ROLES]
        scan_objects = [(role, name) for role, name in runtime_objects if role in SCAN_ROLES]
        if not any(role != "rtc_hold" for role, _ in scan_objects):
            scan_objects = []  # holding RTC words nothing reads changes nothing
        rtc = any(role in RTC_WORDS for role, _ in scan_objects)
        placeholders = [*(SYSTEM_EVENT_LIBRARIES if start_flags else ()), *((RTC_LIBRARY,) if rtc else ())]

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
        for index, task in enumerate(controller.iter_tasks()):
            emit_task(resource, task)
            if start_flags and index == 0:
                self._append_program_call(resource[-1], END_OF_SCAN_PROGRAM)
            if scan_objects and index == 0:
                self._append_program_call(resource[-1], START_OF_SCAN_PROGRAM, first=True)
        global_variables = emit_variables(
            resource,
            [*controller.tags.values(), *generated_tags],
        )
        if global_variables is not None:
            self.append_object_id(
                global_variables,
                self.object_id("Application/ControllerTags"),
            )
        start_kinds = any(role != "first_cycle" for role, _ in start_flags)
        if start_kinds:
            self._append_start_flags_list(resource)

        resource_add_data = ET.SubElement(resource, q(ns, "addData"))
        for block in function_blocks:
            wrapper = ET.SubElement(
                resource_add_data,
                q(ns, "data"),
                {
                    "name": f"{CODESYS_NAMESPACE}/pou",
                    "handleUnknown": "implementation",
                },
            )
            pou = emit_function_block_pou(wrapper, block, ns)
            self.append_object_id(pou, self.object_id(f"Application/pou/{block.name}"))
            append_block_documentation(pou, block, ns)
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
        if start_flags:
            self._append_start_pous(resource_add_data, start_flags)
        if scan_objects:
            self._append_start_of_scan_pou(resource_add_data, scan_objects)
        if needs_standard_library or referenced_libraries or placeholders:
            self.append_libraries(resource_add_data, standard=needs_standard_library,
                                  referenced=referenced_libraries, placeholders=placeholders)
        self.append_object_id_data(
            resource_add_data,
            self.object_id("Application"),
        )
        self.append_project_structure(
            add_data,
            controller,
            has_global_variables=global_variables is not None,
            needs_standard_library=needs_standard_library or bool(referenced_libraries) or bool(placeholders),
            function_blocks=function_blocks,
            program_names=program_names,
            start_handler=bool(start_flags),
            start_of_scan=bool(scan_objects),
            start_flags_list=start_kinds,
        )

    def _append_program_call(self, task_element: ET.Element, program: str, *, first: bool = False) -> None:
        """Call `program` last (or first) in a task, as CODESYS writes a program call."""

        ns = self.namespace
        instance = ET.Element(q(ns, "pouInstance"), {"name": program, "typeName": ""})
        ET.SubElement(ET.SubElement(instance, q(ns, "documentation")), q(XHTML_NAMESPACE, "xhtml"))
        calls = [child for child in task_element if child.tag == q(ns, "pouInstance")]
        if first or not calls:
            position = list(task_element).index(calls[0]) if calls else 0
        else:
            position = list(task_element).index(calls[-1]) + 1
        task_element.insert(position, instance)

    def _append_start_of_scan_pou(self, resource_add_data: ET.Element, objects: Sequence[tuple[str, str]]) -> None:
        """TF_StartOfScan: the clocks and the real-time clock words, once per scan.

        A clock is TRUE for the second half of each period of TIME(). The RTC
        words are the local date and time in BCD, read through SysTimeRtc
        with the plain types its aliases stand for (RTS_IEC_RESULT = UDINT),
        so no further library is needed; while an `rtc_hold` bit is set they
        are left for the program to write.
        """

        ns = self.namespace
        wrapper = ET.SubElement(resource_add_data, q(ns, "data"),
                                {"name": f"{CODESYS_NAMESPACE}/pou", "handleUnknown": "implementation"})
        program = ET.SubElement(wrapper, q(ns, "pou"), {"name": START_OF_SCAN_PROGRAM, "pouType": "program"})
        interface = ET.SubElement(program, q(ns, "interface"))
        local_vars = ET.SubElement(interface, q(ns, "localVars"))
        clocks = [(role, name) for role, name in objects if role in CLOCK_HALF_PERIODS]
        words = [(role, name) for role, name in objects if role in RTC_WORDS]
        hold = [name for role, name in objects if role == "rtc_hold"]
        declarations = [("nMs", "UDINT")] if clocks else []
        if words:
            declarations += [("dwUtc", "DWORD"), ("dwLocal", "DWORD"), ("eGet", "UDINT"), ("eLocal", "UDINT"),
                             ("eDate", "UDINT"), ("stDate", "SYSTIMEDATE")]
        for name, type_name in declarations:
            variable = ET.SubElement(local_vars, q(ns, "variable"), {"name": name})
            type_element = ET.SubElement(variable, q(ns, "type"))
            if type_name == "SYSTIMEDATE":
                ET.SubElement(type_element, q(ns, "derived"), {"name": type_name})
            else:
                ET.SubElement(type_element, q(ns, type_name))

        def bcd(field: str) -> str:
            return f"(stDate.{field} / 10) * 16 + stDate.{field} MOD 10"

        word_values = {
            "rtc_day_of_week": "stDate.wDayOfWeek",
            "rtc_seconds": bcd("wSecond"),
            "rtc_hour_minute": f"({bcd('wHour')}) * 256 + {bcd('wMinute')}",
            "rtc_month_day": f"({bcd('wMonth')}) * 256 + {bcd('wDay')}",
            "rtc_century_year": ("((stDate.wYear / 1000) * 16 + (stDate.wYear / 100) MOD 10) * 256"
                                 " + ((stDate.wYear MOD 100) / 10) * 16 + stDate.wYear MOD 10"),
        }
        lines: list[str] = []
        if clocks:
            lines.append("nMs := TIME_TO_UDINT(TIME());\n")
            lines += [f"{name} := (nMs / {CLOCK_HALF_PERIODS[role]}) MOD 2 = 1;\n" for role, name in clocks]
        if words:
            indent = "    " if hold else ""
            if hold:
                lines.append(f"IF NOT ({' OR '.join(hold)}) THEN\n")
            lines += [
                f"{indent}dwUtc := SysTimeRtcGet(pResult := eGet);\n",
                f"{indent}eLocal := SysTimeRtcConvertUtcToLocal(dwTimestampUtc := dwUtc, pdwTimestampLocal := dwLocal);\n",
                f"{indent}eDate := SysTimeRtcConvertUtcToDate(dwTimestampUtc := dwLocal, pDate := stDate);\n",
                f"{indent}IF eGet = 0 AND eLocal = 0 AND eDate = 0 THEN\n",
            ]
            lines += [f"{indent}    {name} := UINT_TO_INT({word_values[role]});\n" for role, name in words]
            lines.append(f"{indent}END_IF;\n")
            if hold:
                lines.append("END_IF;\n")
        st = ET.SubElement(ET.SubElement(program, q(ns, "body")), q(ns, "ST"))
        ET.SubElement(st, q(XHTML_NAMESPACE, "xhtml")).text = "".join(lines)
        self.append_object_id(program, self.object_id(f"Application/program/{START_OF_SCAN_PROGRAM}"))

    def _append_start_flags_list(self, resource: ET.Element) -> None:
        """TF_StartFlags: NON_RETAIN_INIT and RETAIN_INIT, both TRUE until cleared.

        As CODESYS exports a list mixing ordinary and RETAIN variables (V3.5
        SP22 Patch 3): every variable in the list itself, and the split in a
        `mixedattrsvarlist` section, with `retain="true"` on the RETAIN part.
        A list of RETAIN variables only was exported without any RETAIN
        marking, so the flags share one list.
        """

        ns = self.namespace

        def flag(parent: ET.Element, name: str) -> None:
            variable = ET.SubElement(parent, q(ns, "variable"), {"name": name})
            ET.SubElement(ET.SubElement(variable, q(ns, "type")), q(ns, "BOOL"))
            ET.SubElement(ET.SubElement(variable, q(ns, "initialValue")), q(ns, "simpleValue"), {"value": "TRUE"})

        variables = ET.SubElement(resource, q(ns, "globalVars"), {"name": START_FLAGS_LIST})
        flag(variables, NON_RETAIN_INIT)
        flag(variables, RETAIN_INIT)
        add_data = ET.SubElement(variables, q(ns, "addData"))
        attributes = ET.SubElement(ET.SubElement(add_data, q(ns, "data"), {
            "name": f"{CODESYS_NAMESPACE}/attributes", "handleUnknown": "implementation"}), q(ns, "Attributes"))
        ET.SubElement(attributes, q(ns, "Attribute"), {"Name": "qualified_only", "Value": ""})
        self.append_object_id_data(add_data, self.object_id(f"Application/{START_FLAGS_LIST}"))
        mixed = ET.SubElement(ET.SubElement(add_data, q(ns, "data"), {
            "name": f"{CODESYS_NAMESPACE}/mixedattrsvarlist", "handleUnknown": "implementation"}),
            q(ns, "MixedAttrsVarList"))
        flag(ET.SubElement(mixed, q(ns, "globalVars"), {"name": START_FLAGS_LIST}), NON_RETAIN_INIT)
        flag(ET.SubElement(mixed, q(ns, "globalVars"), {"name": START_FLAGS_LIST, "retain": "true"}), RETAIN_INIT)

    def _append_start_pous(self, resource_add_data: ET.Element, flags: Sequence[tuple[str, str]]) -> None:
        """The PrepareStart handler that sets the flags, and the program that clears them.

        The handler's interface is the one CODESYS generates for a
        PrepareStart handler; the runtime calls it with that signature. It
        runs after the start's initialisation, so TF_StartFlags tells which
        data that reset.
        """

        ns = self.namespace

        def pou(name: str, pou_type: str) -> ET.Element:
            wrapper = ET.SubElement(resource_add_data, q(ns, "data"),
                                    {"name": f"{CODESYS_NAMESPACE}/pou", "handleUnknown": "implementation"})
            return ET.SubElement(wrapper, q(ns, "pou"), {"name": name, "pouType": pou_type})

        def body(element: ET.Element, text: str) -> None:
            st = ET.SubElement(ET.SubElement(element, q(ns, "body")), q(ns, "ST"))
            ET.SubElement(st, q(XHTML_NAMESPACE, "xhtml")).text = text

        handler = pou(FIRST_CYCLE_HANDLER, "function")
        interface = ET.SubElement(handler, q(ns, "interface"))
        ET.SubElement(ET.SubElement(interface, q(ns, "returnType")), q(ns, "DWORD"))
        parameter = ET.SubElement(ET.SubElement(interface, q(ns, "inOutVars")), q(ns, "variable"),
                                  {"name": "EventPrm"})
        ET.SubElement(ET.SubElement(parameter, q(ns, "type")), q(ns, "derived"), {"name": "CmpApp.EVTPARAM_CmpApp"})
        ET.SubElement(ET.SubElement(interface, q(ns, "documentation")), q(XHTML_NAMESPACE, "xhtml")).text = (
            " Do not change the interface of this function!\n"
            " Called by the runtime system's PrepareStart event, before the first scan of every start.\n"
            " Bind it in Task Configuration -> System Events: run bind_system_events.py after the import.")
        non_retain, retain = f"{START_FLAGS_LIST}.{NON_RETAIN_INIT}", f"{START_FLAGS_LIST}.{RETAIN_INIT}"
        value = {"first_cycle": "TRUE", "cold_start": retain, "warm_start": f"{non_retain} AND NOT {retain}"}
        lines = [f"{variable} := {value[role]};\n" for role, variable in flags]
        if any(role != "first_cycle" for role, _ in flags):
            lines += [f"{non_retain} := FALSE;\n", f"{retain} := FALSE;\n"]
        body(handler, "".join(lines))
        self.append_object_id(handler, self.object_id(f"Application/pou/{FIRST_CYCLE_HANDLER}"))

        program = pou(END_OF_SCAN_PROGRAM, "program")
        ET.SubElement(program, q(ns, "interface"))
        body(program, "".join(f"{variable} := FALSE;\n" for _, variable in flags))
        self.append_object_id(program, self.object_id(f"Application/program/{END_OF_SCAN_PROGRAM}"))

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
        """Append an object ID to the element's ``addData`` (one per element in
        TC6), creating it if the element has none yet."""

        add_data = next((child for child in parent if child.tag == q(self.namespace, "addData")), None)
        if add_data is None:
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
        function_blocks: Sequence[GeneratedFunctionBlock] = (),
        program_names: Mapping[str, str] | None = None,
        start_handler: bool = False,
        start_flags_list: bool = False,
        start_of_scan: bool = False,
    ) -> None:
        """Describe CODESYS navigator objects independently of IEC content.

        `program_names` maps a source program name to the IEC name it is
        exported under, where they differ.
        """

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
        for block in function_blocks:
            block_object = self._append_structure_object(application, block.name, f"Application/pou/{block.name}")
            if block.init_inputs:
                ET.SubElement(block_object, q(self.namespace, "Object"),
                              {"Name": "FB_init", "ObjectId": method_object_id(block, "FB_init")})
        for program in controller.iter_programs():
            name = (program_names or {}).get(program.name, program.name)
            program_object = self._append_structure_object(
                application,
                name,
                f"Application/program/{name}",
            )
            for routine in program.iter_routines():
                if routine is program.main_routine:
                    continue
                self._append_structure_object(
                    program_object,
                    routine.name,
                    (
                        f"Application/program/{name}/action/"
                        f"{routine.name}"
                    ),
                )
        if start_of_scan:
            self._append_structure_object(application, START_OF_SCAN_PROGRAM,
                                          f"Application/program/{START_OF_SCAN_PROGRAM}")
        if start_handler:
            self._append_structure_object(application, END_OF_SCAN_PROGRAM,
                                          f"Application/program/{END_OF_SCAN_PROGRAM}")
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
        if start_flags_list:
            self._append_structure_object(application, START_FLAGS_LIST, f"Application/{START_FLAGS_LIST}")
        if start_handler:
            self._append_structure_object(application, FIRST_CYCLE_HANDLER,
                                          f"Application/pou/{FIRST_CYCLE_HANDLER}")

    def append_standard_library(self, parent: ET.Element) -> None:
        """Add the CODESYS Standard library used by TON and R_TRIG blocks."""

        self.append_libraries(parent, standard=True)

    def append_libraries(
        self,
        parent: ET.Element,
        *,
        standard: bool,
        referenced: Sequence[tuple[str, str]] = (),
        placeholders: Sequence[tuple[str, str, str]] = (),
    ) -> None:
        """The Library Manager: Standard and other placeholders, and installed libraries.

        `placeholders` are further library placeholders, as (placeholder,
        namespace, default resolution), written as CODESYS writes them
        (`Name="#CmpApp"`), after Standard.

        An installed library is referenced directly, by its display name and
        namespace, as a CODESYS export writes it (V3.5 SP22 Patch 3):
        `<Library Name="TwinForge_MEBasic, 0.2.1 (TwinForge)"
        Namespace="TwinForge_MEBasic" ... />`, after the placeholder entries
        and before the placeholder redirections.
        """

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
        if standard:
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
        for placeholder, namespace, resolution in placeholders:
            ET.SubElement(
                libraries,
                q(ns, "Library"),
                {
                    "Name": f"#{placeholder}",
                    "Namespace": namespace,
                    "HideWhenReferencedAsDependency": "false",
                    "PublishSymbolsInContainer": "false",
                    "SystemLibrary": "false",
                    "LinkAllContent": "false",
                    "DefaultResolution": resolution,
                },
            )
        for name, namespace in referenced:
            ET.SubElement(
                libraries,
                q(ns, "Library"),
                {
                    "Name": name,
                    "Namespace": namespace,
                    "HideWhenReferencedAsDependency": "false",
                    "PublishSymbolsInContainer": "false",
                    "SystemLibrary": "false",
                    "LinkAllContent": "false",
                },
            )
        if standard:
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
