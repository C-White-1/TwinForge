"""User-made Machine Expert – Basic 3.0 fixtures in examples/machine_expert_basic/.

Each file was drawn by hand in the editor to settle one question in
docs/architecture/machine-expert-basic-smbp-format.md; these tests pin what
the parser and the grid-against-IL check say about them, including that
every built ladder network is equivalent to its rung's Instruction List.
"""
import ast
import importlib.util
import itertools
from pathlib import Path
import subprocess
import sys

import pytest

from twinforge.analysis.tag_dependencies import build_tag_dependency_graph
from twinforge.model import LadderInstruction, LadderOperation, LadderParallel, LadderSeries
from twinforge.parsers.machine_expert_basic import capture_file, parse_project

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "examples/machine_expert_basic"
ALL = sorted(FIXTURES.glob("*.smbp"))
# Fixtures whose rungs use elements with no portable LadderOperation.
WITH_UNSUPPORTED: set[str] = set()
# Fixtures whose timers cannot become IEC instances (Retentive, Dynamic Preset).
WITH_UNCONVERTED_TIMER = {"05c_timer"}

_spec = importlib.util.spec_from_file_location("check_smbp_grid_vs_il", ROOT / "examples/check_smbp_grid_vs_il.py")
assert _spec is not None and _spec.loader is not None
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)

_SHORT = {
    LadderOperation.NORMALLY_OPEN_CONTACT: "NO", LadderOperation.NORMALLY_CLOSED_CONTACT: "NC",
    LadderOperation.COIL: "COIL", LadderOperation.SET_COIL: "SET", LadderOperation.RESET_COIL: "RESET",
    LadderOperation.BLOCK_OUTPUT_REFERENCE: "OUT",
    LadderOperation.POSITIVE_TRANSITION_CONTACT: "P", LadderOperation.NEGATIVE_TRANSITION_CONTACT: "N",
    LadderOperation.NEGATED_COIL: "NCOIL",
}


def _parse(name: str):
    return parse_project(capture_file(FIXTURES / name))


def _routine(result):
    (program,) = result.controller.programs.values()
    (routine,) = program.routines.values()
    return routine


def _user_tags(result) -> dict[str, tuple[str | None, dict]]:
    return {name: (tag.description, tag.metadata) for name, tag in result.controller.tags.items()
            if tag.metadata["source_symbol_table"] not in ("SystemBits", "SystemWords")}


def _shape(series: LadderSeries) -> str:
    """Compact rendering: `[a | b]` is a parallel, `.PIN` a block input pin."""
    parts = []
    for element in series.elements:
        if isinstance(element, LadderParallel):
            parts.append("[" + " | ".join(_shape(branch) for branch in element.branches) + "]")
        else:
            if element.expression is not None:  # COMPARISON / ASSIGNMENT: the typed tree
                label = "CMP" if element.operation is LadderOperation.COMPARISON else "ASSIGN"
                parts.append(f"{label}({element.expression.render()})")
                continue
            label = _SHORT.get(element.operation) or element.source_mnemonic
            parts.append(f"{label}({element.operand})")
    return " ".join(parts)


def _shapes(name: str) -> list[str | None]:
    return [_shape(rung.network) if rung.network else None for rung in _routine(_parse(name)).ladder_rungs]


def test_fixture_set_is_present():
    assert len(ALL) == 16


@pytest.mark.parametrize("path", ALL, ids=lambda path: path.stem)
def test_every_fixture_parses_with_only_expected_diagnostics(path: Path):
    result = parse_project(capture_file(path))

    if result.encrypted:
        expected = {"encrypted_project"}
    else:
        expected = {"unclassified_content"} | ({"ladder_unsupported_element"} if path.stem in WITH_UNSUPPORTED else set())
        expected |= {"timer_not_converted"} if path.stem in WITH_UNCONVERTED_TIMER else set()
    assert {d.code for d in result.diagnostics} == expected
    assert result.project_version == "3.0.0.0"


