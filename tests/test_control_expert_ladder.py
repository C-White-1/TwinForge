"""Ladder (LD) rung resolution: pure series only, branches stay diagnosed."""
from pathlib import Path

import pytest

from twinforge.model import LadderInstruction, LadderOperation, LadderRung
from twinforge.parsers.control_expert import capture_bytes, capture_file, parse_project, parse_projects
from twinforge.parsers.control_expert.capture import CapturedSection

_FFB_TEMPLATE = (
    '<FFBBlock instanceName="{instance}" typeName="{type_name}" additionnalPinNumber="0" '
    'enEnO="{en_en_o}" width="10" height="3">'
    '<objPosition posX="{posx}" posY="{posy}"/>'
    '<descriptionFFB execAfter=""><inputVariable invertedPin="false" formalParameter="{first_input}"/>'
    '{second_input_xml}'
    '</descriptionFFB></FFBBlock>'
)


def _ffb(instance="B1", type_name="TON", posx=2, posy=1, en_en_o="true", first_input="EN", second_input=None):
    second_input_xml = (
        f'<inputVariable invertedPin="false" formalParameter="{second_input}"/>' if second_input else ""
    )
    return _FFB_TEMPLATE.format(
        instance=instance, type_name=type_name, posx=posx, posy=posy,
        en_en_o=en_en_o, first_input=first_input, second_input_xml=second_input_xml,
    )


def _block(routine, instance="B1"):
    diagram = routine.graphical_diagrams[0]
    matches = [obj for obj in diagram.objects if obj.instance_name == instance]
    assert len(matches) == 1
    return matches[0]


def _pin(routine, instance, pin_name):
    pins = [pin for pin in _block(routine, instance).pins if pin.name == pin_name]
    assert len(pins) == 1
    return pins[0]


def _en_pin(routine, instance="B1"):
    return _pin(routine, instance, "EN")


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


def test_coil_fed_from_a_block_output_edge_is_not_unconditional():
    # Real evidence (see _block_output_origins in ladder.py): confirmed
    # twice, independently -- sayahali_conveyor_ali_conv.zef's five TON
    # instances (posY+2 -> Q) and control-expert-mcp's LD_1_Heating.xml
    # Heating_control block (six real outputs at posY+2 through posY+7,
    # all wired to coils). This reproduces that second fixture's exact
    # shape: an enEnO="true" block with more outputs than inputs, height
    # reserving one blank leading row, wired via a drawn HLink starting
    # exactly at the block's own output edge (posX + width).
    _result, routine = _ld_routine('''
    <typeLine><emptyCell nbCells="3"/>
    <FFBBlock instanceName="HC" typeName="Heating" additionnalPinNumber="0" enEnO="true" width="16" height="5">
    <objPosition posX="3" posY="0"/>
    <descriptionFFB execAfter="">
    <inputVariable invertedPin="false" formalParameter="EN"/>
    <inputVariable invertedPin="false" formalParameter="X"/>
    <outputVariable invertedPin="false" formalParameter="ENO"/>
    <outputVariable invertedPin="false" formalParameter="A"/>
    <outputVariable invertedPin="false" formalParameter="B"/>
    </descriptionFFB></FFBBlock>
    <emptyCell nbCells="6"/></typeLine>
    <typeLine><emptyLine nbRows="1"/></typeLine>
    <typeLine><emptyCell nbCells="5"/><HLink nbCells="5"/>
    <coil typeCoil="coil" coilVariableName="Y"/></typeLine>''')
    rungs = [r for r in routine.ladder_rungs if r.number == 2]
    assert len(rungs) == 1
    elements = _instructions(rungs[0])
    assert len(elements) == 2
    assert elements[0].operation == LadderOperation.BLOCK_OUTPUT_REFERENCE
    assert elements[0].operand == "HC.A"
    assert elements[0].source_mnemonic == "Heating"
    assert elements[1].operation == LadderOperation.COIL
    assert elements[1].operand == "Y"


