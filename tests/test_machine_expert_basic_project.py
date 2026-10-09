"""Machine Expert – Basic `.smbp` basic mapping: controller, tags, POUs, rungs."""
import pytest

from twinforge.model import LadderInstruction, LadderOperation, LadderPosition, LadderSeries
from twinforge.parsers.machine_expert_basic import capture_bytes, parse_project

BOM = b"\xef\xbb\xbf"


def _smbp(software: str = "", hardware: str = "", root: str = "ProjectDescriptor", head: str = "") -> bytes:
    head = head or "<ProjectVersion>2.2.0.0</ProjectVersion><Name>Mixer</Name>"
    hardware = hardware or "<Cpu><Reference>TM221CE16R</Reference></Cpu>"
    body = (f"{head}<HardwareConfiguration><Plc>{hardware}</Plc></HardwareConfiguration>"
            f"<SoftwareConfiguration>{software}</SoftwareConfiguration>")
    return BOM + f'<?xml version="1.0" encoding="utf-8"?><{root}>{body}</{root}>'.encode()


def _cell(kind: str, row: int, column: int, connection: str, descriptor: str = "") -> str:
    operand = f"<Descriptor>{descriptor}</Descriptor>" if descriptor else ""
    return (f"<LadderEntity><ElementType>{kind}</ElementType>{operand}<Row>{row}</Row>"
            f"<Column>{column}</Column><ChosenConnection>{connection}</ChosenConnection></LadderEntity>")


def _rung(il: list[str], cells: str = "", comment: str = "", ladder: bool = True) -> str:
    lines = "".join(f"<InstructionLineEntity><InstructionLine>{line}</InstructionLine><Comment /></InstructionLineEntity>"
                    for line in il)
    return (f"<RungEntity><LadderElements>{cells}</LadderElements><InstructionLines>{lines}</InstructionLines>"
            f"<Name /><MainComment>{comment}</MainComment><Label />"
            f"<IsLadderSelected>{'true' if ladder else 'false'}</IsLadderSelected></RungEntity>")


def _pou(name: str, *rungs: str) -> str:
    return (f"<ProgramOrganizationUnits><Name>{name}</Name><SectionNumber>1</SectionNumber>"
            f"<Rungs>{''.join(rungs)}</Rungs></ProgramOrganizationUnits>")


def _parse(data: bytes):
    return parse_project(capture_bytes(data))


def _codes(result) -> list[str]:
    return [d.code for d in result.diagnostics if d.code != "unclassified_content"]


def test_controller_name_version_and_cpu():
    result = _parse(_smbp())

    assert result.controller.name == "Mixer"
    assert result.controller.identity.product_name == "TM221CE16R"
    assert result.project_version == "2.2.0.0"
    assert result.encrypted is False
    assert _codes(result) == []


def test_named_symbol_table_entries_become_tags():
    hardware = ("<Cpu><Reference>TM221CE16R</Reference><DigitalInputs>"
                "<DiscretInput><Address>%I0.0</Address><Index>0</Index><Symbol>START_PB</Symbol>"
                "<Comment>Start push button</Comment></DiscretInput>"
                "<DiscretInput><Address>%I0.1</Address><Index>1</Index></DiscretInput>"
                "</DigitalInputs></Cpu>")
    software = ("<MemoryBits><MemoryBit><Address>%M0</Address><Index>0</Index><Symbol>RUN</Symbol></MemoryBit></MemoryBits>"
                "<SystemBits><MemoryBit><Address>%S0</Address><Index>0</Index><Symbol>SB_COLDSTART</Symbol>"
                "<Comment>Cold start</Comment></MemoryBit></SystemBits>")

    tags = _parse(_smbp(software, hardware)).controller.tags

    assert sorted(tags) == ["RUN", "SB_COLDSTART", "START_PB"]  # %I0.1 has no symbol
    assert tags["START_PB"].description == "Start push button"
    assert tags["START_PB"].metadata == {"source_symbol_table": "DigitalInputs", "source_memory_address": "%I0.0"}
    assert tags["RUN"].description is None
    assert tags["SB_COLDSTART"].metadata["source_symbol_table"] == "SystemBits"
    assert tags["START_PB"].source_extensions[0].root.name == "DiscretInput"


