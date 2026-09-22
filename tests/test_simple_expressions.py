"""Tier 1: a single evidenced binary operator between two independently proven operands."""
import pytest

from twinforge.analysis.simple_expressions import resolve_binary_expression, split_binary_expression
from twinforge.model import AddOnInstructionParameter, Datatype, DatatypeMember, Tag
from twinforge.schema.control_expert.expressions import EXPRESSION_SPEC


@pytest.mark.parametrize(("expression", "left", "operator", "right"), [
    ("Buffer + 1", "Buffer", "+", "1"),
    ("Buffer+1", "Buffer", "+", "1"),
    ("TR_H -0.5", "TR_H", "-", "0.5"),          # asymmetric spacing, real corpus shape
    ("PM5320.ACPT/1000.0", "PM5320.ACPT", "/", "1000.0"),
    ("Sim_Conso_Qvap_TG*0.1", "Sim_Conso_Qvap_TG", "*", "0.1"),
    ("Mode=8", "Mode", "=", "8"),
    ("Mode <>2", "Mode", "<>", "2"),
    ("StepNo>=4", "StepNo", ">=", "4"),
    ("StepNo <2", "StepNo", "<", "2"),
    ("PV1 > 990.0", "PV1", ">", "990.0"),
])
def test_split_recognizes_every_evidenced_operator_shape(expression, left, operator, right):
    assert split_binary_expression(expression) == (left, operator, right)


@pytest.mark.parametrize("expression", [
    "GEST[2] and 16#0F",          # word-form logical operator: zero recognized operators
    "Reset or GQC=65535",         # "or" isn't recognized; the lone "=" leaves "Reset or GQC" as an unclassifiable left side later, but split itself still succeeds here
    "RE(Sim_W505_STOP)",          # function call: zero recognized operators
    "-3",                          # leading operator -> empty left side
    "-t#5s",                       # same, for a signed literal
    "'{1.101}SYS'",                 # never split inside a string literal
    "ADDMX (IN := '0.2.0{10.24.9.31}')",  # ":=" must not be read as "="
    "A = B = C",                    # more than one recognized operator
    "",
])
def test_split_rejects_unsupported_or_ambiguous_shapes(expression):
    result = split_binary_expression(expression)
    if expression == "Reset or GQC=65535":
        assert result == ("Reset or GQC", "=", "65535")  # splits; classification is what fails
    else:
        assert result is None


def _types():
    outer = Datatype(name="Outer", members=[DatatypeMember(name="Vals", data_type_name="INT", dimension="5..7")])
    return {"outer": outer}


def _symbols() -> dict[str, Tag | AddOnInstructionParameter]:
    return {"buffer": Tag(name="Buffer", data_type="WORD"),
            "p": Tag(name="P", data_type="Outer", data_type_definition=_types()["outer"])}


class _Context:
    def __init__(self):
        self.array_pattern = r"ARRAY\[(-?\d+)\.\.(-?\d+)\] OF ([A-Za-z_][A-Za-z_0-9]*)"
        self.datatypes = _types()
        self.function_blocks: dict = {}
        self.library_interfaces: dict = {}


def _resolve(expression, symbols=None, ambiguous=None, member_paths=None):
    return resolve_binary_expression(
        expression, symbols if symbols is not None else _symbols(), ambiguous or set(),
        EXPRESSION_SPEC.identifier, EXPRESSION_SPEC.literals,
        member_paths if member_paths is not None else _Context())


def test_symbol_and_literal_operands_resolve():
    symbols = _symbols()
    result = resolve_binary_expression(
        "Buffer + 1", symbols, set(), EXPRESSION_SPEC.identifier, EXPRESSION_SPEC.literals, _Context())
    assert result is not None
    assert result.operator == "+"
    assert result.left.kind == "declared_symbol" and result.left.target_tag is symbols["buffer"]
    assert result.right.kind == "literal" and result.right.text == "1"


def test_member_path_operand_resolves():
    result = _resolve("P.Vals[5] > 0")
    assert result is not None
    assert result.left.kind == "declared_member_path"
    assert result.left.member_path is not None and result.left.member_path.steps == (".Vals", "[5]")
    assert result.right.kind == "literal"


@pytest.mark.parametrize("expression", [
    "Buffer + missing",       # right operand not declared
    "missing + Buffer",       # left operand not declared
    "P.Vals[4] > 0",           # left operand is a proven-unprovable index (out of bounds)
    "GEST[2] and 16#0F",       # no recognized operator at all
])
def test_any_unresolved_operand_leaves_the_whole_expression_unresolved(expression):
    assert _resolve(expression) is None


def test_ambiguous_operand_is_never_guessed():
    symbols = {"dup": Tag(name="dup", data_type="INT")}
    assert _resolve("dup + 1", symbols=symbols, ambiguous={"dup"}) is None


def test_no_member_path_context_still_resolves_symbol_and_literal_operands():
    result = _resolve("Buffer + 1", member_paths=None)
    assert result is not None


def test_real_fixture_resolves_tier1_binary_expressions_when_available():
    from pathlib import Path
    from twinforge.parsers.control_expert import capture_file, parse_projects

    path = Path("reference/control-expert/estradege_m580-safety.xef")
    if not path.exists():
        pytest.skip("reference fixture absent")
    result, = parse_projects(capture_file(path))
    resolved: dict[str, str] = {}
    for container in [*result.controller.programs.values(), *result.controller.add_on_instructions.values()]:
        for routine in container.routines.values():
            for diagram in routine.graphical_diagrams:
                for obj in diagram.objects:
                    for pin in obj.pins:
                        if pin.binary_expression is not None:
                            resolved[pin.expression] = pin.binary_expression.operator
                    if obj.operand_binary_expression is not None:
                        resolved[obj.operand] = obj.operand_binary_expression.operator
    assert resolved["00MAA10CT001.Mode=8"] == "="
    assert resolved["TR_H -0.5"] == "-"
    assert resolved["PM5320.ACPT/1000.0"] == "/"
    assert resolved["00MAV10AP002.Mode <>2"] == "<>"
    # Explicitly out of Tier 1 scope: not a binary expression at all.
    assert "GEST[2] and 16#0F" not in resolved
    assert "RE(Sim_W505_STOP)" not in resolved
    assert len(resolved) >= 40
