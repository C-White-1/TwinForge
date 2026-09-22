"""User-defined Function Block (DFB) capture: interface, locals and body."""
from pathlib import Path

import pytest

from twinforge.parsers.control_expert import capture_bytes, capture_file, parse_project, parse_projects


def project(body: str):
    return parse_project(capture_bytes(
        (f'<ZEFExchangeFile><contentHeader name="Example"/>{body}</ZEFExchangeFile>').encode(),
        name="project.xef",
    ))


def test_direct_parameters_and_st_body_resolve_cleanly():
    result = project('''
      <FBSource nameOfFBType="M_ADD"><comment>Add two words</comment>
        <inputParameters>
          <variables name="A" typeName="INT"/>
          <variables name="B" typeName="INT"/>
        </inputParameters>
        <outputParameters><variables name="SUM" typeName="INT"/></outputParameters>
        <FBProgram><STSource>SUM := A + B;</STSource></FBProgram>
      </FBSource>
    ''')
    aoi = result.controller.add_on_instructions["M_ADD"]
    assert aoi.description == "Add two words"
    assert [(p.name, p.data_type, p.usage) for p in aoi.parameters.values()] == [
        ("A", "INT", "input"), ("B", "INT", "input"), ("SUM", "INT", "output"),
    ]
    routine = aoi.routines["M_ADD"]
    assert routine.language == "ST"
    assert routine.structured_text == "SUM := A + B;"
    assert not any(d.code.startswith("unresolved_function_block")
                   or d.code == "ambiguous_function_block_body" for d in result.diagnostics)


def test_crypted_body_retains_interface_only():
    result = project('''
      <FBSource nameOfFBType="_SECRET">
        <crypted Encoding="65001">AB12CD34</crypted>
        <ExternalToolsOnly>
          <inputParameters><variables name="IN" typeName="BOOL"/></inputParameters>
          <outputParameters><variables name="OK" typeName="BOOL"/></outputParameters>
        </ExternalToolsOnly>
      </FBSource>
    ''')
    aoi = result.controller.add_on_instructions["_SECRET"]
    assert [(p.name, p.usage) for p in aoi.parameters.values()] == [("IN", "input"), ("OK", "output")]
    assert aoi.routines == {}
    assert any(d.code == "encrypted_function_block_body" for d in result.diagnostics)


def test_fbd_body_is_parsed_like_a_top_level_program():
    result = project('''
      <FBSource nameOfFBType="M_GATE">
        <inputParameters><variables name="IN" typeName="BOOL"/></inputParameters>
        <FBProgram><FBDSource><networkFBD>
          <FFBBlock instanceName=".1" typeName="AND_BOOL"/>
        </networkFBD></FBDSource></FBProgram>
      </FBSource>
    ''')
    aoi = result.controller.add_on_instructions["M_GATE"]
    routine = aoi.routines["M_GATE"]
    assert routine.language == "FBD"
    assert len(routine.graphical_diagrams) == 1
    assert routine.graphical_diagrams[0].objects[0].type_name == "AND_BOOL"


def test_fbd_body_pin_resolves_against_the_fbs_own_parameter_end_to_end():
    result = project('''
      <FBSource nameOfFBType="M_GATE">
        <inputParameters><variables name="IN" typeName="BOOL"/></inputParameters>
        <FBProgram><FBDSource><networkFBD>
          <FFBBlock instanceName=".1" typeName="AND_BOOL">
            <descriptionFFB><inputVariable formalParameter="IN1" effectiveParameter="IN"/></descriptionFFB>
          </FFBBlock>
        </networkFBD></FBDSource></FBProgram>
      </FBSource>
    ''')
    aoi = result.controller.add_on_instructions["M_GATE"]
    pin = aoi.routines["M_GATE"].graphical_diagrams[0].objects[0].pins[0]
    assert pin.binding_kind == "declared_symbol"
    assert pin.target_parameter is aoi.parameters["IN"]
    assert pin.target_tag is None


def test_fbd_body_pin_does_not_fall_back_to_a_same_named_global_tag():
    result = project('''
      <dataBlock><variables name="IN" typeName="BOOL"/></dataBlock>
      <FBSource nameOfFBType="M_GATE">
        <inputParameters><variables name="OTHER" typeName="BOOL"/></inputParameters>
        <FBProgram><FBDSource><networkFBD>
          <FFBBlock instanceName=".1" typeName="AND_BOOL">
            <descriptionFFB><inputVariable formalParameter="IN1" effectiveParameter="IN"/></descriptionFFB>
          </FFBBlock>
        </networkFBD></FBDSource></FBProgram>
      </FBSource>
    ''')
    aoi = result.controller.add_on_instructions["M_GATE"]
    pin = aoi.routines["M_GATE"].graphical_diagrams[0].objects[0].pins[0]
    assert pin.binding_kind == "missing_symbol"
    assert pin.target_tag is None and pin.target_parameter is None
    assert any(d.code == "unresolved_pin_symbol" for d in result.diagnostics)


