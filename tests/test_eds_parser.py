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
