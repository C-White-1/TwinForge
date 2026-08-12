from pathlib import Path

from twinforge.converters import DiagnosticSeverity
from twinforge.parsers import EDSParser


def test_parses_device_identity_and_preserves_unknown_sections(tmp_path: Path):
    source = tmp_path / "gateway.eds"
    source.write_text(
        """
$ Generated fixture
[File]
DescText = "Gateway $ identity";

[Device]
VendCode = 309;
VendName = "Prosoft Technology";
ProdType = 12;
ProdTypeStr = "Communications Adapter";
ProdCode = 0x146C;
MajRev = 1;
MinRev = 1;
ProdName = "PLX51-PBM";
FutureIdentity = "keep";

[Future Section]
Repeated = 1;
Repeated = 2;
Multiline =
    "first",
    "second";

[Assembly]
Object_Name = "Assembly Object";
Assem1 =
    "Input, Primary",
    ,
    ,
    0x0000,
    ,,
    4000,Param2;

[Connection Manager]
Connection1 =
    0x04010002,
    0x44640405,
    Param1,496,Assem2,
    Param1,500,Assem1,
    ,,
    0,,
    "I/O Connection",
    "Cyclic data",
    "20 04 24 66 2C 85 2C 84";
""",
        encoding="utf-8",
    )

    document = EDSParser().parse(source)

    identity = document.identity
    assert identity.vendor is not None
    assert identity.vendor.id == 309
    assert identity.vendor.name == "Prosoft Technology"
    assert identity.product_type == 12
    assert identity.product_type_name == "Communications Adapter"
    assert identity.product_code == 5228
    assert identity.product_name == "PLX51-PBM"
    assert identity.revision is not None
    assert (identity.revision.major, identity.revision.minor) == (1, 1)
    assert document.preamble[1] == "$ Generated fixture"
    file_section = document.section("file")
    assert file_section is not None
    assert file_section.value("DescText") == '"Gateway $ identity"'
    future = document.section("future section")
    assert future is not None
    assert future.values("Repeated") == ("1", "2")
    assert '"second"' in (future.value("Multiline") or "")
    extension = identity.source_extensions[0]
    assert extension.format == "EDS"
    assert extension.root.children[-1].name == "FutureIdentity"
    assert extension.root.children[-1].text == '"keep"'
    assert len(document.assemblies) == 1
    assembly = document.assemblies[0]
    assert assembly.reference == "Assem1"
    assert assembly.name == "Input, Primary"
    assert assembly.descriptor == 0
    assert assembly.declared_count == 4000
    assert assembly.parameter_reference == "Param2"
    assert len(assembly.fields) == 8
    assert "4000,Param2" in assembly.raw_statement
    assert len(document.connections) == 1
    connection = document.connections[0]
    assert connection.reference == "Connection1"
    assert connection.transport_class_trigger == 0x04010002
    assert connection.connection_parameters == 0x44640405
    assert connection.originator_to_target.parameter_reference == "Param1"
    assert connection.originator_to_target.declared_size == 496
    assert connection.originator_to_target.assembly_reference == "Assem2"
    assert connection.target_to_originator.declared_size == 500
    assert connection.target_to_originator.assembly_reference == "Assem1"
    assert connection.proxy_config_size is None
    assert connection.target_config_size == 0
    assert connection.name == "I/O Connection"
    assert connection.help_text == "Cyclic data"
    assert connection.path_text == "20 04 24 66 2C 85 2C 84"
    assert connection.path == (0x20, 0x04, 0x24, 0x66, 0x2C, 0x85, 0x2C, 0x84)
    assert len(connection.fields) == 15
    assert document.diagnostics == ()


def test_invalid_identity_integer_is_diagnosed_and_retained(tmp_path: Path):
    source = tmp_path / "invalid.eds"
    source.write_text(
        """
[Device]
VendCode = future;
VendName = "Future Vendor";
ProdCode = 7;
""",
        encoding="utf-8",
    )
    parser = EDSParser()

    document = parser.parse(source)

    assert document.identity.vendor is None
    assert document.identity.product_code == 7
    device = document.section("Device")
    assert device is not None
    assert device.value("VendCode") == "future"
    assert len(document.diagnostics) == 1
    assert document.diagnostics[0].code == "invalid_eds_integer"
    assert document.diagnostics[0].severity is DiagnosticSeverity.WARNING
    assert document.diagnostics[0].raw_value == "future"


def test_missing_device_section_returns_preserved_document_with_diagnostic(
    tmp_path: Path,
):
    source = tmp_path / "missing.eds"
    source.write_text("[Future]\nValue = 1;\n", encoding="utf-8")

    document = EDSParser().parse(source)

    assert document.identity.vendor is None
    assert document.section("Future") is not None
    assert [item.code for item in document.diagnostics] == [
        "eds_device_section_missing"
    ]
    assert document.diagnostics[0].severity is DiagnosticSeverity.ERROR


def test_malformed_assembly_fields_are_diagnosed_without_loss(tmp_path: Path):
    source = tmp_path / "assembly.eds"
    source.write_text(
        """
[Device]
VendCode = 1;
[Assembly]
Assem9 = "Future",,;
Assem10 = "Bad Count",,,0,,,many,Param7;
""",
        encoding="utf-8",
    )

    document = EDSParser().parse(source)

    assert [item.reference for item in document.assemblies] == [
        "Assem9",
        "Assem10",
    ]
    assert document.assemblies[0].fields == ('"Future"', "", "")
    assert document.assemblies[1].declared_count is None
    assert {item.code for item in document.diagnostics} == {
        "invalid_eds_assembly",
        "invalid_eds_assembly_integer",
    }


def test_malformed_connection_fields_are_diagnosed_without_loss(tmp_path: Path):
    source = tmp_path / "connection.eds"
    source.write_text(
        """
[Device]
VendCode = 1;
[Connection Manager]
Connection9 = future,broken;
Connection10 = 2,4,Param1,many,Assem2,Param1,8,Assem1,,,0,,"Test","","GG";
""",
        encoding="utf-8",
    )

    document = EDSParser().parse(source)

    assert [item.reference for item in document.connections] == [
        "Connection9",
        "Connection10",
    ]
    assert document.connections[0].fields == ("future", "broken")
    assert document.connections[1].originator_to_target.declared_size is None
    assert document.connections[1].path is None
    assert {item.code for item in document.diagnostics} == {
        "invalid_eds_connection",
        "invalid_eds_connection_integer",
        "invalid_eds_connection_path",
    }
