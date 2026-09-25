"""Standalone Derived Function Block export (.xdb/.XDB) capture and mapping."""
from io import BytesIO
import zipfile

import pytest

from twinforge.parsers.control_expert import (
    capture_bytes, parse_function_block_libraries, parse_function_block_library,
)


def _fb_exchange(body: str) -> bytes:
    return (
        '<FBExchangeFile>'
        '<fileHeader company="Schneider Automation" product="UnitySoControl V14.0" '
        'dateTime="date_and_time#2021-1-29-13:34:41" content="Function Block source file" '
        'DTDVersion="41"></fileHeader>'
        '<contentHeader name="Project" version="0.0.1" dateTime="date_and_time#2021-1-29-12:59:44"></contentHeader>'
        f'{body}'
        '</FBExchangeFile>'
    ).encode()


def library(body: str):
    return parse_function_block_library(capture_bytes(_fb_exchange(body), name="dfb.xdb"))


def test_capture_recognizes_the_fbexchangefile_root():
    captured = capture_bytes(_fb_exchange(
        '<FBSource nameOfFBType="M_ADD"><FBProgram name="Main">'
        '<STSource>SUM := A + B;</STSource></FBProgram></FBSource>'
    ), name="dfb.xdb")
    assert captured.kind == "xml"
    assert captured.section is not None
    assert captured.section.tag == "FBExchangeFile"


def test_single_program_st_body_resolves_with_interface():
    result = library('''
      <FBSource nameOfFBType="M_ADD"><comment>Add two words</comment>
        <inputParameters>
          <variables name="A" typeName="INT"/>
          <variables name="B" typeName="INT"/>
        </inputParameters>
        <outputParameters><variables name="SUM" typeName="INT"/></outputParameters>
        <FBProgram><STSource>SUM := A + B;</STSource></FBProgram>
      </FBSource>
    ''')
    assert result.controller.name == "M_ADD"
    aoi = result.controller.add_on_instructions["M_ADD"]
    assert aoi.description == "Add two words"
    assert [(p.name, p.data_type, p.usage) for p in aoi.parameters.values()] == [
        ("A", "INT", "input"), ("B", "INT", "input"), ("SUM", "INT", "output"),
    ]
    routine = aoi.routines["M_ADD"]
    assert routine.language == "ST"
    assert routine.structured_text == "SUM := A + B;"
    assert not any(d.code == "missing_function_block_name" for d in result.diagnostics)


def test_multiple_named_program_sections_resolve_independently():
    result = library('''
      <FBSource nameOfFBType="Get_Reg_Float">
        <inputParameters><variables name="RegisterNumber" typeName="UINT"/></inputParameters>
        <FBProgram name="GetSystemData"><STSource>x := 1;</STSource></FBProgram>
        <FBProgram name="RegisterCondition"><STSource>y := 2;</STSource></FBProgram>
        <FBProgram name="Read_Me"><STSource>(* docs *)</STSource></FBProgram>
      </FBSource>
    ''')
    aoi = result.controller.add_on_instructions["Get_Reg_Float"]
    assert set(aoi.routines) == {"GetSystemData", "RegisterCondition", "Read_Me"}
    assert aoi.routines["GetSystemData"].structured_text == "x := 1;"


def test_fbd_body_resolves_through_the_shared_graphical_parser():
    result = library('''
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
    assert routine.graphical_diagrams[0].objects[0].type_name == "AND_BOOL"


def test_crypted_body_retains_interface_only():
    result = library('''
      <FBSource nameOfFBType="_SECRET">
        <crypted Encoding="65001">AB12CD34</crypted>
        <ExternalToolsOnly>
          <inputParameters><variables name="IN" typeName="BOOL"/></inputParameters>
        </ExternalToolsOnly>
      </FBSource>
    ''')
    aoi = result.controller.add_on_instructions["_SECRET"]
    assert [(p.name, p.usage) for p in aoi.parameters.values()] == [("IN", "input")]
    assert aoi.routines == {}
    assert any(d.code == "encrypted_function_block_body" for d in result.diagnostics)


def test_missing_fbsource_is_diagnosed_not_silently_empty():
    result = library("")
    assert result.controller.name == ""
    assert result.controller.add_on_instructions == {}
    assert any(d.code == "missing_function_block_name" for d in result.diagnostics)


def test_non_fbexchangefile_root_is_rejected():
    captured = capture_bytes(b'<ZEFExchangeFile><contentHeader name="Example"/></ZEFExchangeFile>', name="p.zef")
    with pytest.raises(ValueError, match="Expected a captured Function Block exchange XML artifact"):
        parse_function_block_library(captured)


def test_parse_function_block_libraries_walks_an_archive():
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("a.xdb", _fb_exchange(
            '<FBSource nameOfFBType="A"><FBProgram><STSource>x := 1;</STSource></FBProgram></FBSource>'
        ))
        archive.writestr("b.XDB", _fb_exchange(
            '<FBSource nameOfFBType="B"><FBProgram><STSource>y := 2;</STSource></FBProgram></FBSource>'
        ))
        archive.writestr("readme.txt", b"not xml")
    captured = capture_bytes(buffer.getvalue(), name="bundle.zip")

    libraries = parse_function_block_libraries(captured)

    names = sorted(lib.controller.name for lib in libraries)
    assert names == ["A", "B"]
