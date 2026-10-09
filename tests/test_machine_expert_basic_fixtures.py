"""User-made Machine Expert – Basic 3.0 fixtures in examples/machine_expert_basic/.

Each file was drawn by hand in the editor to settle one question in
docs/architecture/machine-expert-basic-smbp-format.md; these tests pin what
the parser and the grid-against-IL check say about them.
"""
import ast
from pathlib import Path
import subprocess
import sys

import pytest

from twinforge.parsers.machine_expert_basic import capture_file, parse_project

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "examples/machine_expert_basic"
ALL = sorted(FIXTURES.glob("*.smbp"))


def _parse(name: str):
    return parse_project(capture_file(FIXTURES / name))


def _routine(result):
    (program,) = result.controller.programs.values()
    (routine,) = program.routines.values()
    return routine


def _user_tags(result) -> dict[str, tuple[str | None, dict]]:
    return {name: (tag.description, tag.metadata) for name, tag in result.controller.tags.items()
            if tag.metadata["source_symbol_table"] not in ("SystemBits", "SystemWords")}


def test_fixture_set_is_present():
    assert len(ALL) == 15


@pytest.mark.parametrize("path", ALL, ids=lambda path: path.stem)
def test_every_fixture_parses_with_only_expected_diagnostics(path: Path):
    result = parse_project(capture_file(path))

    expected = {"encrypted_project"} if result.encrypted else {"unclassified_content"}
    assert {d.code for d in result.diagnostics} == expected
    assert result.project_version == "3.0.0.0"


def test_series_rung():
    routine = _routine(_parse("01_series.smbp"))

    assert routine.language == "LD"
    assert [rung.text for rung in routine.ladder_rungs] == ["LD  %I0.0\nANDN  %I0.1\nST  %Q0.0"]


def test_two_rungs_are_numbered_in_order():
    rungs = _routine(_parse("08_edges.smbp")).ladder_rungs

    assert [(rung.number, rung.text) for rung in rungs] == [
        (0, "LDR   %I0.0\nST    %Q0.0"),
        (1, "LDF   %I0.1\nST    %Q0.1"),
    ]


def test_symbols_from_io_memory_and_counter_tables():
    tags = _user_tags(_parse("09_symbols.smbp"))

    assert tags == {
        "START_PB": ("Start push button", {"source_symbol_table": "DigitalInputs", "source_memory_address": "%I0.0"}),
        "MOTOR_RUN": ("Motor contactor", {"source_symbol_table": "DigitalOutputs", "source_memory_address": "%Q0.0"}),
        "RUN_LATCH": (None, {"source_symbol_table": "MemoryBits", "source_memory_address": "%M0"}),
        "PART_COUNT": (None, {"source_symbol_table": "Counters", "source_memory_address": "%C0"}),
    }


def test_instruction_list_rung():
    routine = _routine(_parse("10_il_only.smbp"))

    assert routine.language == "IL"
    assert routine.ladder_rungs[0].text == "LD    %I0.0\nAND   %I0.1\nST    %Q0.0"


def test_encrypted_project_keeps_only_its_public_name():
    result = _parse("11_encrypted.smbp")

    assert result.encrypted is True
    # The internal name comes from the project it was copied from, not the file name.
    assert result.controller.name == "01_series"
    assert result.controller.programs == {} and result.controller.tags == {}


def _check(*arguments: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "examples/check_smbp_grid_vs_il.py"), str(FIXTURES), *arguments],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    return ast.literal_eval(completed.stdout.splitlines()[0])


def test_every_grid_rung_matches_its_instruction_list():
    assert _check() == {"match": 14, "il-only": 1}


def test_grid_check_fails_under_the_wrong_vertical_edge_rule():
    outcome = _check("--vertical-on-left")

    assert outcome.get("mismatch", 0) > 0
