# -*- coding: utf-8 -*-
"""Bind TwinForge's system-event handlers in CODESYS after a PLCopen import.

A TwinForge CODESYS export can contain handlers of the runtime's system
events: TF_OnPrepareStart sets Machine Expert - Basic's first-cycle bit
(%S13) before the first scan of every start. PLCopen XML cannot carry
Task Configuration -> System Events, so after an import the handler is never
called. This script binds each handler the application contains, found by
its name (TF_On<Event>), as if added with Add Event Handler.

How: CODESYS's native export of the Task Configuration does hold the event
list (alSysEventList). The script exports the Task Configuration, adds the
missing entries, removes it and imports the edited copy in its place:
importing over the existing one replaces only its tasks. See
docs/experiments/codesys-first-cycle.md.

Run with the imported project open: Tools > Scripting > Execute Script
File... Run it again at any time: a bound event is left as it is. This file
runs inside CODESYS's IronPython 2.7 ScriptEngine. The text functions above
`main` are plain Python, tested by TwinForge
(tests/test_codesys_bind_system_events.py); keep them Python 2.7 compatible.
"""
from __future__ import print_function

import os
import re
import tempfile

PREFIX = "TF_On"

# Each event's alSysEventList entry, copied from CODESYS's native export of
# a handler added with Add Event Handler (V3.5 SP22 Patch 3, Control Win).
# Only the function to call and the position vary.
EVENTS = {
    "PrepareStart": (
        '<Single Type="{357faaca-a279-4878-8c2f-ec7c49896fa3}" Method="IArchivable">\n'
        '  <Single Name="Eventname" Type="string">PrepareStart</Single>\n'
        '  <Single Name="Description" Type="string">Called before application starts. '
        'Context=Communication task. Debugging=Disabled</Single>\n'
        '  <Single Name="stComponentId" Type="string">CmpApp.EventIDs.CMPID_CmpApp</Single>\n'
        '  <Single Name="stEventId" Type="string">CmpApp.EventIDs.EVT_PrepareStart</Single>\n'
        '  <Single Name="stParameterId" Type="string">CmpApp.EventIDs.EVTPARAMID_CmpApp</Single>\n'
        '  <Single Name="stParameterVersion" Type="string">CmpApp.EventIDs.EVTVERSION_CmpApp</Single>\n'
        '  <Single Name="ParameterStruct" Type="string">CmpApp.EVTPARAM_CmpApp</Single>\n'
        '  <Null Name="Library" />\n'
        '  <Single Name="Active" Type="bool">True</Single>\n'
        '  <Single Name="FunctionToCall" Type="string">%(function)s</Single>\n'
        '  <Single Name="Position" Type="short">%(position)d</Single>\n'
        '</Single>\n'
    ),
}

# A project that never had a handler writes the list as Null.
_EMPTY_LIST = re.compile(r'<(?:List2|Null) Name="alSysEventList"\s*/>')
_LIST = re.compile(r'<List2 Name="alSysEventList">')
_BOUND = re.compile(r'<Single Name="Eventname" Type="string">([^<]*)</Single>')
_POSITION = re.compile(r'<Single Name="Position" Type="short">(\d+)</Single>')


def handlers(names):
    """(event, function) for each TwinForge handler among object names."""
    found = []
    for name in sorted(set(names)):
        if name.startswith(PREFIX) and name[len(PREFIX):] in EVENTS:
            found.append((name[len(PREFIX):], name))
    return found


def bound_events(text):
    """The events a native Task Configuration export binds."""
    match = _LIST.search(text)
    if match is None:
        return []
    return _BOUND.findall(text[match.end():text.index("</List2>", match.end())])


def with_events(text, wanted):
    """The export with an entry for each wanted (event, function) not yet bound.

    Returns (text, added events). Raises ValueError for a layout this script
    does not know.
    """
    bound = bound_events(text)
    missing = [(event, function) for event, function in wanted if event not in bound]
    if not missing:
        return text, []
    empty = _EMPTY_LIST.search(text)
    if empty is not None:
        start, end, position = empty.start(), empty.end(), 0
        before, after = '<List2 Name="alSysEventList">\n', "</List2>"
    else:
        match = _LIST.search(text)
        if match is None:
            raise ValueError("no alSysEventList in the Task Configuration export")
        start = end = text.index("</List2>", match.end())
        positions = [int(p) for p in _POSITION.findall(text[match.end():start])]
        position = max(positions) + 1 if positions else 0
        before = after = ""
    entries = "".join(EVENTS[event] % {"function": function, "position": position + index}
                      for index, (event, function) in enumerate(missing))
    return text[:start] + before + entries + after + text[end:], [event for event, _ in missing]


def main():
    project = projects.primary  # noqa: F821 - provided by CODESYS
    if project is None:
        print("Open the imported project first.")
        return
    application = project.active_application
    wanted = handlers(child.get_name() for child in application.get_children(True))
    if not wanted:
        print("No TwinForge event handler (%s<Event>) in the application; nothing to bind." % PREFIX)
        return
    found = application.find("Task Configuration", False)
    if not found:
        print("The application has no Task Configuration.")
        return
    folder = tempfile.mkdtemp(prefix="twinforge_events_")
    before = os.path.join(folder, "task_configuration_before.export")
    after = os.path.join(folder, "task_configuration_after.export")
    project.export_native([found[0]], before, recursive=True)
    with open(before) as source:
        text = source.read()
    edited, added = with_events(text, wanted)
    if not added:
        print("Already bound: %s." % ", ".join(event for event, _ in wanted))
        return
    with open(after, "w") as target:
        target.write(edited)

    class Replace(NativeImportHandler):  # noqa: F821 - provided by CODESYS
        def conflict(self, *args):
            return NativeImportResolve.replace  # noqa: F821 - provided by CODESYS

        def progress(self, *args):
            pass

        def skipped(self, *args):
            print("Skipped on import: %r" % (args,))

    found[0].remove()
    application.import_native(after, None, Replace())
    found = application.find("Task Configuration", False)
    if not found:
        print("The Task Configuration did not come back! Import %s with Project > Import." % before)
        return
    check = os.path.join(folder, "task_configuration_check.export")
    project.export_native([found[0]], check, recursive=True)
    with open(check) as source:
        missing = [event for event in added if event not in bound_events(source.read())]
    if missing:
        print("Not bound: %s. The Task Configuration as it was: %s" % (", ".join(missing), before))
        return
    for event, function in wanted:
        if event in added:
            print("Bound %s -> %s (Task Configuration > System Events)." % (event, function))


try:
    projects  # noqa: B018, F821 - defined only inside CODESYS
except NameError:
    pass  # imported outside CODESYS (TwinForge's tests)
else:
    main()
