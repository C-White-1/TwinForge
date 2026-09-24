"""Ladder (LD) rung resolution: pure series only, branches stay diagnosed."""
from pathlib import Path

import pytest

from twinforge.model import LadderInstruction, LadderOperation, LadderRung
from twinforge.parsers.control_expert import capture_bytes, capture_file, parse_project, parse_projects

_FFB_TEMPLATE = (
    '<FFBBlock instanceName="{instance}" typeName="{type_name}" additionnalPinNumber="0" '
    'enEnO="{en_en_o}" width="10" height="3">'
    '<objPosition posX="{posx}" posY="{posy}"/>'
    '<descriptionFFB execAfter=""><inputVariable invertedPin="false" formalParameter="{first_input}"/>'
    '</descriptionFFB></FFBBlock>'
)


def _ffb(instance="B1", type_name="TON", posx=2, posy=1, en_en_o="true", first_input="EN"):
    return _FFB_TEMPLATE.format(
        instance=instance, type_name=type_name, posx=posx, posy=posy,
        en_en_o=en_en_o, first_input=first_input,
    )


def _block(routine, instance="B1"):
    diagram = routine.graphical_diagrams[0]
    matches = [obj for obj in diagram.objects if obj.instance_name == instance]
    assert len(matches) == 1
    return matches[0]


def _en_pin(routine, instance="B1"):
    pins = [pin for pin in _block(routine, instance).pins if pin.name == "EN"]
    assert len(pins) == 1
    return pins[0]


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


def test_set_coil_resolves_like_reset_coil():
    # Real evidence: github.com/sayahali/conveyor-automation's M340 export
    # uses typeCoil="setCoil" (4 real occurrences) -- resetCoil's natural
    # counterpart, previously missing from _COIL_OPERATIONS entirely, so
    # every such row fell through to UNSUPPORTED/unresolved_ladder_instruction.
    result, routine = _ld_routine('''
    <typeLine><HLink nbCells="10"/><coil typeCoil="setCoil" coilVariableName="P"/></typeLine>''')
    assert len(routine.ladder_rungs) == 1
    elements = _instructions(routine.ladder_rungs[0])
    assert len(elements) == 1
    assert elements[0].operation == LadderOperation.SET_COIL
    assert not any(d.code == "unresolved_ladder_instruction" for d in result.diagnostics)


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


def test_short_circuit_wire_resolves_to_target_block_en_pin():
    _result, routine = _ld_routine(f'''
    <typeLine><shortCircuit><VLink/>
    <contact typeContact="openContact" contactVariableName="A"/></shortCircuit>
    <HLink nbCells="9"/></typeLine>
    <typeLine><VLink/><emptyCell nbCells="1"/>{_ffb(posx=2, posy=1)}</typeLine>''')
    pin = _en_pin(routine)
    assert pin.ladder_condition is not None
    assert len(pin.ladder_condition.elements) == 1
    instruction = pin.ladder_condition.elements[0]
    assert isinstance(instruction, LadderInstruction)
    assert instruction.operation == LadderOperation.NORMALLY_OPEN_CONTACT
    assert instruction.operand == "A"


def test_short_circuit_wire_with_no_contact_is_unconditional():
    _result, routine = _ld_routine(f'''
    <typeLine><HLink nbCells="1"/><shortCircuit><VLink/>
    <HLink nbCells="3"/></shortCircuit><emptyCell nbCells="6"/></typeLine>
    <typeLine><emptyCell nbCells="3"/><VLink/><emptyCell nbCells="1"/>{_ffb(posx=5, posy=1)}</typeLine>''')
    pin = _en_pin(routine)
    assert pin.ladder_condition is not None
    assert pin.ladder_condition.elements == ()


def test_short_circuit_wire_that_continues_past_landing_row_stays_unresolved():
    # Real evidence (MBP_MSTR_7 in the corpus) shows this shape exists but its
    # true target is ambiguous; do not guess which pin it feeds.
    _result, routine = _ld_routine(f'''
    <typeLine><shortCircuit><VLink/>
    <contact typeContact="openContact" contactVariableName="A"/></shortCircuit>
    <HLink nbCells="9"/></typeLine>
    <typeLine><VLink/><emptyCell nbCells="1"/>{_ffb(posx=2, posy=1)}</typeLine>
    <typeLine><VLink/><emptyCell nbCells="9"/></typeLine>''')
    pin = _en_pin(routine)
    assert pin.ladder_condition is None


def test_short_circuit_wire_does_not_bind_without_en_en_o():
    _result, routine = _ld_routine(f'''
    <typeLine><shortCircuit><VLink/>
    <contact typeContact="openContact" contactVariableName="A"/></shortCircuit>
    <HLink nbCells="9"/></typeLine>
    <typeLine><VLink/><emptyCell nbCells="1"/>{_ffb(posx=2, posy=1, en_en_o="false")}</typeLine>''')
    pin = _en_pin(routine)
    assert pin.ladder_condition is None