def test_coil_fed_from_an_unrelated_column_stays_unconditional():
    # Real negative case: sayahali_conveyor_ali_conv.zef rows 81 and 97 have
    # the identical grid shape (leading emptyCell, no contacts, a coil) with
    # no block anywhere near the matching column -- genuinely unconditional,
    # and must stay that way. Same block as above, but the coil sits one
    # column short of the block's real output edge (col 4, not 5).
    _result, routine = _ld_routine('''
    <typeLine><emptyCell nbCells="3"/>
    <FFBBlock instanceName="HC" typeName="Heating" additionnalPinNumber="0" enEnO="true" width="16" height="5">
    <objPosition posX="3" posY="0"/>
    <descriptionFFB execAfter="">
    <inputVariable invertedPin="false" formalParameter="EN"/>
    <inputVariable invertedPin="false" formalParameter="X"/>
    <outputVariable invertedPin="false" formalParameter="ENO"/>
    <outputVariable invertedPin="false" formalParameter="A"/>
    <outputVariable invertedPin="false" formalParameter="B"/>
    </descriptionFFB></FFBBlock>
    <emptyCell nbCells="6"/></typeLine>
    <typeLine><emptyLine nbRows="1"/></typeLine>
    <typeLine><emptyCell nbCells="4"/><HLink nbCells="6"/>
    <coil typeCoil="coil" coilVariableName="Y"/></typeLine>''')
    rungs = [r for r in routine.ladder_rungs if r.number == 2]
    assert len(rungs) == 1
    elements = _instructions(rungs[0])
    assert len(elements) == 1
    assert elements[0].operation == LadderOperation.COIL


def test_contact_disconnected_by_a_gap_is_excluded_not_misattributed():
    # Real evidence: LD_1_Heating.xml's sixth row (control-expert-mcp,
    # local-only) has a real contact ("Start_process") ahead of the same
    # block-output wire the other five rows resolve, separated from it by
    # a genuine emptyCell gap. Before this fix, every contact in a row was
    # collected into the coil's condition regardless of gaps, so that
    # contact was silently misattributed as the coil's condition instead
    # of the block's own output. Reproduces that exact shape: contact,
    # HLink, emptyCell (the real break), HLink starting at the block's own
    # output edge, coil.
    result, routine = _ld_routine('''
    <typeLine><emptyCell nbCells="3"/>
    <FFBBlock instanceName="HC" typeName="Heating" additionnalPinNumber="0" enEnO="true" width="16" height="5">
    <objPosition posX="3" posY="0"/>
    <descriptionFFB execAfter="">
    <inputVariable invertedPin="false" formalParameter="EN"/>
    <inputVariable invertedPin="false" formalParameter="X"/>
    <outputVariable invertedPin="false" formalParameter="ENO"/>
    <outputVariable invertedPin="false" formalParameter="A"/>
    <outputVariable invertedPin="false" formalParameter="B"/>
    </descriptionFFB></FFBBlock>
    <emptyCell nbCells="6"/></typeLine>
    <typeLine><emptyLine nbRows="1"/></typeLine>
    <typeLine><contact typeContact="openContact" contactVariableName="Dummy"/>
    <HLink nbCells="2"/><emptyCell nbCells="2"/><HLink nbCells="5"/>
    <coil typeCoil="coil" coilVariableName="Y"/></typeLine>''')
    rungs = [r for r in routine.ladder_rungs if r.number == 2]
    assert len(rungs) == 1
    elements = _instructions(rungs[0])
    assert len(elements) == 2
    assert elements[0].operation == LadderOperation.BLOCK_OUTPUT_REFERENCE
    assert elements[0].operand == "HC.A"
    assert elements[1].operation == LadderOperation.COIL
    assert not any(e.operand == "Dummy" for e in elements)
    assert sum(d.code == "ladder_disconnected_segment_discarded" for d in result.diagnostics) == 1


def test_optional_real_ld_1_heating_coils_resolve_correctly():
    path = Path("reference/control-expert/LD_1_Heating.xml")
    if not path.exists():
        pytest.skip("Local LD_1_Heating.xml reference unavailable")
    from twinforge.parsers.control_expert.ladder import parse_ladder_rungs

    def find_all(node, tag):
        if node.tag == tag:
            yield node
        for child in node.ordered_children:
            yield from find_all(child, tag)

    captured = capture_file(path)
    assert captured.section is not None
    ld_source = next(find_all(captured.section, "LDSource"))
    rungs, diagnostics = parse_ladder_rungs(ld_source)

    def rung_by_row(row: int):
        matches = [r for r in rungs if r.number == row]
        assert len(matches) == 1
        return _instructions(matches[0])

    for row, pin, coil in (
        (6, "plus_10_percent", "plus_10_percent"),
        (7, "plus_5_percent", "plus_5_percent"),
        (8, "plus_1_percent", "plus_1_percent"),
        (9, "minus_1_percent", "minus_1_percent"),
        (10, "minus_5_percent", "minus_5_percent"),
        (11, "minus_10_percent", "minus_10_percent"),
    ):
        elements = rung_by_row(row)
        assert len(elements) == 2
        assert elements[0].operation == LadderOperation.BLOCK_OUTPUT_REFERENCE
        assert elements[0].operand == f"Heating_control.{pin}"
        assert elements[1].operation == LadderOperation.COIL
        assert elements[1].operand == coil
    assert sum(d.code == "ladder_disconnected_segment_discarded" for d in diagnostics) == 1


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


