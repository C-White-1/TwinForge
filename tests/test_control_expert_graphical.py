"""Graphical evidence is inspectable without inventing executable connections."""
from pathlib import Path

import pytest

from twinforge.parsers.control_expert import capture_bytes, capture_file, parse_projects
from twinforge.parsers.control_expert.graphical import parse_diagrams


def diagrams(body: str):
    artifact = capture_bytes(body.encode(), name="diagram.xml")
    assert artifact.section is not None
    return parse_diagrams(artifact.section)


def test_pin_direction_bindings_and_position_without_inferred_edges():
    results, diagnostics = diagrams('''<FBDSource><networkFBD>
      <FFBBlock instanceName=".1" typeName="CALL" width="8" height="4">
        <objPosition posX="2" posY="3"/><descriptionFFB execAfter="">
          <inputVariable formalParameter="IN" effectiveParameter="buffer" invertedPin="false"/>
          <outputVariable formalParameter="IN" effectiveParameter="buffer" invertedPin="true"/>
          <outputVariable formalParameter="ENO"/>
        </descriptionFFB>
      </FFBBlock>
      <FFBBlock instanceName=".1" typeName="OTHER"><descriptionFFB>
        <inputVariable formalParameter="IN" effectiveParameter="buffer"/>
      </descriptionFFB></FFBBlock>
      <textBox width="3" height="1"> note <objPosition posX="0" posY="0"/></textBox>
    </networkFBD></FBDSource>''')
    diagram = results[0]
    assert not diagram.connectivity_resolved and not diagram.execution_order_resolved
    assert len(diagram.objects) == 3  # Duplicate instance names are not collapsed.
    block = diagram.objects[0]
    assert block.position is not None and (block.position.column, block.position.row) == (2, 3)
    assert [(p.direction, p.expression, p.inverted) for p in block.pins] == [
        ("input", "buffer", False), ("output", "buffer", True), ("output", None, None)]
    assert diagram.objects[2].text == " note "
    assert diagnostics[0].code == "unresolved_graphical_connections"


def test_ladder_contacts_do_not_receive_invented_positions_or_semantics():
    results, diagnostics = diagrams('''<LDSource><networkLD>
      <typeLine><emptyLine nbRows="3"/></typeLine>
      <typeLine><contact typeContact="PContact" contactVariableName="trigger"/>
        <shortCircuit><VLink/><HLink nbCells="4"/></shortCircuit>
        <FFBBlock instanceName="timer" typeName="TON"><objPosition posX="5" posY="3"/></FFBBlock>
      </typeLine><FutureWire from="a" to="b"/>
    </networkLD></LDSource>''')
    diagram = results[0]
    assert [o.kind for o in diagram.objects] == ["contact", "block"]
    assert diagram.objects[0].type_name == "PContact"
    assert diagram.objects[0].position is None
    assert diagram.objects[0].operand == "trigger"
    assert diagram.source_extensions[0].root.children[-1].name == "FutureWire"
    assert any(d.code == "unclassified_graphical_object" for d in diagnostics)


def test_invalid_numbers_and_conflicting_descriptions_preserved():
    results, diagnostics = diagrams('''<FBDSource><networkFBD>
      <FFBBlock width="bad"><objPosition posX="-1" posY="2"/>
        <descriptionFFB/><descriptionFFB/>
      </FFBBlock>
    </networkFBD></FBDSource>''')
    block = results[0].objects[0]
    assert block.width is None and block.position is None and block.pins == []
    assert block.source_extensions[0].root.attributes["width"] == "bad"
    assert {d.code for d in diagnostics} >= {"invalid_graphical_number", "ambiguous_block_interface"}