@pytest.mark.parametrize(("name", "shapes"), [
    ("01_series.smbp", ["NO(%I0.0) NC(%I0.1) COIL(%Q0.0)"]),
    ("02_parallel.smbp", ["[NO(%I0.0) | NO(%I0.1)] COIL(%Q0.0)"]),
    ("03_nested.smbp", ["NO(%I0.0) [NO(%I0.1) | NO(%I0.2) NO(%I0.3)] COIL(%Q0.0)"]),
    # Same logic as 03 drawn with the contact moved one column: same network.
    ("12_edited.smbp", ["NO(%I0.0) [NO(%I0.1) | NO(%I0.2) NO(%I0.3)] COIL(%Q0.0)"]),
    ("04_two_outputs.smbp", ["NO(%I0.0) [COIL(%Q0.0) | COIL(%Q0.1)]"]),
    ("05_timer.smbp", ["[NO(%I0.0) Timer(%TM0.IN) | OUT(%TM0.Q) COIL(%Q0.0)]"]),
    # Branches in drawn order, top to bottom then left to right: R (row 0),
    # D (row 1), then on row 2 the CU contact (column 0) before F (column 2).
    ("06_counter.smbp", ["[NO(%I0.1) Counter(%C0.R) | OUT(%C0.D) COIL(%Q0.0) | NO(%I0.0) Counter(%C0.CU) "
                         "| OUT(%C0.F) COIL(%Q0.1)]"]),
    # The counter simulator project: all four pins of %C0, and one contact
    # driving two pins at once (CU+CD of %C1, R+S of %C2).
    ("13_counter_simulation.smbp", [
        "[NO(%I0.2) Counter(%C0.R) | OUT(%C0.E) COIL(%Q0.1) | NO(%I0.3) Counter(%C0.S) | OUT(%C0.D) COIL(%Q0.0) "
        "| NO(%I0.0) Counter(%C0.CU) | OUT(%C0.F) COIL(%Q0.2) | NO(%I0.1) Counter(%C0.CD)]",
        "[NO(%I0.6) Counter(%C1.R) | NO(%I0.5) Counter(%C1.S) | NO(%I0.4) [Counter(%C1.CU) | Counter(%C1.CD)]]",
        "NO(%I0.7) [Counter(%C2.R) | Counter(%C2.S)]",
    ]),
    ("07_compare_operate.smbp", ["CMP(%MW0 > 10) ASSIGN(%MW1 := (%MW1 + 1))"]),
    ("08_edges.smbp", ["P(%I0.0) COIL(%Q0.0)", "N(%I0.1) COIL(%Q0.1)"]),
    # Written in IL, no grid: the network is derived from the IL.
    ("10_il_only.smbp", ["NO(%I0.0) NO(%I0.1) COIL(%Q0.0)"]),
])
def test_network_shapes_match_the_drawn_rungs(name: str, shapes: list[str | None]):
    assert _shapes(name) == shapes


def test_rung_text_is_never_instruction_list():
    # LadderRung.text means Logix RLL elsewhere in TwinForge.
    for path in ALL:
        for program in parse_project(capture_file(path)).controller.programs.values():
            for routine in program.routines.values():
                assert all(rung.text is None for rung in routine.ladder_rungs)


def test_symbols_from_io_memory_and_counter_tables():
    tags = _user_tags(_parse("09_symbols.smbp"))

    assert tags == {
        "START_PB": ("Start push button", {"source_symbol_table": "DigitalInputs", "source_memory_address": "%I0.0"}),
        "MOTOR_RUN": ("Motor contactor", {"source_symbol_table": "DigitalOutputs", "source_memory_address": "%Q0.0"}),
        "RUN_LATCH": (None, {"source_symbol_table": "MemoryBits", "source_memory_address": "%M0"}),
        "PART_COUNT": (None, {"source_symbol_table": "Counters", "source_memory_address": "%C0",
                              "function_block_semantics": "machine-expert-basic.counter",
                              "iec_function_block_inputs": {"PV": "9999"}}),
    }