def test_public_and_private_local_variables_are_captured():
    result = project('''
      <FBSource nameOfFBType="M_STATE">
        <publicLocalVariables><variables name="Pub" typeName="BOOL"/></publicLocalVariables>
        <privateLocalVariables><variables name="Priv" typeName="INT"/></privateLocalVariables>
        <FBProgram><STSource>Pub := TRUE;</STSource></FBProgram>
      </FBSource>
    ''')
    aoi = result.controller.add_on_instructions["M_STATE"]
    assert {t.name: t.data_type for t in aoi.local_tags.values()} == {"Pub": "BOOL", "Priv": "INT"}
    assert aoi.local_tags["Pub"].metadata["visibility"] == "public"
    assert aoi.local_tags["Priv"].metadata["visibility"] == "private"


def test_ambiguous_body_is_diagnosed_not_guessed():
    result = project('''
      <FBSource nameOfFBType="M_DUP">
        <FBProgram><STSource>A := 1;</STSource></FBProgram>
        <FBProgram><STSource>A := 2;</STSource></FBProgram>
      </FBSource>
    ''')
    aoi = result.controller.add_on_instructions["M_DUP"]
    assert aoi.routines == {}
    assert any(d.code == "ambiguous_function_block_body" for d in result.diagnostics)


def test_missing_body_is_diagnosed():
    result = project('<FBSource nameOfFBType="M_EMPTY"/>')
    aoi = result.controller.add_on_instructions["M_EMPTY"]
    assert aoi.routines == {}
    assert any(d.code == "unresolved_function_block_body" for d in result.diagnostics)


def test_duplicate_function_block_name_is_ambiguous():
    result = project('''
      <FBSource nameOfFBType="DUP"><FBProgram><STSource>A := 1;</STSource></FBProgram></FBSource>
      <FBSource nameOfFBType="DUP"><FBProgram><STSource>A := 2;</STSource></FBProgram></FBSource>
    ''')
    assert list(result.controller.add_on_instructions) == ["DUP"]
    assert sum(d.code == "ambiguous_identity" for d in result.diagnostics) == 1


def test_duplicate_parameter_name_within_one_fb_is_ambiguous():
    result = project('''
      <FBSource nameOfFBType="M_BAD">
        <inputParameters>
          <variables name="A" typeName="BOOL"/>
          <variables name="A" typeName="BOOL"/>
        </inputParameters>
        <FBProgram><STSource>A := TRUE;</STSource></FBProgram>
      </FBSource>
    ''')
    aoi = result.controller.add_on_instructions["M_BAD"]
    assert len(aoi.parameters) == 1
    assert any(d.code == "ambiguous_identity" for d in result.diagnostics)


def test_parameter_and_local_type_resolve_against_a_known_datatype():
    result = project('''
      <DDTSource DDTName="T_CMD"><structure><variables name="F" typeName="BOOL"/></structure></DDTSource>
      <FBSource nameOfFBType="M_USES_DDT">
        <inputParameters><variables name="CMD" typeName="T_CMD"/></inputParameters>
        <privateLocalVariables><variables name="Local" typeName="T_CMD"/></privateLocalVariables>
        <FBProgram><STSource>CMD.F := TRUE;</STSource></FBProgram>
      </FBSource>
    ''')
    aoi = result.controller.add_on_instructions["M_USES_DDT"]
    ddt = result.controller.datatypes["T_CMD"]
    param = next(iter(aoi.parameters.values()))
    local = next(iter(aoi.local_tags.values()))
    assert param.data_type_definition is ddt
    assert local.data_type_definition is ddt
    assert not any(d.code == "unresolved_type" for d in result.diagnostics)


def test_function_block_is_a_library_interface_for_call_validation():
    result = project('''
      <FBSource nameOfFBType="M_ADD">
        <inputParameters><variables name="A" typeName="INT"/></inputParameters>
        <outputParameters><variables name="OUT" typeName="INT"/></outputParameters>
        <FBProgram><STSource>OUT := A;</STSource></FBProgram>
      </FBSource>
      <program><identProgram name="Main"/><FBDSource><networkFBD>
        <FFBBlock instanceName=".1" typeName="M_ADD"><descriptionFFB>
          <inputVariable formalParameter="A" effectiveParameter="x"/>
          <outputVariable formalParameter="OUT" effectiveParameter="y"/>
        </descriptionFFB></FFBBlock>
      </networkFBD></FBDSource></program>
    ''')
    interface = next(i for i in result.library_interfaces if i.name == "M_ADD")
    assert interface.kind == "user_function_block"
    routine = result.controller.programs["Main"].main_routine
    assert routine is not None
    # match_library_calls already ran as part of parse_project's own pipeline.
    block = routine.graphical_diagrams[0].objects[0]
    assert block.interface_status == "matched"
    assert all(pin.interface_status == "matched" for pin in block.pins)