def test_tags_get_the_iec_type_schneider_documents_for_their_table():
    hardware = ("<Cpu><Reference>TM221CE16R</Reference><DigitalInputs><DiscretInput><Address>%I0.0</Address>"
                "<Symbol>START_PB</Symbol></DiscretInput></DigitalInputs></Cpu>")
    software = ("<MemoryBits><MemoryBit><Address>%M0</Address><Symbol>RUN</Symbol></MemoryBit></MemoryBits>"
                "<MemoryFloats><MemoryFloat><Address>%MF0</Address><Symbol>SPEED</Symbol></MemoryFloat></MemoryFloats>"
                "<MemoryWords><MemoryWord><Address>%MW0</Address><Symbol>COUNT</Symbol></MemoryWord></MemoryWords>"
                "<MemoryDoubleWords><MemoryDoubleWord><Address>%MD0</Address><Symbol>TOTAL</Symbol></MemoryDoubleWord>"
                "</MemoryDoubleWords>"
                "<Timers><TimerTM><Address>%TM0</Address><Symbol>DELAY</Symbol></TimerTM></Timers>"
                "<SystemBits><MemoryBit><Address>%S0</Address><Symbol>SB_COLD</Symbol></MemoryBit></SystemBits>")

    tags = _parse(_smbp(software, hardware)).controller.tags

    assert {name: tag.data_type for name, tag in tags.items()} == {
        "START_PB": "BOOL", "RUN": "BOOL", "SB_COLD": "BOOL", "SPEED": "REAL",
        # 16-bit / 32-bit two's complement (EIO0000003289.04, "Word Objects",
        # "Floating Point and Double Word Objects").
        "COUNT": "INT", "TOTAL": "DINT",
        # A function-block instance, not an elementary type.
        "DELAY": None,
    }


def test_duplicate_symbol_is_reported_not_overwritten():
    software = ("<MemoryBits><MemoryBit><Address>%M0</Address><Symbol>RUN</Symbol></MemoryBit>"
                "<MemoryBit><Address>%M1</Address><Symbol>run</Symbol></MemoryBit></MemoryBits>")

    result = _parse(_smbp(software))

    assert result.controller.tags["RUN"].metadata["source_memory_address"] == "%M0"
    assert _codes(result) == ["ambiguous_identity"]


def test_counter_symbol_becomes_tag():
    software = ("<Counters><Counter><Address>%C0</Address><Index>0</Index>"
                "<Symbol>PART_COUNT</Symbol></Counter></Counters>")

    result = _parse(_smbp(software))

    tag = result.controller.tags["PART_COUNT"]
    assert tag.metadata == {"source_symbol_table": "Counters", "source_memory_address": "%C0"}
    assert _codes(result) == []


def test_symbol_outside_declared_tables_is_reported():
    # A hypothetical table: any named entry the profile does not declare.
    software = "<FutureTable><FutureEntry><Address>%X0</Address><Symbol>PARTS</Symbol></FutureEntry></FutureTable>"

    result = _parse(_smbp(software))

    assert "PARTS" not in result.controller.tags
    assert _codes(result) == ["unmapped_symbol"]
    assert "'PARTS'" in result.diagnostics[-1].message


def _wire(row: int, first: int, last: int) -> str:
    return "".join(_cell("Line", row, column, "Left, Right") for column in range(first, last + 1))


def _source_child(rung, name: str):
    return next(child for child in rung.source_extensions[0].root.children if child.name == name)


