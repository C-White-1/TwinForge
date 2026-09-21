"""Index/member/bit-select paths resolve only when every step is proven by a definition."""
from pathlib import Path

import pytest

from twinforge.analysis.member_paths import resolve_member_path
from twinforge.model import AddOnInstructionParameter, Datatype, DatatypeMember, Tag
from twinforge.model.library_interface import LibraryInterface, LibraryParameter
from twinforge.parsers.control_expert import capture_bytes, capture_file, parse_project, parse_projects
from twinforge.schema.control_expert.expressions import EXPRESSION_SPEC
from twinforge.schema.control_expert.mapping import BASIC_MAPPING

IDENT = EXPRESSION_SPEC.identifier
ARRAY = BASIC_MAPPING.array_pattern


def _types():
    inner = Datatype(name="Inner", members=[DatatypeMember(name="Flags", data_type_name="WORD")])
    outer = Datatype(name="Outer", members=[
        DatatypeMember(name="Cfg", data_type_name="Inner", data_type=inner),
        DatatypeMember(name="Vals", data_type_name="INT", dimension="5..7"),
        DatatypeMember(name="Name", data_type_name="STRING"),
    ])
    return {"inner": inner, "outer": outer}


def _resolve(expression, tag, *, function_blocks=None, library_interfaces=None):
    return resolve_member_path(
        expression, tag, identifier=IDENT, array_pattern=ARRAY, datatypes=_types(),
        function_blocks=function_blocks or {}, library_interfaces=library_interfaces or {})


def _outer_tag():
    return Tag(name="P", data_type="Outer", data_type_definition=_types()["outer"])


@pytest.mark.parametrize(("expression", "steps", "type_name"), [
    ("P.Name", (".Name",), "STRING"),
    ("p.cfg.flags", (".Cfg", ".Flags"), "WORD"),  # case-insensitive, nested DDT
    ("P.Cfg.Flags.15", (".Cfg", ".Flags", ".15"), "BOOL"),  # bit of a WORD
    ("P.Vals[5]", (".Vals", "[5]"), "INT"),  # non-zero lower bound kept as declared
    ("P.Vals[7]", (".Vals", "[7]"), "INT"),
])
def test_proven_paths_resolve(expression, steps, type_name):
    result = _resolve(expression, _outer_tag())
    assert result.status == "resolved", result.detail
    assert result.path is not None
    assert (result.path.steps, result.path.type_name) == (steps, type_name)


@pytest.mark.parametrize(("expression", "status"), [
    ("P.Vals[4]", "index_out_of_bounds"),  # below the declared 5..7 lower bound (not zero-based)
    ("P.Vals[8]", "index_out_of_bounds"),
    ("P.Cfg.Flags.16", "index_out_of_bounds"),
    ("P.Nope", "unresolved"),
    ("P.Vals", "resolved"),  # a whole array is a proven path
    ("P.Vals.1", "unresolved"),  # member/bit of an un-indexed array
    ("P.Name.1", "unresolved"),  # bit select on a non-integer type
    ("P.Cfg[1]", "unresolved"),  # index on a non-array
    ("P.Vals[i]", "unresolved"),  # non-literal index cannot be bounds-checked
    ("P.Vals[5, 6]", "unresolved"),
    ("P", "unresolved"),  # no steps: not a path
    ("P.", "unresolved"),
])
def test_unproven_or_out_of_range_paths(expression, status):
    assert _resolve(expression, _outer_tag()).status == status


def test_untyped_or_missing_base_never_resolves():
    assert _resolve("X.a", None).status == "unresolved"
    assert _resolve("X.a", Tag(name="X", data_type=None)).status == "unresolved"
    assert _resolve("X.a", Tag(name="X", data_type="Unknown")).status == "unresolved"


def test_array_tag_bounds_and_element_datatype_come_from_the_declaration():
    tag = Tag(name="A", data_type="ARRAY[1..3] OF Outer", data_type_definition=_types()["outer"])
    assert _resolve("A[3].Name", tag).status == "resolved"
    assert _resolve("A[0].Name", tag).status == "index_out_of_bounds"
    assert _resolve("A.Name", tag).status == "unresolved"