@pytest.mark.parametrize("filename", ["estradege_m580-safety.xef"])
def test_optional_real_m580_safety_function_blocks(filename):
    path = Path(__file__).resolve().parents[1] / "reference" / "control-expert" / filename
    if not path.exists():
        pytest.skip("Local M580 safety reference unavailable")
    result, = parse_projects(capture_file(path))
    controller = result.controller
    assert len(controller.add_on_instructions) == 83
    body_languages: dict[str, int] = {}
    crypted_count = 0
    for aoi in controller.add_on_instructions.values():
        if aoi.routines:
            language = next(iter(aoi.routines.values())).language
            assert language is not None
            body_languages[language] = body_languages.get(language, 0) + 1
        else:
            crypted_count += 1
    assert body_languages == {"ST": 66, "FBD": 10}
    assert crypted_count == 7  # every remaining bodyless block is genuinely encrypted.
    assert sum(d.code == "encrypted_function_block_body" for d in result.diagnostics) == 7
    assert sum(d.code == "ambiguous_function_block_body" for d in result.diagnostics) == 0

    # IO_AI_EX has separately named INIT and MAIN sections; both are kept, and
    # INIT's activation condition (previously unreachable) is now captured.
    two_sections = controller.add_on_instructions["IO_AI_EX"]
    assert list(two_sections.routines) == ["INIT", "MAIN"]
    assert two_sections.routines["INIT"].metadata["section_conditions"]["activation"] == {
        "text": "%S13", "binding_kind": "direct_address"}
    assert two_sections.routines["MAIN"].metadata["function_block_section"] == {"index": 1, "count": 2}

    sample = controller.add_on_instructions["M_DWORD_TO_BIT"]
    assert sample.parameters["IN"].data_type == "DWORD"
    assert len(sample.parameters) == 33  # IN plus 32 output bits.

    user_fb_interfaces = [i for i in result.library_interfaces if i.kind == "user_function_block"]
    assert len(user_fb_interfaces) == 83
    matched_calls = sum(
        1 for program in controller.programs.values() for routine in program.routines.values()
        for diagram in routine.graphical_diagrams for obj in diagram.objects
        if obj.interface_status == "matched" and obj.type_name in controller.add_on_instructions
    )
    assert matched_calls > 0

    # Pins inside a DFB body resolve against that DFB's own parameters/locals,
    # never the project's global tags -- IEC 61131-3 encapsulation.
    fb_body_bindings: dict[str, int] = {}
    parameter_bound = 0
    for aoi in controller.add_on_instructions.values():
        for routine in aoi.routines.values():
            for diagram in routine.graphical_diagrams:
                for obj in diagram.objects:
                    for pin in obj.pins:
                        fb_body_bindings[pin.binding_kind] = fb_body_bindings.get(pin.binding_kind, 0) + 1
                        if pin.target_parameter is not None:
                            parameter_bound += 1
                            assert pin.target_tag is None
    assert fb_body_bindings.get("declared_symbol", 0) > 0
    assert parameter_bound > 0


def test_distinctly_named_sections_are_all_captured_without_an_order_claim():
    result = project('''
      <FBSource nameOfFBType="M_TWO">
        <FBProgram name="code1"><STSource>A := 1;</STSource></FBProgram>
        <FBProgram name="Code2"><FBDSource><networkFBD/></FBDSource></FBProgram>
      </FBSource>
    ''')
    aoi = result.controller.add_on_instructions["M_TWO"]
    assert list(aoi.routines) == ["code1", "Code2"]
    assert [r.language for r in aoi.routines.values()] == ["ST", "FBD"]
    assert aoi.routines["code1"].metadata["function_block_section"] == {"index": 0, "count": 2}
    assert not any(d.code == "ambiguous_function_block_body" for d in result.diagnostics)


def test_same_named_sections_stay_ambiguous_case_insensitively():
    result = project('''
      <FBSource nameOfFBType="M_SAME">
        <FBProgram name="Main"><STSource>A := 1;</STSource></FBProgram>
        <FBProgram name="MAIN"><STSource>A := 2;</STSource></FBProgram>
      </FBSource>
    ''')
    assert result.controller.add_on_instructions["M_SAME"].routines == {}
    assert any(d.code == "ambiguous_function_block_body" for d in result.diagnostics)


def test_a_single_section_keeps_the_block_name_and_no_section_metadata():
    result = project('''
      <FBSource nameOfFBType="M_ONE"><FBProgram name="code"><STSource>A := 1;</STSource></FBProgram></FBSource>
    ''')
    routine = result.controller.add_on_instructions["M_ONE"].routines["M_ONE"]
    assert "function_block_section" not in routine.metadata
