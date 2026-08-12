from pathlib import Path

from twinforge.converters import DiagnosticSeverity
from twinforge.parsers import GSDParser


def test_parses_identity_and_limits_while_preserving_unknowns(tmp_path: Path):
    source = tmp_path / "gateway.gsd"
    source.write_text(
        """
; fixture
#Profibus_DP
Vendor_Name = "ProSoft; Technology"
Model_Name = "PLX51-PBM"
Revision = "V1.0"
Ident_Number = 0x10FE
Protocol_Ident = 0
Station_Type = 0
Hardware_Release = "V1.0"
Software_Release = "V1.0"
Max_Module = 40
Max_Input_Len = 244
Max_Output_Len = 244
Max_Data_Len = 488
Max_Diag_Data_Len = 244
Max_User_Prm_Data_Len = 3
Min_Slave_Intervall = 6
Future_Keyword = "keep"
Future_Keyword = "duplicate"
""",
        encoding="latin-1",
    )

    document = GSDParser().parse(source)

    assert document.directives == ("#Profibus_DP",)
    assert document.identity.vendor_name == "ProSoft; Technology"
    assert document.identity.model_name == "PLX51-PBM"
    assert document.identity.revision == "V1.0"
    assert document.identity.ident_number == 0x10FE
    assert document.identity.protocol_ident == 0
    assert document.identity.station_type == 0
    assert document.identity.hardware_release == "V1.0"
    assert document.identity.software_release == "V1.0"
    assert document.limits.max_modules == 40
    assert document.limits.max_input_length == 244
    assert document.limits.max_output_length == 244
    assert document.limits.max_data_length == 488
    assert document.limits.max_diagnostic_data_length == 244
    assert document.limits.max_user_parameter_data_length == 3
    assert document.limits.minimum_slave_interval == 6
    assert document.values("future_keyword") == ('"keep"', '"duplicate"')
    assert "Future_Keyword = \"keep\"" in document.raw_lines
    assert document.diagnostics == ()


def test_invalid_promoted_integer_is_diagnosed_and_retained(tmp_path: Path):
    source = tmp_path / "invalid.gsd"
    source.write_text(
        "#Profibus_DP\nIdent_Number = future\nMax_Module = 8\n",
        encoding="latin-1",
    )

    document = GSDParser().parse(source)

    assert document.identity.ident_number is None
    assert document.limits.max_modules == 8
    assert document.value("Ident_Number") == "future"
    assert len(document.diagnostics) == 1
    diagnostic = document.diagnostics[0]
    assert diagnostic.code == "invalid_gsd_integer"
    assert diagnostic.severity is DiagnosticSeverity.WARNING
    assert diagnostic.raw_value == "future"