def test_pou_becomes_program_with_ladder_routine_and_rungs():
    cells = (_cell("NormalContact", 0, 0, "Left, Right", "%I0.0") + _wire(0, 1, 9)
             + _cell("Coil", 0, 10, "Left", "%Q0.0"))
    software = "<Pous>" + _pou("Main",
                               _rung(["LD    %I0.0", "ST    %Q0.0"], cells, comment="Start motor"),
                               _rung(["LD    %M0", "ST    %Q0.1"], ladder=False)) + "</Pous>"

    result = _parse(_smbp(software))

    routine = result.controller.programs["Main"].routines["Main"]
    assert routine.name == "Main" and routine.language == "LD"
    first, second = routine.ladder_rungs
    assert (first.number, first.comment) == (0, "Start motor")
    assert first.network == LadderSeries((
        LadderInstruction(LadderOperation.NORMALLY_OPEN_CONTACT, "NormalContact", "%I0.0",
                          position=LadderPosition(column=0, row=0)),
        LadderInstruction(LadderOperation.COIL, "Coil", "%Q0.0", position=LadderPosition(column=10, row=0)),
    ))
    # An IL-only rung has no grid, so no network.
    assert (second.number, second.comment, second.network) == (1, None, None)
    # `text` means Logix RLL elsewhere in TwinForge, so IL never goes there;
    # it stays verbatim in the rung's source extension.
    assert first.text is None and second.text is None
    lines = _source_child(second, "InstructionLines")
    assert [entry.children[0].text for entry in lines.children] == ["LD    %M0", "ST    %Q0.1"]
    assert _codes(result) == []


def test_pou_with_only_instruction_list_or_placeholder_cells_is_il():
    placeholder = _cell("None", 0, 3, "None")
    software = "<Pous>" + _pou("Calc", _rung(["LD 1", "ST %Q0.0"], placeholder, ladder=False)) + "</Pous>"

    routine = _parse(_smbp(software)).controller.programs["Calc"].routines["Calc"]

    assert routine.language == "IL"


def test_rung_without_instruction_list_is_reported():
    cells = _cell("NormalContact", 0, 0, "Left, Right", "%I0.0") + _cell("Coil", 0, 1, "Left", "%Q0.0")
    software = "<Pous>" + _pou("Main", _rung([], cells)) + "</Pous>"

    result = _parse(_smbp(software))

    assert result.controller.programs["Main"].routines["Main"].ladder_rungs[0].network is not None
    assert _codes(result) == ["missing_instruction_list"]


def test_unreachable_output_gets_no_network():
    # A coil with no wire back to the rail.
    software = "<Pous>" + _pou("Main", _rung(["ST %Q0.0"], _cell("Coil", 0, 10, "Left", "%Q0.0"))) + "</Pous>"

    result = _parse(_smbp(software))

    assert result.controller.programs["Main"].routines["Main"].ladder_rungs[0].network is None
    assert _codes(result) == ["ladder_no_output"]


def test_duplicate_pou_name_is_reported():
    software = "<Pous>" + _pou("Main") + _pou("Main") + "</Pous>"

    result = _parse(_smbp(software))

    assert list(result.controller.programs) == ["Main"]
    assert _codes(result) == ["ambiguous_identity"]


def test_missing_name_and_cpu_are_reported():
    result = _parse(_smbp(head="<ProjectVersion>2.2.0.0</ProjectVersion>", hardware="<Cpu />"))

    assert result.controller.name == ""
    assert result.controller.identity.product_name is None
    assert _codes(result) == ["missing_project_name", "missing_cpu_reference"]


def test_encrypted_project_exposes_public_name_only():
    data = BOM + ('<?xml version="1.0" encoding="utf-8"?><CryptedProject>'
                  "<ProjectVersion>2.0.0.0</ProjectVersion><Crypted>QUJD</Crypted>"
                  "<PublicProperties><ProjectInformations><Name>Secret</Name></ProjectInformations>"
                  "</PublicProperties></CryptedProject>").encode()

    result = _parse(data)

    assert result.encrypted is True
    assert result.controller.name == "Secret"
    assert result.controller.programs == {} and result.controller.tags == {}
    assert _codes(result) == ["encrypted_project"]


def test_non_project_artifact_is_rejected():
    with pytest.raises(ValueError):
        parse_project(capture_bytes(b"<project/>"))
