"""Ladder (LD) rung resolution: pure series only, branches stay diagnosed."""
from pathlib import Path

import pytest

from twinforge.model import LadderInstruction, LadderOperation, LadderRung
from twinforge.parsers.control_expert import capture_bytes, capture_file, parse_project, parse_projects


def _ld_routine(network_body: str):
    data = f'''<FEFExchangeFile><logicConf><resource><taskDesc task="MAST" taskType="cyclic">
    <sectionDesc name="Rungs"/></taskDesc></resource></logicConf>
    <program><identProgram name="Rungs" task="MAST"/>
    <LDSource nbColumns="11"><networkLD>{network_body}</networkLD></LDSource>
    </program></FEFExchangeFile>'''
    result = parse_project(capture_bytes(data.encode(), name="ladder.xef"))
    routine = result.controller.programs["Rungs"].main_routine
    assert routine is not None and routine.language == "LD"
    return result, routine


def _instructions(rung: LadderRung) -> list[LadderInstruction]:
    assert rung.network is not None
    for element in rung.network.elements:
        assert isinstance(element, LadderInstruction)
    return list(rung.network.elements)  # type: ignore[return-value]


def test_series_row_with_mixed_contacts_resolves():
    result, routine = _ld_routine('''
    <typeLine>
    <contact typeContact="openContact" contactVariableName="A"/>
    <HLink nbCells="1"/>
    <contact typeContact="closedContact" contactVariableName="B"/>
    <HLink nbCells="7"/>
    <coil typeCoil="coil" coilVariableName="Out"/>
    </typeLine>''')
    assert len(routine.ladder_rungs) == 1
    rung = routine.ladder_rungs[0]
    assert rung.number == 0
    ops = [(e.operation, e.operand, e.position.column if e.position else None) for e in _instructions(rung)]
    assert ops == [
        (LadderOperation.NORMALLY_OPEN_CONTACT, "A", 0),
        (LadderOperation.NORMALLY_CLOSED_CONTACT, "B", 2),
        (LadderOperation.COIL, "Out", 10),
    ]
    assert not any(d.code.startswith("ladder") or d.code.startswith("unresolved_ladder")
                   for d in result.diagnostics)


def test_unconditional_coil_with_leading_wire_only_resolves():
    result, routine = _ld_routine('''
    <typeLine><HLink nbCells="10"/><coil typeCoil="resetCoil" coilVariableName="P"/></typeLine>''')
    assert len(routine.ladder_rungs) == 1
    elements = _instructions(routine.ladder_rungs[0])
    assert len(elements) == 1
    assert elements[0].operation == LadderOperation.RESET_COIL
    assert elements[0].position is not None and elements[0].position.column == 10


def test_missing_coil_is_diagnosed_and_not_resolved():
    result, routine = _ld_routine('''
    <typeLine><contact typeContact="openContact" contactVariableName="A"/><HLink nbCells="9"/></typeLine>''')
    assert routine.ladder_rungs == []
    assert sum(d.code == "ladder_series_missing_coil" for d in result.diagnostics) == 1


@pytest.mark.parametrize("body", [
    # Two coils.
    '<contact typeContact="openContact" contactVariableName="A"/>'
    '<coil typeCoil="coil" coilVariableName="X"/><coil typeCoil="coil" coilVariableName="Y"/>',
    # Coil not last.
    '<coil typeCoil="coil" coilVariableName="X"/>'
    '<contact typeContact="openContact" contactVariableName="A"/>',
])
def test_coil_not_alone_at_the_end_is_diagnosed(body):
    result, routine = _ld_routine(f'<typeLine>{body}</typeLine>')
    assert routine.ladder_rungs == []
    assert sum(d.code == "ladder_series_unexpected_coil_position" for d in result.diagnostics) == 1


def test_short_circuit_row_is_diagnosed_not_guessed():
    result, routine = _ld_routine('''
    <typeLine><HLink nbCells="1"/><shortCircuit><VLink/>
    <contact typeContact="openContact" contactVariableName="A"/></shortCircuit>
    <HLink nbCells="2"/></typeLine>''')
    assert routine.ladder_rungs == []
    assert sum(d.code == "unresolved_ladder_row" for d in result.diagnostics) == 1


