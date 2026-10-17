"""The text handling of the CODESYS script that binds TwinForge's event handlers.

The script runs inside CODESYS's IronPython; its export and import cannot run
here, but finding the handlers and editing the native Task Configuration
export can. The layouts below are those of CODESYS's own exports (V3.5 SP22
Patch 3): docs/experiments/codesys-first-cycle.md.
"""
import ast
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

from twinforge.exporters.plcopen_codesys import FIRST_CYCLE_HANDLER

SCRIPT = Path(__file__).parents[1] / "examples/CODESYS/scripts/bind_system_events.py"
_spec = importlib.util.spec_from_file_location("bind_system_events", SCRIPT)
assert _spec is not None and _spec.loader is not None
script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(script)  # outside CODESYS: does nothing


def _export(event_list: str) -> str:
    """A native Task Configuration export, cut down around its event list."""
    return (
        '<ExportFile>\n  <StructuredView Guid="{d9b2b2cc-ea99-4c3b-aa42-1e5c49e65b84}">\n'
        '<Single Name="Object" Type="{ae1de277-a207-4a28-9efb-456c06bd52f3}" Method="IArchivable">\n'
        '  <Single Name="StackSize" Type="uint">0</Single>\n'
        f"  {event_list}\n"
        '  <List2 Name="alTaskGroups">\n'
        '    <Single Type="{609a42d4-f974-4041-8548-f80e229ca5ed}" Method="IArchivable">\n'
        '      <Single Name="Groupname" Type="string">IEC-Tasks</Single>\n'
        "    </Single>\n"
        "  </List2>\n"
        "</Single>  </StructuredView>\n</ExportFile>\n"
    )


# An imported project, which never had a handler.
NEVER_BOUND = _export('<Null Name="alSysEventList" />')
# A project with StartDone bound by hand (Add Event Handler).
START_DONE = _export(
    '<List2 Name="alSysEventList">\n'
    '    <Single Type="{357faaca-a279-4878-8c2f-ec7c49896fa3}" Method="IArchivable">\n'
    '      <Single Name="Eventname" Type="string">StartDone</Single>\n'
    '      <Single Name="FunctionToCall" Type="string">OnStartDone</Single>\n'
    '      <Single Name="Position" Type="short">1</Single>\n'
    "    </Single>\n"
    "  </List2>")


def _entries(text: str) -> list[dict[str, str]]:
    root = ET.fromstring(text)
    (events,) = [e for e in root.iter() if e.get("Name") == "alSysEventList"]
    return [{field.get("Name") or "": field.text or "" for field in entry} for entry in events]


def test_the_exporters_handler_is_found_by_its_name():
    names = ["Library Manager", "New_POU", FIRST_CYCLE_HANDLER, "TF_EndOfScan", "MAST", "ControllerTags"]

    assert script.handlers(names) == [("PrepareStart", FIRST_CYCLE_HANDLER)]
    assert script.handlers(["TF_OnSomethingElse", "OnPrepareStart"]) == []  # not ours, or no known entry


def test_an_imported_project_gets_the_binding():
    edited, added = script.with_events(NEVER_BOUND, [("PrepareStart", FIRST_CYCLE_HANDLER)])

    assert added == ["PrepareStart"]
    (entry,) = _entries(edited)
    assert entry["Eventname"] == "PrepareStart" and entry["FunctionToCall"] == FIRST_CYCLE_HANDLER
    assert entry["stEventId"] == "CmpApp.EventIDs.EVT_PrepareStart" and entry["ParameterStruct"] == "CmpApp.EVTPARAM_CmpApp"
    assert (entry["Active"], entry["Position"]) == ("True", "0")
    assert script.bound_events(edited) == ["PrepareStart"]
    assert edited.replace(edited[edited.index("<List2 Name=\"alSysEventList\">"):edited.index("</List2>") + 8],
                          '<Null Name="alSysEventList" />') == NEVER_BOUND  # nothing else changes


def test_existing_bindings_are_kept_and_the_new_one_goes_last():
    edited, added = script.with_events(START_DONE, [("PrepareStart", FIRST_CYCLE_HANDLER)])

    assert added == ["PrepareStart"]
    assert [(e["Eventname"], e["FunctionToCall"], e["Position"]) for e in _entries(edited)] == [
        ("StartDone", "OnStartDone", "1"), ("PrepareStart", FIRST_CYCLE_HANDLER, "2")]


def test_running_it_again_changes_nothing():
    once, _ = script.with_events(NEVER_BOUND, [("PrepareStart", FIRST_CYCLE_HANDLER)])

    assert script.with_events(once, [("PrepareStart", FIRST_CYCLE_HANDLER)]) == (once, [])


def test_an_unknown_layout_is_refused_rather_than_guessed():
    try:
        script.with_events(_export(""), [("PrepareStart", FIRST_CYCLE_HANDLER)])
    except ValueError as error:
        assert "alSysEventList" in str(error)
    else:
        raise AssertionError("expected ValueError")


def test_the_script_stays_python_2_compatible():
    # CODESYS runs it in IronPython 2.7: no f-strings or annotations.
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    nodes = list(ast.walk(tree))
    assert not [n for n in nodes if isinstance(n, ast.JoinedStr)]
    functions = [n for n in nodes if isinstance(n, ast.FunctionDef)]
    assert not [f.name for f in functions if f.returns or any(a.annotation for a in f.args.args)]
    assert any(isinstance(n, ast.ImportFrom) and n.module == "__future__" for n in nodes)