def test_function_block_and_library_members_use_declared_parameters_only():
    fb = {"myfb": {"out": AddOnInstructionParameter(name="OUT", data_type="WORD")}}
    lib = {"ton": LibraryInterface("TON", "EFB", [LibraryParameter("Q", "BOOL", "output")])}
    assert _resolve("I.OUT.3", Tag(name="I", data_type="MyFB"), function_blocks=fb).status == "resolved"
    assert _resolve("I.Hidden", Tag(name="I", data_type="MyFB"), function_blocks=fb).status == "unresolved"
    assert _resolve("T.Q", Tag(name="T", data_type="TON"), library_interfaces=lib).status == "resolved"
    assert _resolve("T.X", Tag(name="T", data_type="TON"), library_interfaces=lib).status == "unresolved"


def _fbd_project(expressions):
    pins = "".join(f'<inputVariable formalParameter="IN{i}" effectiveParameter="{e}"/>'
                   for i, e in enumerate(expressions))
    return parse_project(capture_bytes((
        '<ZEFExchangeFile><contentHeader name="E"/>'
        '<DDTSource DDTName="Pair"><structure><variables name="A" typeName="INT"/>'
        '<variables name="W" typeName="ARRAY[2..3] OF WORD"/></structure></DDTSource>'
        '<dataBlock><variables name="p" typeName="Pair"/><variables name="dup" typeName="Pair"/>'
        '<variables name="DUP" typeName="Pair"/></dataBlock>'
        '<logicConf><resource><taskDesc task="MAST" taskType="cyclic">'
        '<sectionDesc name="s"/></taskDesc></resource></logicConf>'
        '<program><identProgram name="s" task="MAST"/><FBDSource><networkFBD>'
        f'<FFBBlock instanceName="B" typeName="X"><descriptionFFB>{pins}</descriptionFFB></FFBBlock>'
        '</networkFBD></FBDSource></program></ZEFExchangeFile>').encode(), name="p.xef"))


def test_pins_bind_paths_to_the_base_symbol_without_joining_shared_variable_groups():
    result = _fbd_project(["p.A", "p.W[3].5", "P.W[9]", "dup.A", "p.Nope"])
    routine = result.controller.programs["s"].main_routine
    assert routine is not None
    diagram = routine.graphical_diagrams[0]
    pins = {pin.name: pin for pin in diagram.objects[0].pins}
    first, second = pins["IN0"], pins["IN1"]
    assert first.binding_kind == "declared_member_path"
    assert first.target_tag is result.controller.tags["p"]
    assert first.member_path is not None
    assert (first.member_path.steps, first.member_path.type_name) == ((".A",), "INT")
    assert second.member_path is not None and second.member_path.steps == (".W", "[3]", ".5")
    assert pins["IN2"].binding_kind == "member_path_out_of_bounds" and pins["IN2"].member_path is None
    assert pins["IN3"].binding_kind == "unresolved_expression"  # ambiguous base is never guessed
    assert pins["IN4"].binding_kind == "unresolved_expression"
    codes = [d.code for d in result.diagnostics]
    assert codes.count("pin_member_path_out_of_bounds") == 1
    assert codes.count("unresolved_pin_expression") == 2
    assert diagram.shared_variables == []


def test_real_fixtures_resolve_member_paths_when_available():
    root = Path("reference/control-expert")
    if not (root / "estradege_m580-safety.xef").exists():
        pytest.skip("reference fixtures absent")
    resolved: dict[str, str | None] = {}
    for name in ("estradege_m340.xef", "estradege_m580-safety.xef"):
        for result in parse_projects(capture_file(root / name)):
            containers = [*result.controller.programs.values(), *result.controller.add_on_instructions.values()]
            for container in containers:
                for routine in container.routines.values():
                    for diagram in routine.graphical_diagrams:
                        for obj in diagram.objects:
                            for pin in obj.pins:
                                assert pin.binding_kind != "member_path_out_of_bounds", pin.expression
                                if pin.member_path is not None:
                                    resolved[pin.expression] = pin.member_path.type_name
    assert resolved["GEST[1].0"] == "BOOL"
    assert resolved["GEST[2]"] == "INT"
    assert resolved["T1.STAT.6"] == "BOOL"
    assert len(resolved) >= 10