def test_ffb_block_footprint_blocks_a_later_wire_landing():
    # Real evidence (module docstring in ladder.py): an FFBBlock always spans
    # exactly two columns, so scanning now continues past it instead of
    # abandoning the row. That footprint must still obstruct any other wire
    # trying to reach a second block further along the same row -- a shape
    # that could never even be reached before this block width was known.
    _result, routine = _ld_routine(f'''
    <typeLine><shortCircuit><VLink/>
    <contact typeContact="openContact" contactVariableName="A"/></shortCircuit>
    <emptyCell nbCells="1"/>{_ffb(instance="B1", posx=2, posy=0, en_en_o="false")}
    <emptyCell nbCells="1"/>{_ffb(instance="B2", posx=5, posy=0)}</typeLine>''')
    assert _en_pin(routine, "B1").ladder_condition is None
    assert _en_pin(routine, "B2").ladder_condition is None


def test_wire_starting_after_an_ffb_block_still_resolves():
    # Companion to the footprint-blocking test above: scanning must actually
    # continue past the first block (not merely stop there), so a wire that
    # starts to its right can still cleanly reach a second block. Before the
    # block width was known, the row scan stopped at the first FFBBlock, so
    # this shape was unreachable regardless of any obstruction logic.
    _result, routine = _ld_routine(f'''
    <typeLine>{_ffb(instance="B1", posx=0, posy=0, en_en_o="false")}
    <shortCircuit><VLink/>
    <contact typeContact="openContact" contactVariableName="A"/></shortCircuit>
    <emptyCell nbCells="1"/>{_ffb(instance="B2", posx=4, posy=0)}</typeLine>''')
    pin = _en_pin(routine, "B2")
    assert pin.ladder_condition is not None
    assert [e.operand for e in pin.ladder_condition.elements] == ["A"]  # type: ignore[union-attr]


def test_malformed_short_circuit_shape_is_diagnosed_not_guessed():
    result, _routine = _ld_routine('''
    <typeLine><shortCircuit>
    <contact typeContact="openContact" contactVariableName="A"/>
    <contact typeContact="openContact" contactVariableName="B"/>
    </shortCircuit><HLink nbCells="9"/></typeLine>''')
    assert sum(d.code == "unresolved_ladder_short_circuit" for d in result.diagnostics) == 1


def test_optional_real_function15_short_circuit_conditions():
    for filename in ("function15.zip", "function2.zip"):
        path = Path("reference/control-expert") / filename
        if not path.exists():
            pytest.skip("Local function15/function2 reference unavailable")
        captured = capture_file(path)
        result, = parse_projects(next(m for m in captured.members if m.name.endswith(".zef")))

        def en_condition(program_name: str, instance: str) -> list[str | None] | None:
            routine = result.controller.programs[program_name].main_routine
            assert routine is not None
            block = next(o for d in routine.graphical_diagrams for o in d.objects if o.instance_name == instance)
            pin = next(p for p in block.pins if p.name == "EN")
            if pin.ladder_condition is None:
                return None
            return [e.operand for e in pin.ladder_condition.elements]  # type: ignore[union-attr]

        assert en_condition("sendnoe", ".2") == ["abortnoe"]       # SET
        assert en_condition("sendnoe", ".4") == ["timedoutnoe"]    # ADD
        assert en_condition("resetnoe", ".5") == ["resetnoe"]      # ADD
        assert en_condition("resetnoe", ".4") == []                # SET, unconditional
        # Genuinely ambiguous shapes in the corpus stay unresolved, not guessed.
        assert en_condition("sendnoe", "MBP_MSTR_2") is None
        assert en_condition("sendnoe", "TON_2") is None
        assert en_condition("resetnoe", ".3") is None               # RESET
        assert en_condition("resetnoe", "MBP_MSTR_7") is None


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


def test_optional_real_sayahali_conveyor_set_coil_rows():
    # github.com/sayahali/conveyor-automation's real M340 export -- see the
    # setCoil/new-corpus checkpoint. Real evidence: 4 rows end in
    # typeCoil="setCoil", previously UNSUPPORTED.
    path = Path("reference/control-expert/sayahali_conveyor_ali_conv.zef")
    if not path.exists():
        pytest.skip("Local sayahali/conveyor-automation reference unavailable")
    result, = parse_projects(capture_file(path))
    routine = result.controller.programs["prog"].routines["prog"]
    set_coil_rungs = [rung for rung in routine.ladder_rungs
                      if any(e.operation == LadderOperation.SET_COIL for e in _instructions(rung))]
    assert len(set_coil_rungs) == 4
    assert not any(d.code == "unresolved_ladder_instruction" for d in result.diagnostics)