def test_block_row_is_diagnosed_not_guessed():
    result, routine = _ld_routine('''
    <typeLine><emptyCell nbCells="4"/>
    <FFBBlock instanceName=".1" typeName="TON" additionnalPinNumber="0" enEnO="true" width="12" height="4">
    <objPosition posX="4" posY="0"/><descriptionFFB execAfter=""/>
    </FFBBlock></typeLine>''')
    assert routine.ladder_rungs == []
    assert sum(d.code == "unresolved_ladder_row" for d in result.diagnostics) == 1


def test_empty_line_advances_row_without_producing_a_rung():
    result, routine = _ld_routine('''
    <typeLine><contact typeContact="openContact" contactVariableName="A"/>
    <HLink nbCells="9"/><coil typeCoil="coil" coilVariableName="X"/></typeLine>
    <typeLine><emptyLine nbRows="3"/></typeLine>
    <typeLine><contact typeContact="openContact" contactVariableName="B"/>
    <HLink nbCells="9"/><coil typeCoil="coil" coilVariableName="Y"/></typeLine>''')
    assert [rung.number for rung in routine.ladder_rungs] == [0, 4]


def test_unsupported_contact_type_resolves_structurally_but_is_flagged():
    result, routine = _ld_routine('''
    <typeLine><contact typeContact="PContact" contactVariableName="R"/>
    <HLink nbCells="9"/><coil typeCoil="coil" coilVariableName="X"/></typeLine>''')
    assert len(routine.ladder_rungs) == 1
    instruction = _instructions(routine.ladder_rungs[0])[0]
    assert instruction.operation == LadderOperation.UNSUPPORTED
    assert instruction.source_mnemonic == "PContact"
    assert instruction.operand == "R"
    assert sum(d.code == "unresolved_ladder_instruction" for d in result.diagnostics) == 1


def test_invalid_cell_count_is_diagnosed():
    result, routine = _ld_routine('''
    <typeLine><HLink nbCells="not-a-number"/>
    <coil typeCoil="coil" coilVariableName="X"/></typeLine>''')
    assert routine.ladder_rungs == []
    assert sum(d.code == "invalid_ladder_number" for d in result.diagnostics) == 1


@pytest.mark.parametrize("filename", ["Escalier_Mecanique.XEF", "escalier_mecanique.zef"])
def test_optional_real_escalator_ladder_rungs(filename):
    path = Path("reference/control-expert") / filename
    if not path.exists():
        pytest.skip("Local SFC reference unavailable")
    result, = parse_projects(capture_file(path))
    counts = {}
    for program in result.controller.programs.values():
        for routine in program.routines.values():
            if routine.language == "LD":
                counts[program.name] = len(routine.ladder_rungs)
    assert counts == {"Init_Logic": 2, "TIMERS": 0, "Rising_Edge_Detection": 4}
    rising_edge_operands = [
        [e.operand for e in _instructions(rung)]
        for program in result.controller.programs.values()
        for routine in program.routines.values()
        if routine.language == "LD" and program.name == "Rising_Edge_Detection"
        for rung in routine.ladder_rungs
    ]
    assert rising_edge_operands == [
        ["p", "p_prev", "Presence_Request_rising_edge"],
        ["Presence_Request_rising_edge", "Presence_Request"],
        ["Presence_Request", "Start_Timer"],
        ["p", "p_prev"],
    ]


@pytest.mark.parametrize("filename", ["MultiGrafcet_Coordination_V1_2026.XEF", "tsaii_multigrafcet_final_v1.zef"])
def test_optional_real_multigrafcet_ladder_has_no_pure_series_rungs(filename):
    path = Path("reference/control-expert") / filename
    if not path.exists():
        pytest.skip("Local multi-Grafcet reference unavailable")
    result, = parse_projects(capture_file(path))
    ld_routines = [routine for program in result.controller.programs.values()
                   for routine in program.routines.values() if routine.language == "LD"]
    assert len(ld_routines) == 1
    # This LD section is entirely block/branch-gated (INITCHART/SETSTEP/TON via
    # shortCircuit+VLink); nothing here is a pure series rung.
    assert ld_routines[0].ladder_rungs == []
    assert any(d.code == "unresolved_ladder_row" for d in result.diagnostics)
