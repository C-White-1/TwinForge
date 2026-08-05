from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from io import StringIO
from pathlib import Path

from twinforge.cli import main
from twinforge.exporters import (
    CAEX_NAMESPACE,
    PLCOPEN_201_NAMESPACE,
    PLCOPEN_CODESYS_NAMESPACE,
)


DATA = Path(__file__).parent / "data"
CONTROLLER = DATA / "basic/BoosterCompressor_20260128.L5X"


def test_export_writes_generic_plcopen_xml(tmp_path: Path) -> None:
    destination = tmp_path / "nested/project.xml"
    output = StringIO()
    errors = StringIO()

    result = main(
        (
            "export",
            str(CONTROLLER),
            "--target",
            "plcopen",
            "--output",
            str(destination),
        ),
        stdout=output,
        stderr=errors,
    )

    assert result == 0
    assert errors.getvalue() == ""
    root = ET.parse(destination).getroot()
    assert root.tag == f"{{{PLCOPEN_201_NAMESPACE}}}project"
    xml = destination.read_text(encoding="utf-8")
    assert "www.3s-software.com" not in xml
    assert "Exported PLCopen XML 2.01" in output.getvalue()


def test_export_rejects_non_controller_target(tmp_path: Path) -> None:
    destination = tmp_path / "project.xml"
    errors = StringIO()

    result = main(
        (
            "export",
            str(DATA / "standalone/module.L5X"),
            "--target",
            "plcopen",
            "--output",
            str(destination),
        ),
        stderr=errors,
    )

    assert result == 1
    assert not destination.exists()
    assert "requires a Controller L5X target" in errors.getvalue()