def test_short_circuit_wraps_block_directly_lands_on_second_input_when_en_hidden():
    # Real evidence: sayahali_conveyor_ali_conv.zef's SR_2/SR_3/SR_4/SR_5/SR_7
    # (enEnO="false") each show <shortCircuit><VLink/><FFBBlock/></shortCircuit>
    # landing on the block's own anchor row -- confirmed by the user against
    # the vendor's own PDF rendering of SR_4: S1 and Q1 share the block's top
    # row, no separate EN/ENO row exists at all when EN/ENO are hidden. EN is
    # still declared (never rendered when enEnO="false"), so the wire lands
    # on the second declared input instead.
    _result, routine = _ld_routine(f'''
    <typeLine><shortCircuit><VLink/>
    {_ffb(posy=0, en_en_o="false", second_input="S1")}</shortCircuit></typeLine>''')
    pin = _pin(routine, "B1", "S1")
    assert pin.ladder_condition is not None
    assert pin.ladder_condition.elements == ()


def test_short_circuit_wraps_block_directly_with_a_leading_contact_condition():
    _result, routine = _ld_routine(f'''
    <typeLine><contact typeContact="openContact" contactVariableName="A"/>
    <shortCircuit><VLink/>{_ffb(posy=0, en_en_o="false", second_input="S1")}</shortCircuit></typeLine>''')
    pin = _pin(routine, "B1", "S1")
    assert pin.ladder_condition is not None
    assert [e.operand for e in pin.ladder_condition.elements] == ["A"]  # type: ignore[union-attr]


def test_bare_block_without_short_circuit_wrapper_does_not_bind():
    # Real negative case: sayahali_conveyor_ali_conv.zef's SR_8/SR_9 are bare
    # FFBBlock elements with no shortCircuit wrapper at all -- structurally
    # distinct from a genuinely wired block, not merely an unresolved wire.
    _result, routine = _ld_routine(f'''
    <typeLine><emptyCell nbCells="4"/>{_ffb(posy=0, en_en_o="false", second_input="S1")}</typeLine>''')
    pin = _pin(routine, "B1", "S1")
    assert pin.ladder_condition is None


def test_short_circuit_wraps_block_without_a_second_declared_input_does_not_bind():
    _result, routine = _ld_routine(f'''
    <typeLine><shortCircuit><VLink/>
    {_ffb(posy=0, en_en_o="false")}</shortCircuit></typeLine>''')
    pin = _en_pin(routine)
    assert pin.ladder_condition is None


_SR_LIKE_BLOCK = '''
<FFBBlock instanceName="{instance}" typeName="SR" additionnalPinNumber="0" enEnO="false" width="10" height="3">
<objPosition posX="{posx}" posY="{posy}"/>
<descriptionFFB execAfter="">
<inputVariable invertedPin="false" formalParameter="EN"/>
<inputVariable invertedPin="false" formalParameter="S1"/>
<outputVariable invertedPin="false" formalParameter="ENO"/>
<outputVariable invertedPin="false" formalParameter="Q1"/>
</descriptionFFB></FFBBlock>'''

_TON_LIKE_BLOCK = '''
<FFBBlock instanceName="{instance}" typeName="TON" additionnalPinNumber="0" enEnO="true" width="10" height="4">
<objPosition posX="{posx}" posY="{posy}"/>
<descriptionFFB execAfter="">
<inputVariable invertedPin="false" formalParameter="EN"/>
<inputVariable invertedPin="false" formalParameter="IN"/>
<inputVariable invertedPin="false" formalParameter="PT"/>
</descriptionFFB></FFBBlock>'''