def test_sample_graphical_objects_when_available():
    folder = Path(__file__).resolve().parents[1] / "reference" / "control-expert"
    if not (folder / "readvar.zip").exists() or not (folder / "function15.zip").exists():
        pytest.skip("Local Control Expert references are not installed")
    def embedded(name: str):
        captured = capture_file(folder / name)
        return parse_projects(next(m for m in captured.members if m.name.endswith(".zef")))[0]
    fbd = embedded("readvar.zip").controller.programs["rvar"].main_routine
    assert fbd is not None
    blocks = [o for d in fbd.graphical_diagrams for o in d.objects if o.kind == "block"]
    assert [b.type_name for b in blocks] == ["ADDR", "READ_VAR"]
    assert [(p.direction, p.expression) for p in blocks[1].pins if p.name == "GEST"] == [
        ("input", "manage"), ("output", "manage")]
    ld = embedded("function15.zip").controller.programs["sendnoe"].main_routine
    assert ld is not None
    blocks = [o for d in ld.graphical_diagrams for o in d.objects if o.kind == "block"]
    assert [b.type_name for b in blocks] == ["MBP_MSTR", "RESET", "SET", "TON", "SET", "ADD"]
    assert ld.ladder_rungs == []


def test_enable_pins_and_single_block_order_are_separate_from_wiring():
    results, diagnostics = diagrams('''<FBDSource><networkFBD>
      <textBox>Label</textBox><FFBBlock instanceName="call" typeName="FN">
        <descriptionFFB execAfter="">
          <inputVariable formalParameter="EN" effectiveParameter="run" invertedPin="false"/>
          <inputVariable formalParameter="ENABLE" effectiveParameter="request"/>
          <outputVariable formalParameter="ENO"/>
        </descriptionFFB>
      </FFBBlock>
    </networkFBD></FBDSource>''')
    diagram = results[0]
    assert diagram.execution_order == [1]
    assert diagram.execution_order_resolved
    assert diagram.execution_order_basis == "single_block_network"
    assert not diagram.connectivity_resolved
    block = diagram.objects[1]
    assert [p.role for p in block.pins] == ["execution_enable", "data", "execution_status"]
    assert block.pins[0].expression == "run"
    assert block.execution_after == ""


@pytest.mark.parametrize("extra", [
    '<FutureControl/>',
    '<FFBBlock typeName="SECOND"/>',
])
def test_single_block_rule_not_used_with_unknown_control_or_multiple_blocks(extra: str):
    results, diagnostics = diagrams(
        '<FBDSource><networkFBD><FFBBlock typeName="FIRST"/>' + extra + '</networkFBD></FBDSource>')
    assert not results[0].execution_order_resolved
    assert results[0].execution_order == []
    # Whole-project shared-variable dataflow may still resolve multi-block
    # order later; parse_diagrams alone no longer claims the diagram unresolved.
    assert not any(d.code == "unresolved_block_order" for d in diagnostics)


def test_execution_override_retained_without_guessing_reference_meaning():
    results, diagnostics = diagrams('''<FBDSource><networkFBD>
      <FFBBlock instanceName=".2"><descriptionFFB execAfter=".1"/></FFBBlock>
    </networkFBD></FBDSource>''')
    assert results[0].objects[0].execution_after == ".1"


def _fbd_with_link(link_body: str, *, extra_blocks: str = ""):
    return diagrams(f'''<FBDSource><networkFBD>
      <FFBBlock instanceName=".1" typeName="A" width="8" height="4">
        <objPosition posX="1" posY="1"/><descriptionFFB execAfter="">
          <outputVariable formalParameter="OUT"/>
        </descriptionFFB>
      </FFBBlock>
      <FFBBlock instanceName=".2" typeName="B" width="8" height="4">
        <objPosition posX="20" posY="1"/><descriptionFFB execAfter="">
          <inputVariable formalParameter="IN"/>
        </descriptionFFB>
      </FFBBlock>
      {extra_blocks}
      <linkFB>{link_body}</linkFB>
    </networkFBD></FBDSource>''')