def test_instruction_list_rung_keeps_its_il_in_source():
    routine = _routine(_parse("10_il_only.smbp"))

    assert routine.language == "IL"
    assert routine.ladder_rungs[0].instruction_list == ["LD    %I0.0", "AND   %I0.1", "ST    %Q0.0"]
    rung = routine.ladder_rungs[0]
    lines = next(child for child in rung.source_extensions[0].root.children if child.name == "InstructionLines")
    assert [entry.children[0].text for entry in lines.children] == ["LD    %I0.0", "AND   %I0.1", "ST    %Q0.0"]


def test_operands_use_declared_symbols_and_feed_tag_dependencies():
    result = _parse("09_symbols.smbp")
    assert _shapes("09_symbols.smbp") == ["[NO(START_PB) | NO(%I0.1)] COIL(MOTOR_RUN)"]

    graph = build_tag_dependency_graph(result.controller)

    assert sorted((ref.tag_name, ref.access.value) for ref in graph.references) == [
        ("MOTOR_RUN", "write"), ("START_PB", "read")]
    # The unnamed input is kept as evidence, not dropped.
    assert [ref.operand for ref in graph.unresolved_references] == ["%I0.1"]


def test_expression_variables_are_dependency_evidence():
    graph = build_tag_dependency_graph(_parse("07_compare_operate.smbp").controller)

    # The words are unnamed, so they stay unresolved evidence (like %I0.1 in
    # 09_symbols) rather than being dropped; %MW1 := %MW1 + 1 writes and reads.
    assert [(ref.instruction, ref.operand, ref.argument_position) for ref in graph.unresolved_references] == [
        ("assignment", "%MW1", 0), ("assignment", "%MW1", 1), ("comparison", "%MW0", 0)]


@pytest.mark.parametrize(("name", "pins"), [
    ("05_timer.smbp", [("function_block_input", ".IN", "write"), ("block_output_reference", ".Q", "read")]),
    ("06_counter.smbp", [("function_block_input", ".R", "write"), ("block_output_reference", ".D", "read"),
                         ("function_block_input", ".CU", "write"), ("block_output_reference", ".F", "read")]),
])
def test_block_pins_are_dependency_evidence_on_the_instance(name: str, pins: list[tuple[str, str, str]]):
    graph = build_tag_dependency_graph(_parse(name).controller)

    assert sorted((ref.instruction, ref.member_path, ref.access.value) for ref in graph.references) == sorted(pins)
    assert {ref.tag_name for ref in graph.references} == {"%" + ("TM0" if "timer" in name else "C0")}


def test_encrypted_project_keeps_only_its_public_name():
    result = _parse("11_encrypted.smbp")

    assert result.encrypted is True
    # The internal name comes from the project it was copied from, not the file name.
    assert result.controller.name == "01_series"
    assert result.controller.programs == {} and result.controller.tags == {}


# --- every network is equivalent to its rung's IL --------------------------

_OUTPUT_KEYS = {LadderOperation.COIL: "ST", LadderOperation.SET_COIL: "S", LadderOperation.RESET_COIL: "R"}
_EDGE_ATOMS = {"RisingEdge": "R:", "FallingEdge": "F:", "RisingEdgeBlock": "RISING"}


def _address(element: LadderInstruction) -> str:
    """The text the IL uses: an expression box's original text, else the
    `address=` annotation when the operand is a symbol, else the operand."""
    for key in ("source_expression=", "address="):
        annotated = [a.split("=", 1)[1] for a in element.annotations if a.startswith(key)]
        if annotated:
            return annotated[0]
    return element.operand or ""


def _atom(element: LadderInstruction) -> str | None:
    operand = _address(element)
    if element.operation is LadderOperation.BLOCK_OUTPUT_REFERENCE:
        if element.annotations:  # operand is "SYMBOL.PIN"; rebuild "%C0.PIN"
            return f"out:{operand}.{(element.operand or '').rsplit('.', 1)[1]}"
        return f"out:{operand}"
    if element.operation in (LadderOperation.NORMALLY_OPEN_CONTACT, LadderOperation.NORMALLY_CLOSED_CONTACT):
        return operand
    if element.source_mnemonic in _EDGE_ATOMS:
        return _EDGE_ATOMS[element.source_mnemonic] + operand
    if element.source_mnemonic == "Xor":
        return operand
    if element.source_mnemonic == "Comparison" and ":=" not in operand:
        return "[" + checker.norm(operand) + "]"
    return None