def test_short_circuit_wraps_block_carries_its_own_output_onward():
    # Real evidence: sayahali_conveyor_ali_conv.zef's SR_2.Q1 feeds
    # TON_23.IN directly -- the SAME <shortCircuit><VLink/><FFBBlock/>
    # </shortCircuit> element that lands an incoming wire on the block's
    # own input (S1, tested above) also carries the block's own output
    # edge onward to whatever it next reaches. B2 (TON-shaped, enEnO=
    # "true") declares its own anchor on row 0; its IN pin lands at
    # posY+1+1 = row 2, which is where B1 (SR-shaped) sits, wrapped
    # inline in a shortCircuit whose sibling HLink/emptyCell cleanly
    # reaches B2's own posX.
    _result, routine = _ld_routine(f'''
    <typeLine><emptyCell nbCells="7"/>{_TON_LIKE_BLOCK.format(instance="B2", posx=7, posy=0)}</typeLine>
    <typeLine><emptyLine nbRows="1"/></typeLine>
    <typeLine><shortCircuit><VLink/>{_SR_LIKE_BLOCK.format(instance="B1", posx=2, posy=2)}</shortCircuit>
    <HLink nbCells="1"/><emptyCell nbCells="2"/></typeLine>''')
    in_pin = _pin(routine, "B2", "IN")
    assert in_pin.ladder_condition is not None
    assert len(in_pin.ladder_condition.elements) == 1
    instruction = in_pin.ladder_condition.elements[0]
    assert isinstance(instruction, LadderInstruction)
    assert instruction.operation == LadderOperation.BLOCK_OUTPUT_REFERENCE
    assert instruction.operand == "B1.Q1"
    assert instruction.source_mnemonic == "SR"
    # The block's own S1 input, resolved by the pre-existing rule, is
    # unaffected by also carrying its output onward.
    assert _pin(routine, "B1", "S1").ladder_condition is not None
    assert _pin(routine, "B1", "S1").ladder_condition.elements == ()  # type: ignore[union-attr]


def test_block_output_wire_is_consumed_and_does_not_also_land_on_a_later_input():
    # Real bug caught directly against the fixture while implementing the
    # test above: SR_2.Q1 landed correctly on TON_23.IN (row posY+2) but
    # then ALSO "landed" on TON_23.PT (row posY+3), since the wire stayed
    # marked as surviving into the next row. PT is genuinely fed by its
    # own literal (`effectiveParameter`), never a wire -- a landed wire
    # must stop at its own landing, not keep matching later rows too.
    _result, routine = _ld_routine(f'''
    <typeLine><emptyCell nbCells="7"/>{_TON_LIKE_BLOCK.format(instance="B2", posx=7, posy=0)}</typeLine>
    <typeLine><emptyLine nbRows="1"/></typeLine>
    <typeLine><shortCircuit><VLink/>{_SR_LIKE_BLOCK.format(instance="B1", posx=2, posy=2)}</shortCircuit>
    <HLink nbCells="1"/><emptyCell nbCells="2"/></typeLine>''')
    assert _pin(routine, "B2", "PT").ladder_condition is None


def _captured_ffb_block(xml: str) -> CapturedSection:
    data = f'''<FEFExchangeFile><logicConf><resource><taskDesc task="MAST" taskType="cyclic">
    <sectionDesc name="Rungs"/></taskDesc></resource></logicConf>
    <program><identProgram name="Rungs" task="MAST"/>
    <LDSource nbColumns="11"><networkLD><typeLine>{xml}</typeLine></networkLD></LDSource>
    </program></FEFExchangeFile>'''
    captured = capture_bytes(data.encode(), name="ladder.xef")
    section = captured.section
    assert section is not None

    def find_all(node: CapturedSection, tag: str):
        if node.tag == tag:
            yield node
        for c in node.ordered_children:
            yield from find_all(c, tag)

    return next(find_all(section, "FFBBlock"))


def test_enable_block_does_not_carry_an_output_onward():
    # Scope guard: `_first_wireable_output` is evidenced only for
    # enEnO="false" blocks declaring exactly ENO + one output (every real
    # SR instance in the corpus). An enEnO="true" block must not ALSO
    # originate a block-output wire from this mechanism -- that shape has
    # no positive example anywhere in the corpus.
    from twinforge.parsers.control_expert.ladder import _first_wireable_output
    block = _captured_ffb_block(_ffb(posy=0))
    assert _first_wireable_output(block) is None