def test_explicit_link_resolves_by_object_and_pin_name_not_position():
    # The link's own objPosition deliberately does not match either block's
    # position, proving resolution is by (instanceName, pinName), not proximity.
    results, diagnostics = _fbd_with_link('''
      <linkSource parentObjectName=".1" pinName="OUT"><objPosition posX="9" posY="4"/></linkSource>
      <linkDestination parentObjectName=".2" pinName="IN"><objPosition posX="20" posY="4"/></linkDestination>
    ''')
    diagram = results[0]
    assert len(diagram.links) == 1
    link = diagram.links[0]
    assert (link.source.status, link.source.object_index, link.source.pin_index) == ("resolved", 0, 0)
    assert (link.destination.status, link.destination.object_index, link.destination.pin_index) == ("resolved", 1, 0)
    assert not any(d.code == "unclassified_graphical_object" for d in diagnostics)
    assert not any(d.code == "unresolved_graphical_link_endpoint" for d in diagnostics)


@pytest.mark.parametrize("object_name,pin_name,expected_status", [
    ("missing", "OUT", "missing_object"),
    (".1", "MISSING", "missing_pin"),
    (".1", "IN", "missing_pin"),  # Block .1 declares no IN pin at all (only OUT).
])
def test_explicit_link_source_endpoint_failure_modes(object_name, pin_name, expected_status):
    results, diagnostics = _fbd_with_link(
        f'<linkSource parentObjectName="{object_name}" pinName="{pin_name}"/>'
        '<linkDestination parentObjectName=".2" pinName="IN"/>')
    link = results[0].links[0]
    assert link.source.status == expected_status
    assert link.source.object_index is None if expected_status == "missing_object" else True
    assert any(d.code == "unresolved_graphical_link_endpoint" for d in diagnostics)


def test_explicit_link_endpoint_ambiguous_object_is_diagnosed():
    results, diagnostics = _fbd_with_link(
        '<linkSource parentObjectName=".1" pinName="OUT"/>'
        '<linkDestination parentObjectName=".2" pinName="IN"/>',
        extra_blocks='<FFBBlock instanceName=".1" typeName="DUP"/>',
    )
    link = results[0].links[0]
    assert link.source.status == "ambiguous_object"
    assert link.source.object_index is None
    assert any(d.code == "unresolved_graphical_link_endpoint" for d in diagnostics)


def test_explicit_link_source_pin_wrong_direction_is_not_matched():
    # ".2" declares IN as an input; a link claiming it as a *source* pin must
    # not match an input-direction pin, even though the name is right.
    results, diagnostics = _fbd_with_link(
        '<linkSource parentObjectName=".2" pinName="IN"/>'
        '<linkDestination parentObjectName=".1" pinName="OUT"/>')
    link = results[0].links[0]
    assert link.source.status == "missing_pin" and link.source.object_index == 1
    assert link.destination.status == "missing_pin" and link.destination.object_index == 0


def test_malformed_endpoint_count_is_diagnosed_not_guessed():
    results, diagnostics = _fbd_with_link(
        '<linkSource parentObjectName=".1" pinName="OUT"/>'
        '<linkSource parentObjectName=".1" pinName="OUT"/>'
        '<linkDestination parentObjectName=".2" pinName="IN"/>')
    link = results[0].links[0]
    assert link.source.status == "unresolved" and link.source.object_name is None
    assert any(d.code == "invalid_graphical_link_endpoint_count" for d in diagnostics)


@pytest.mark.parametrize("filename", ["estradege_m580-safety.xef", "estradege_m340.xef"])
def test_optional_real_explicit_fbd_links_resolve(filename):
    path = Path(__file__).resolve().parents[1] / "reference" / "control-expert" / filename
    if not path.exists():
        pytest.skip("Local FBD link reference unavailable")
    result, = parse_projects(capture_file(path))
    links = [link for program in result.controller.programs.values()
             for routine in program.routines.values()
             for diagram in routine.graphical_diagrams for link in diagram.links]
    assert links
    assert all(link.source.status == "resolved" and link.destination.status == "resolved" for link in links)
    assert not any(d.code == "unclassified_graphical_object" for d in result.diagnostics)