def _evaluate(series: LadderSeries, power: bool, env: dict, results: dict) -> bool:
    """Power flow through a network, recording every output it reaches."""
    for element in series.elements:
        if isinstance(element, LadderParallel):
            power = any([_evaluate(branch, power, env, results) for branch in element.branches])
            continue
        kind, operand = element.source_mnemonic, _address(element)
        if element.operation is LadderOperation.FUNCTION_BLOCK_INPUT:
            # operand "instance.pin"; the IL names the instance by address.
            annotated = [a.split("=", 1)[1] for a in element.annotations if a.startswith("address=")]
            instance, _, pin = (element.operand or "").rpartition(".")
            results[("PIN", annotated[0] if annotated else instance, pin)] = power
        elif element.operation in _OUTPUT_KEYS or kind in ("NegativeCoil", "Operation"):
            key = ((_OUTPUT_KEYS[element.operation], operand) if element.operation in _OUTPUT_KEYS
                   else ("STN", operand) if kind == "NegativeCoil" else ("OP", checker.norm(operand)))
            results[key] = results.get(key, False) or power
        elif kind == "Comparison" and ":=" in operand:
            key = ("OP", checker.norm(operand))
            results[key] = results.get(key, False) or power
        elif element.operation is LadderOperation.BLOCK_OUTPUT_REFERENCE:
            power = env[_atom(element)]
        elif element.operation is LadderOperation.NORMALLY_CLOSED_CONTACT:
            power = power and not env[_atom(element)]
        elif kind == "Xor":
            power = power != env[_atom(element)]
        elif kind == "Not":
            power = not power
        else:
            power = power and env[_atom(element)]
    return power


def _atoms(series: LadderSeries) -> set[str]:
    found: set[str] = set()
    for element in series.elements:
        if isinstance(element, LadderParallel):
            for branch in element.branches:
                found |= _atoms(branch)
        elif (atom := _atom(element)) is not None:
            found.add(atom)
    return found


def _grid_rungs():
    for path in ALL:
        for program in parse_project(capture_file(path)).controller.programs.values():
            for routine in program.routines.values():
                for rung in routine.ladder_rungs:
                    if rung.network is not None:
                        yield pytest.param(rung, id=f"{path.stem}-{rung.number}")


@pytest.mark.parametrize("rung", list(_grid_rungs()))
def test_network_is_equivalent_to_instruction_list(rung):
    lines = next(child for child in rung.source_extensions[0].root.children if child.name == "InstructionLines")
    program, il_atoms, il_outputs, _internal, _pins, _outs = checker.parse_il(
        [entry.children[0].text or "" for entry in lines.children])
    atoms = sorted(_atoms(rung.network))
    assert set(atoms) == il_atoms
    reached: dict = {}
    _evaluate(rung.network, True, dict.fromkeys(atoms, False), reached)
    assert set(reached) == il_outputs
    for bits in itertools.product((False, True), repeat=len(atoms)):
        env = dict(zip(atoms, bits))
        network_results: dict = {}
        _evaluate(rung.network, True, env, network_results)
        il_results = checker.run_il(program, env)
        assert {key: network_results.get(key, False) for key in il_outputs} == \
               {key: il_results.get(key, False) for key in il_outputs}, env


def test_every_network_is_checked():
    # 14 grid rungs plus the one IL-only rung (10_il_only).
    assert len(list(_grid_rungs())) == 18


# --- the grid checker script itself ----------------------------------------

def _check(*arguments: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "examples/check_smbp_grid_vs_il.py"), str(FIXTURES), *arguments],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    return ast.literal_eval(completed.stdout.splitlines()[0])


def test_every_grid_rung_matches_its_instruction_list():
    assert _check() == {"match": 17, "il-only": 1}


def test_grid_check_fails_under_the_wrong_vertical_edge_rule():
    outcome = _check("--vertical-on-left")

    assert outcome.get("mismatch", 0) > 0
