from pathlib import Path
import runpy

from twinforge.converters import ConversionDiagnostic, DiagnosticSeverity
from twinforge.parsers import L5XParser


SAMPLE_L5X = Path(__file__).parent / "data/basic/BoosterCompressor_20260128.L5X"
SCRIPT = Path(__file__).parents[1] / "examples/parse_l5x.py"
SCRIPT_GLOBALS = runpy.run_path(str(SCRIPT), run_name="parse_l5x")
print_model_summary = SCRIPT_GLOBALS["print_model_summary"]
print_diagnostics = SCRIPT_GLOBALS["print_diagnostics"]


def test_compact_model_summary_avoids_raw_dataclass_output(capsys):
    plant = L5XParser().parse(SAMPLE_L5X, report_mode=None)

    print_model_summary(plant)

    output = capsys.readouterr().out
    assert "Plant: booster_compressor" in output
    assert "Controller tags: 154" in output
    assert "Program: MainProgram" in output
    assert "Routines: 10" in output
    assert "Task: MainTask" in output
    assert "Plant(name=" not in output
    assert "id=" not in output


def test_optional_model_lists(capsys):
    plant = L5XParser().parse(SAMPLE_L5X, report_mode=None)

    print_model_summary(
        plant,
        list_modules=True,
        list_tags=True,
        list_routines=True,
    )

    output = capsys.readouterr().out
    assert "slot 2: DI_Slot2 [1756-IB16]" in output
    assert "AlmActive: Alias (Local:3:O.Data.14)" in output
    assert "MainRoutine: RLL" in output


def test_diagnostic_summary_is_compact(capsys):
    print_diagnostics(
        [
            ConversionDiagnostic(
                severity=DiagnosticSeverity.WARNING,
                code="example_warning",
                message="Something needs attention",
                object_name="Example",
            )
        ]
    )

    output = capsys.readouterr().out
    assert "Diagnostics: 1" in output
    assert "WARNING example_warning [Example]: Something needs attention" in output
