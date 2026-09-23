"""Derived type (DDT) capture: structure, array bounds, and cross-references."""
from pathlib import Path

import pytest

from twinforge.parsers.control_expert import capture_bytes, capture_file, parse_project, parse_projects


def project(body: str):
    return parse_project(capture_bytes(
        (f'<ZEFExchangeFile><contentHeader name="Example"/>{body}</ZEFExchangeFile>').encode(),
        name="project.xef",
    ))


def test_plain_scalar_members_resolve_cleanly():
    result = project('''
      <DDTSource DDTName="T_CMD"><comment>Command word</comment>
        <structure>
          <variables name="AUTHCMD" typeName="BYTE"><comment>auth</comment></variables>
          <variables name="ENABLE" typeName="BOOL"/>
        </structure>
      </DDTSource>
    ''')
    datatype = result.controller.datatypes["T_CMD"]
    assert datatype.description == "Command word"
    assert [(m.name, m.data_type_name, m.description) for m in datatype.members] == [
        ("AUTHCMD", "BYTE", "auth"), ("ENABLE", "BOOL", None),
    ]
    assert all(m.dimension is None and m.data_type is None for m in datatype.members)
    assert not any(d.code in {"unresolved_type", "unresolved_array_type", "invalid_array_bounds"}
                   for d in result.diagnostics)


def test_array_member_bounds_are_retained_lexically_not_zero_based():
    result = project('''
      <DDTSource DDTName="T_HEALTH">
        <structure>
          <variables name="DEVICE_CNX_HEALTH" typeName="ARRAY[257..384] OF BOOL"/>
        </structure>
      </DDTSource>
    ''')
    member = result.controller.datatypes["T_HEALTH"].members[0]
    assert member.data_type_name == "BOOL"
    assert member.dimension == "257..384"  # Lower bound preserved, not renumbered from 0.
    assert any(d.code == "unresolved_array_type" for d in result.diagnostics)
    assert not any(d.code == "unresolved_type" for d in result.diagnostics)


def test_invalid_array_bounds_is_diagnosed():
    result = project('''
      <DDTSource DDTName="T_BAD">
        <structure><variables name="X" typeName="ARRAY[9..1] OF BOOL"/></structure>
      </DDTSource>
    ''')
    member = result.controller.datatypes["T_BAD"].members[0]
    assert member.dimension is None
    assert any(d.code == "invalid_array_bounds" for d in result.diagnostics)


def test_nested_datatype_reference_resolves_regardless_of_declaration_order():
    # T_OUTER is declared before T_INNER, its own dependency -- a forward
    # reference the two-pass member resolution must still handle.
    result = project('''
      <DDTSource DDTName="T_OUTER">
        <structure><variables name="HEALTH" typeName="T_INNER"/></structure>
      </DDTSource>
      <DDTSource DDTName="T_INNER">
        <structure><variables name="FLAG" typeName="BOOL"/></structure>
      </DDTSource>
    ''')
    outer = result.controller.datatypes["T_OUTER"]
    member = outer.members[0]
    assert member.data_type is result.controller.datatypes["T_INNER"]
    assert not any(d.code == "unresolved_type" for d in result.diagnostics)


def test_unsupported_member_type_is_diagnosed():
    result = project('''
      <DDTSource DDTName="T_X">
        <structure><variables name="M" typeName="TON"/></structure>
      </DDTSource>
    ''')
    member = result.controller.datatypes["T_X"].members[0]
    assert member.data_type is None
    assert any(d.code == "unresolved_type" for d in result.diagnostics)


def test_duplicate_datatype_name_is_ambiguous_and_member_names_scope_per_datatype():
    result = project('''
      <DDTSource DDTName="DUP"><structure><variables name="IN" typeName="BOOL"/></structure></DDTSource>
      <DDTSource DDTName="DUP"><structure><variables name="IN" typeName="BOOL"/></structure></DDTSource>
      <DDTSource DDTName="OTHER"><structure><variables name="IN" typeName="BOOL"/></structure></DDTSource>
    ''')
    assert list(result.controller.datatypes) == ["DUP", "OTHER"]  # Second DUP rejected, not overwritten.
    assert sum(d.code == "ambiguous_identity" for d in result.diagnostics) == 1
    # "IN" repeats across two distinct datatypes without conflict.
    assert result.controller.datatypes["OTHER"].members[0].name == "IN"


def test_top_level_tag_typed_with_a_known_datatype_is_resolved():
    result = project('''
      <DDTSource DDTName="T_CMD"><structure><variables name="F" typeName="BOOL"/></structure></DDTSource>
      <dataBlock><variables name="Cmd" typeName="T_CMD"/></dataBlock>
    ''')
    assert not any(d.code == "unresolved_type" for d in result.diagnostics)


@pytest.mark.parametrize("filename", ["estradege_m580-safety.xef"])
def test_optional_real_m580_safety_datatypes(filename):
    path = Path(__file__).resolve().parents[1] / "reference" / "control-expert" / filename
    if not path.exists():
        pytest.skip("Local M580 safety reference unavailable")
    result, = parse_projects(capture_file(path))
    controller = result.controller
    assert len(controller.datatypes) == 13
    module_health = controller.datatypes["T_BMENOC0321"]
    array_members = [m for m in module_health.members if m.dimension]
    nested_members = [m for m in module_health.members if m.data_type is not None]
    assert len(array_members) == 5
    assert [m.name for m in nested_members] == ["DID_HEALTH"]
    assert nested_members[0].data_type is not None and nested_members[0].data_type.name == "T_NOCDIO_HEALTH"
    # No DDT member type is unresolved. The remaining unresolved_type reports are
    # resource variables and DFB local variables typed by library device types
    # this export does not define.
    datatype_names = set(controller.datatypes)
    assert not any(
        d.code == "unresolved_type" and d.message.split(".")[0] in datatype_names for d in result.diagnostics)
    # The SAFE task is an ordinarily-scheduled periodic task, already handled
    # by existing generic (name-agnostic) task logic -- no special casing.
    safe = controller.tasks["SAFE"]
    assert safe.task_type == "periodic"
    assert len(safe.scheduled_programs) == len(safe.scheduled_program_names) == 6