def test_export_writes_codesys_profile_without_generic_namespace(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "codesys.xml"
    output = StringIO()

    result = main(
        (
            "export",
            str(CONTROLLER),
            "--target",
            "codesys",
            "--output",
            str(destination),
        ),
        stdout=output,
    )

    assert result == 0
    root = ET.parse(destination).getroot()
    assert root.tag == f"{{{PLCOPEN_CODESYS_NAMESPACE}}}project"
    xml = destination.read_text(encoding="utf-8")
    assert "www.3s-software.com/plcopenxml/application" in xml
    assert PLCOPEN_201_NAMESPACE not in xml
    assert "Exported CODESYS PLCopen XML" in output.getvalue()


def test_codesys_export_rejects_standard_xsd_option(tmp_path: Path) -> None:
    destination = tmp_path / "codesys.xml"
    errors = StringIO()

    result = main(
        (
            "export",
            str(CONTROLLER),
            "--target",
            "codesys",
            "--output",
            str(destination),
            "--xsd",
            str(tmp_path / "standard.xsd"),
        ),
        stderr=errors,
    )

    assert result == 1
    assert not destination.exists()
    assert "cannot be used with --target codesys" in errors.getvalue()


def test_export_writes_native_openplc_project(tmp_path: Path) -> None:
    destination = tmp_path / "openplc-project"
    output = StringIO()

    result = main(
        (
            "export",
            str(DATA / "openplc/native_boolean.L5X"),
            "--target",
            "openplc",
            "--output",
            str(destination),
            "--compile-only",
        ),
        stdout=output,
    )

    assert result == 0
    assert (destination / "project.json").is_file()
    assert (destination / "devices/configuration.json").is_file()
    ladder = destination / "pous/programs/main.ld"
    assert ladder.is_file()
    assert "XIC" not in ladder.read_text(encoding="utf-8")
    configuration = (destination / "devices/configuration.json").read_text(
        encoding="utf-8"
    )
    assert '"compileOnly": true' in configuration
    assert "Source program SourceProgram was lowered as main" in output.getvalue()


def test_openplc_export_rejects_unsupported_controller_without_writing(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "openplc-project"
    errors = StringIO()

    result = main(
        (
            "export",
            str(CONTROLLER),
            "--target",
            "openplc",
            "--output",
            str(destination),
        ),
        stderr=errors,
    )

    assert result == 1
    assert not destination.exists()
    assert "global-variable representation is not yet evidenced" in errors.getvalue()


def test_compile_only_is_rejected_for_plcopen_xml(tmp_path: Path) -> None:
    destination = tmp_path / "project.xml"
    errors = StringIO()

    result = main(
        (
            "export",
            str(CONTROLLER),
            "--target",
            "plcopen",
            "--output",
            str(destination),
            "--compile-only",
        ),
        stderr=errors,
    )

    assert result == 1
    assert not destination.exists()
    assert "applies only to --target openplc" in errors.getvalue()


def test_export_writes_semantically_valid_automationml(tmp_path: Path) -> None:
    destination = tmp_path / "nested/plant.aml"
    base_library = DATA / "automationml_base_libraries.aml"
    output = StringIO()

    result = main(
        (
            "export",
            str(CONTROLLER),
            "--target",
            "automationml",
            "--output",
            str(destination),
            "--base-library",
            str(base_library),
        ),
        stdout=output,
    )

    assert result == 0
    root = ET.parse(destination).getroot()
    assert root.tag == f"{{{CAEX_NAMESPACE}}}CAEXFile"
    assert root.attrib["SchemaVersion"] == "3.0"
    assert root.attrib["FileName"] == "plant.aml"
    reference = root.find(f"{{{CAEX_NAMESPACE}}}ExternalReference")
    assert reference is not None
    resolved = (destination.parent / reference.attrib["Path"]).resolve()
    assert resolved == base_library.resolve()
    assert "Exported AutomationML 2.1" in output.getvalue()


def test_automationml_requires_base_library_before_writing(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "plant.aml"
    errors = StringIO()

    result = main(
        (
            "export",
            str(CONTROLLER),
            "--target",
            "automationml",
            "--output",
            str(destination),
        ),
        stderr=errors,
    )

    assert result == 1
    assert not destination.exists()
    assert "--base-library is required" in errors.getvalue()


def test_openplc_config_maps_locations_and_cli_overrides_mode(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "openplc-project"
    config = tmp_path / "openplc.json"
    config.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "target": "openplc",
                "compile_only": True,
                "locations": {
                    "Enable": "%QX0.0",
                    "Output": "%QX0.1",
                },
            }
        ),
        encoding="utf-8",
    )

    result = main(
        (
            "export",
            str(DATA / "openplc/native_boolean.L5X"),
            "--target",
            "openplc",
            "--output",
            str(destination),
            "--config",
            str(config),
            "--no-compile-only",
        )
    )

    assert result == 0
    ladder = (destination / "pous/programs/main.ld").read_text(
        encoding="utf-8"
    )
    assert "Enable : bool AT %QX0.0;" in ladder
    assert "Output : bool AT %QX0.1;" in ladder
    device = (destination / "devices/configuration.json").read_text(
        encoding="utf-8"
    )
    assert '"compileOnly": false' in device


def test_openplc_config_rejects_unknown_fields_without_writing(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "openplc-project"
    config = tmp_path / "invalid.json"
    config.write_text(
        '{"schema_version":"1.0","target":"openplc","guess":true}',
        encoding="utf-8",
    )
    errors = StringIO()

    result = main(
        (
            "export",
            str(DATA / "openplc/native_boolean.L5X"),
            "--target",
            "openplc",
            "--output",
            str(destination),
            "--config",
            str(config),
        ),
        stderr=errors,
    )

    assert result == 1
    assert not destination.exists()
    assert "invalid OpenPLC export configuration" in errors.getvalue()


def test_plcopen_dry_run_reports_diagnostics_without_writing(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "project.xml"
    output = StringIO()

    result = main(
        (
            "export",
            str(CONTROLLER),
            "--target",
            "plcopen",
            "--output",
            str(destination),
            "--dry-run",
        ),
        stdout=output,
    )

    assert result == 0
    assert not destination.exists()
    assert "Ready to export PLCopen XML 2.01" in output.getvalue()
    assert "WARNING" in output.getvalue()


def test_openplc_dry_run_plans_files_without_writing(tmp_path: Path) -> None:
    destination = tmp_path / "openplc-project"
    output = StringIO()

    result = main(
        (
            "export",
            str(DATA / "openplc/native_boolean.L5X"),
            "--target",
            "openplc",
            "--output",
            str(destination),
            "--dry-run",
        ),
        stdout=output,
    )

    assert result == 0
    assert not destination.exists()
    assert "Ready to export native OpenPLC project" in output.getvalue()
    assert "pous\\programs\\main.ld" in output.getvalue()


def test_export_validation_failure_does_not_write_output(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "project.xml"
    invalid_schema = tmp_path / "invalid.xsd"
    invalid_schema.write_text("not an XML schema", encoding="utf-8")
    errors = StringIO()

    result = main(
        (
            "export",
            str(CONTROLLER),
            "--target",
            "plcopen",
            "--output",
            str(destination),
            "--xsd",
            str(invalid_schema),
        ),
        stderr=errors,
    )

    assert result == 1
    assert not destination.exists()
    assert "cannot export L5X" in errors.getvalue()
