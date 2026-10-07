"""Machine Expert – Basic `.smbp` basic mapping: controller, tags, POUs, rungs."""
import pytest

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


def test_duplicate_symbol_is_reported_not_overwritten():
    software = ("<MemoryBits><MemoryBit><Address>%M0</Address><Symbol>RUN</Symbol></MemoryBit>"
                "<MemoryBit><Address>%M1</Address><Symbol>run</Symbol></MemoryBit></MemoryBits>")

    result = _parse(_smbp(software))

    assert result.controller.tags["RUN"].metadata["source_memory_address"] == "%M0"
    assert _codes(result) == ["ambiguous_identity"]


def test_symbol_outside_declared_tables_is_reported():
    software = "<Counters><CounterC><Address>%C0</Address><Symbol>PARTS</Symbol></CounterC></Counters>"

    result = _parse(_smbp(software))

    assert "PARTS" not in result.controller.tags
    assert _codes(result) == ["unmapped_symbol"]
    assert "'PARTS'" in result.diagnostics[-1].message


def test_pou_becomes_program_with_ladder_routine_and_rungs():
    cells = _cell("NormalContact", 0, 0, "Left, Right", "%I0.0") + _cell("Coil", 0, 10, "Left", "%Q0.0")
    software = "<Pous>" + _pou("Main",
                               _rung(["LD    %I0.0", "ST    %Q0.0"], cells, comment="Start motor"),
                               _rung(["LD    %M0", "ST    %Q0.1"], ladder=False)) + "</Pous>"

    controller = _parse(_smbp(software)).controller

    routine = controller.programs["Main"].routines["Main"]
    assert routine.name == "Main" and routine.language == "LD"
    first, second = routine.ladder_rungs
    assert (first.number, first.comment, first.text) == (0, "Start motor", "LD    %I0.0\nST    %Q0.0")
    assert (second.number, second.comment, second.text) == (1, None, "LD    %M0\nST    %Q0.1")
    assert first.network is None  # Milestone 2
    # The grid is retained as rung evidence.
    rung_source = first.source_extensions[0].root
    elements = next(child for child in rung_source.children if child.name == "LadderElements")
    assert [cell.children[0].text for cell in elements.children] == ["NormalContact", "Coil"]


def test_pou_with_only_instruction_list_or_placeholder_cells_is_il():
    placeholder = _cell("None", 0, 3, "None")
    software = "<Pous>" + _pou("Calc", _rung(["LD 1", "ST %Q0.0"], placeholder, ladder=False)) + "</Pous>"

    routine = _parse(_smbp(software)).controller.programs["Calc"].routines["Calc"]

    assert routine.language == "IL"


def test_rung_without_instruction_list_is_reported():
    software = "<Pous>" + _pou("Main", _rung([], _cell("Coil", 0, 10, "Left", "%Q0.0"))) + "</Pous>"

    result = _parse(_smbp(software))

    assert result.controller.programs["Main"].routines["Main"].ladder_rungs[0].text is None
    assert _codes(result) == ["missing_instruction_list"]


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
