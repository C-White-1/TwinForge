"""Standard Universal I/O Device DDTs resolve from Schneider's own manuals, not project evidence."""
from pathlib import Path

import pytest

from twinforge.analysis.graphical_bindings import member_path_context
from twinforge.model import Controller, Datatype, DatatypeMember, Identity
from twinforge.parsers.control_expert import capture_bytes, capture_file, parse_project, parse_projects
from twinforge.schema.control_expert.device_ddt_catalog import DEVICE_DDT_CATALOG
from twinforge.schema.control_expert.mapping import BASIC_MAPPING


def _context(controller=None):
    return member_path_context(controller or Controller(identity=Identity()), [], BASIC_MAPPING.array_pattern)


def test_every_catalog_type_is_reachable_and_self_consistent():
    context = _context()
    for name, definition in DEVICE_DDT_CATALOG.items():
        datatype = context.datatypes[name.casefold()]
        assert isinstance(datatype, Datatype) and datatype.name == name
        assert [m.name for m in datatype.members] == [m.name for m in definition.members]
        # Any member that names another catalog type must itself be a catalog entry
        # (a nested struct, e.g. ANA -> T_U_ANA_VALUE_IN), not a dangling reference.
        for member in datatype.members:
            data_type_name = member.data_type_name or ""
            if data_type_name.isupper() and data_type_name.startswith("T_U_"):
                assert data_type_name.casefold() in context.datatypes


@pytest.mark.parametrize(("type_name", "path", "expected_type"), [
    ("T_U_DIS_STD_CH_IN", ".VALUE", "EBOOL"),
    ("T_U_DIS_STD_CH_IN", ".CH_HEALTH", "BOOL"),
    ("T_U_DIS_STD_CH_OUT", ".VALUE", "EBOOL"),
    ("T_U_ANA_STD_CH_IN", ".ANA.VALUE", "INT"),
    ("T_U_ANA_STD_CH_IN", ".CH_WARNING", "BOOL"),
    ("T_U_ANA_TEMP_CH_IN", ".CJC_VALUE", "INT"),
    ("T_U_ANA_SIS_CH_IN", ".VALUE", "INT"),
    ("T_U_ANA_SIS_CH_IN", ".OOR", "BOOL"),
    ("T_U_DIS_SIS_CH_IN", ".SC", "BOOL"),
    ("T_U_DIS_SIS_CH_ROUT", ".CH_FBST", "BOOL"),
])
def test_documented_members_resolve_by_type(type_name, path, expected_type):
    from twinforge.analysis.member_paths import resolve_member_path
    from twinforge.model import Tag
    from twinforge.schema.control_expert.expressions import EXPRESSION_SPEC
    context = _context()
    tag = Tag(name="X", data_type=type_name)  # no data_type_definition: not project-captured
    result = resolve_member_path(
        f"X{path}", tag, identifier=EXPRESSION_SPEC.identifier, array_pattern=context.array_pattern,
        datatypes=context.datatypes, function_blocks=context.function_blocks,
        library_interfaces=context.library_interfaces)
    assert result.status == "resolved", result.detail
    assert result.path is not None and result.path.type_name == expected_type


def test_project_captured_definition_takes_precedence_over_the_catalog():
    # A real DDTSource of the same name is real project evidence and must win,
    # even though Device DDT names are not normally expected to collide with one.
    project_defined = Datatype(name="T_U_DIS_STD_CH_IN", members=[DatatypeMember(name="ONLY", data_type_name="INT")])
    controller = Controller(identity=Identity())
    controller.add_datatype(project_defined)
    context = _context(controller)
    assert [m.name for m in context.datatypes["t_u_dis_std_ch_in"].members] == ["ONLY"]


def test_catalog_is_never_added_to_the_parsed_projects_own_datatypes():
    result = parse_project(capture_bytes((
        '<ZEFExchangeFile><contentHeader name="E"/>'
        '<dataBlock><variables name="ch" typeName="T_U_DIS_STD_CH_IN"/></dataBlock>'
        '<logicConf><resource><taskDesc task="MAST" taskType="cyclic">'
        '<sectionDesc name="s"/></taskDesc></resource></logicConf>'
        '<program><identProgram name="s" task="MAST"/><FBDSource><networkFBD>'
        '<FFBBlock instanceName="B" typeName="X"><descriptionFFB>'
        '<inputVariable formalParameter="IN0" effectiveParameter="ch.VALUE"/>'
        '</descriptionFFB></FFBBlock></networkFBD></FBDSource></program></ZEFExchangeFile>').encode(),
        name="p.xef"))
    assert "T_U_DIS_STD_CH_IN" not in result.controller.datatypes
    routine = result.controller.programs["s"].main_routine
    assert routine is not None
    pin = routine.graphical_diagrams[0].objects[0].pins[0]
    assert pin.binding_kind == "declared_member_path"
    assert pin.member_path is not None and pin.member_path.type_name == "EBOOL"


def test_real_fixture_resolves_universal_io_channel_members_when_available():
    path = Path("reference/control-expert/estradege_m580-safety.xef")
    if not path.exists():
        pytest.skip("reference fixture absent")
    result, = parse_projects(capture_file(path))
    resolved: dict[str, str | None] = {}
    for container in [*result.controller.programs.values(), *result.controller.add_on_instructions.values()]:
        for routine in container.routines.values():
            for diagram in routine.graphical_diagrams:
                for obj in diagram.objects:
                    for pin in obj.pins:
                        if pin.member_path is not None:
                            resolved[pin.expression] = pin.member_path.type_name
    # Unaffected by the catalog: a project-defined Function Block (P_BREAKER), already resolved before it.
    assert resolved["00BBA01GS001.CLOSED"] == "BOOL"
    # These only resolve once the catalog supplements the missing Device DDTs.
    assert resolved["GEST[2]"] == "INT"
    assert len(resolved) >= 400  # distinct expressions; 688 pin occurrences collapse into fewer unique strings