def test_block_with_more_than_one_wireable_output_does_not_originate_a_wire():
    # Scope guard: only the exact evidenced shape (enEnO="false", exactly
    # ENO + one other output) is trusted. A block with two or more
    # wireable outputs has no positive example in the corpus to confirm
    # which one (if any) a passing shortCircuit would carry.
    from twinforge.parsers.control_expert.ladder import _first_wireable_output
    block = _captured_ffb_block('''
    <FFBBlock instanceName="B1" typeName="SR" additionnalPinNumber="0" enEnO="false" width="10" height="3">
    <objPosition posX="2" posY="0"/>
    <descriptionFFB execAfter="">
    <inputVariable invertedPin="false" formalParameter="EN"/>
    <inputVariable invertedPin="false" formalParameter="S1"/>
    <outputVariable invertedPin="false" formalParameter="ENO"/>
    <outputVariable invertedPin="false" formalParameter="Q1"/>
    <outputVariable invertedPin="false" formalParameter="Q2"/>
    </descriptionFFB></FFBBlock>''')
    assert _first_wireable_output(block) is None


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


def test_optional_real_sayahali_sr_block_s1_conditions():
    # Real evidence: SR_2/SR_3/SR_4/SR_5/SR_7 (enEnO="false") each land
    # unconditionally on S1 via <shortCircuit><VLink/><FFBBlock/></shortCircuit>
    # -- confirmed against the vendor's own PDF rendering of SR_4 (S1/Q1 share
    # the block's top row, no EN/ENO row at all). SR_8/SR_9 are bare
    # FFBBlock elements with no shortCircuit wrapper -- structurally
    # unconnected, not merely unresolved, and must stay that way.
    path = Path("reference/control-expert/sayahali_conveyor_ali_conv.zef")
    if not path.exists():
        pytest.skip("Local sayahali/conveyor-automation reference unavailable")
    result, = parse_projects(capture_file(path))
    routine = result.controller.programs["prog"].main_routine
    assert routine is not None

    def s1_condition(instance: str) -> list[str | None] | None:
        block = next(o for d in routine.graphical_diagrams for o in d.objects if o.instance_name == instance)
        pin = next(p for p in block.pins if p.name == "S1")
        if pin.ladder_condition is None:
            return None
        return [e.operand for e in pin.ladder_condition.elements]  # type: ignore[union-attr]

    for instance in ("SR_2", "SR_3", "SR_4", "SR_5", "SR_7"):
        assert s1_condition(instance) == []
    for instance in ("SR_8", "SR_9"):
        assert s1_condition(instance) is None


def test_optional_real_sayahali_sr_output_feeds_ton_in():
    # Real evidence: the same fixture's SR_2/SR_3/SR_4/SR_5/SR_7 each feed
    # their own Q1 output directly into a TON block's IN pin (SR_2 ->
    # TON_23, SR_3 -> TON_24, SR_4 -> TON_25, SR_5 -> TON_26, SR_7 ->
    # TON_28) -- the SAME <shortCircuit><VLink/><FFBBlock/></shortCircuit>
    # element already resolving S1 (tested above) also carries the block's
    # own output edge onward. Confirmed end to end through the full parse
    # pipeline, not just the lower-level resolver.
    path = Path("reference/control-expert/sayahali_conveyor_ali_conv.zef")
    if not path.exists():
        pytest.skip("Local sayahali/conveyor-automation reference unavailable")
    result, = parse_projects(capture_file(path))
    routine = result.controller.programs["prog"].main_routine
    assert routine is not None

    def in_condition_operand(instance: str) -> str | None:
        block = next(o for d in routine.graphical_diagrams for o in d.objects if o.instance_name == instance)
        pin = next(p for p in block.pins if p.name == "IN")
        if pin.ladder_condition is None or not pin.ladder_condition.elements:
            return None
        (element,) = pin.ladder_condition.elements
        assert isinstance(element, LadderInstruction)
        assert element.operation == LadderOperation.BLOCK_OUTPUT_REFERENCE
        return element.operand

    assert in_condition_operand("TON_23") == "SR_2.Q1"
    assert in_condition_operand("TON_24") == "SR_3.Q1"
    assert in_condition_operand("TON_25") == "SR_4.Q1"
    assert in_condition_operand("TON_26") == "SR_5.Q1"
    assert in_condition_operand("TON_28") == "SR_7.Q1"
    assert not any(d.code == "unresolved_ladder_pin_condition" for d in result.diagnostics)


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
