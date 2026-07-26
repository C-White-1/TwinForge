from pathlib import Path

from twinforge.analysis import analyze_aoi_portability
from twinforge.exporters import AOIPlantUMLExporter
from twinforge.parsers import L5XParser


DATA = Path(__file__).parent / "data/aoi"


def _diagram(name: str) -> str:
    plant = L5XParser().parse(DATA / name, report_mode=None)
    report = analyze_aoi_portability(next(plant.iter_controllers()))
    return AOIPlantUMLExporter().export(report)


def test_exports_portable_aoi_without_runtime_boundary():
    diagram = _diagram("Str_Capacity_AOI.L5X")

    assert diagram.startswith("@startuml DEVPAC_AOI_Portability\n")
    assert "Str_Capacity\\nfunction\\nportable_candidate" in diagram
    assert "PLCopen CBM: none/none" in diagram
    assert 'package "Target runtime adapter boundary"' not in diagram
    assert diagram.endswith("@enduml\n")


def test_exports_aoi_and_datatype_dependencies_deterministically():
    first = _diagram("dependencies_and_locals.L5X")
    second = _diagram("dependencies_and_locals.L5X")

    assert first == second
    assert first.startswith(
        "@startuml TestController_AOI_Portability\n"
    )
    assert "MainAOI\\nfunction_block\\nportable_candidate" in first
    assert '"ExampleData"' in first
    assert ": uses" in first
    assert ": datatype" in first
