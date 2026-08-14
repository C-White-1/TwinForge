"""Tests for validated, reproducible CODESYS deployment bundles."""

from pathlib import Path
import json

from pydantic import ValidationError
import pytest

from twinforge.targets.codesys import (
    CodesysEtherNetIPConnectionManifest,
    CodesysDeploymentBundlePackager,
    CodesysPowerFlex525BundleExporter,
    CodesysPowerFlex525DeploymentManifest,
    load_codesys_powerflex525_manifest,
)


ROOT = Path(__file__).parents[1]
MANIFEST = (
    ROOT
    / "examples"
    / "deployment"
    / "powerflex525_two_drive.json"
)


def test_manifest_loads_two_unique_validated_devices() -> None:
    manifest = load_codesys_powerflex525_manifest(MANIFEST)

    assert len(manifest.devices) == 2
    assert str(manifest.devices[0].ip_address) == "192.168.1.80"
    assert manifest.devices[1].device_variable == "Dev_PF525_02"


def test_powerflex_device_uses_reusable_ethernetip_connection_contract() -> None:
    manifest = load_codesys_powerflex525_manifest(MANIFEST)
    device = manifest.devices[0]

    assert isinstance(device, CodesysEtherNetIPConnectionManifest)
    assert device.rpi_ms == 10
    assert device.output_bytes == 4
    assert device.input_bytes == 8
    assert device.connection_path == (32, 4, 36, 6, 44, 2, 44, 1)


def test_generic_ethernetip_connection_requires_explicit_valid_evidence() -> None:
    connection = CodesysEtherNetIPConnectionManifest(
        rpi_ms=20,
        output_bytes=496,
        input_bytes=500,
        connection_path=(32, 4, 36, 102, 44, 133, 44, 132),
    )

    assert connection.connection_path[-2:] == (44, 132)
    with pytest.raises(ValidationError, match="must not be empty"):
        CodesysEtherNetIPConnectionManifest(
            rpi_ms=20,
            output_bytes=496,
            input_bytes=500,
            connection_path=(),
        )


def test_generic_packager_writes_supplied_profile_artifacts(tmp_path: Path) -> None:
    native = tmp_path / "source.export"
    native.write_text("<native-profile />", encoding="utf-8")

    bundle = CodesysDeploymentBundlePackager().package(
        tmp_path / "generic-bundle",
        manifest_payload={
            "schema_version": 1,
            "profile": "fixture",
            "native_template": str(native),
        },
        application_xml="<project />",
        native_template_source=native,
        instructions_markdown="# Import fixture\n",
    )

    assert bundle.application.read_text(encoding="utf-8") == "<project />"
    assert bundle.native_template.read_text(encoding="utf-8") == (
        "<native-profile />"
    )
    payload = json.loads(bundle.manifest.read_text(encoding="utf-8"))
    assert payload == {
        "schema_version": 1,
        "profile": "fixture",
        "native_template": "native-device-template.export",
    }
    assert bundle.instructions.read_text(encoding="utf-8") == (
        "# Import fixture\n"
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("ip_address", "999.1.1.1", "valid IPv4 address"),
        ("device_variable", "Dev-PF525", "IEC 61131-3 identifier"),
        ("rpi_ms", 0, "greater than 0"),
    ),
)
def test_manifest_rejects_invalid_external_values(
    field: str,
    value: object,
    message: str,
) -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload["devices"][0][field] = value

    with pytest.raises(ValidationError, match=message):
        CodesysPowerFlex525DeploymentManifest.model_validate(payload)


def test_manifest_rejects_duplicate_device_identity() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload["devices"][1]["name"] = "pf525_01"

    with pytest.raises(ValidationError, match="names must be unique"):
        CodesysPowerFlex525DeploymentManifest.model_validate(payload)


def test_bundle_contains_application_template_manifest_and_instructions(
    tmp_path: Path,
) -> None:
    manifest = load_codesys_powerflex525_manifest(MANIFEST)
    bundle = CodesysPowerFlex525BundleExporter().export(
        manifest,
        tmp_path / "bundle",
        manifest_directory=MANIFEST.parent,
    )

    assert bundle.application.is_file()
    assert bundle.native_template.read_bytes() == (
        ROOT
        / "examples"
        / "CODESYS"
        / "46_powerflex525_two_drive_device_template.export"
    ).read_bytes()
    normalized = json.loads(bundle.manifest.read_text(encoding="utf-8"))
    assert normalized["native_template"] == "native-device-template.export"
    assert normalized["native_template_scope"] == "device_configuration"
    application = bundle.application.read_text(encoding="utf-8")
    assert "fbPowerFlex525_PF525_01" in application
    assert "fbPowerFlex525_PF525_02" in application
    instructions = bundle.instructions.read_text(encoding="utf-8")
    assert "import `native-device-template.export`" in instructions
    assert "import `application.xml`" in instructions
    assert "Select `PLC Logic`" in instructions
    assert "`Application_1`" in instructions
    assert "`Dev_PF525_01`" in instructions
    assert "`Dev_PF525_02`" in instructions


def test_bundle_rejects_template_that_lacks_manifest_devices(
    tmp_path: Path,
) -> None:
    manifest = load_codesys_powerflex525_manifest(MANIFEST)
    incomplete = tmp_path / "incomplete.export"
    incomplete.write_text(
        '<Single Name="Name" Type="string">Dev_PF525_01</Single>',
        encoding="utf-8",
    )
    payload = manifest.model_dump()
    payload["native_template"] = incomplete
    invalid = CodesysPowerFlex525DeploymentManifest.model_validate(payload)

    with pytest.raises(ValueError, match="Dev_PF525_02"):
        CodesysPowerFlex525BundleExporter().export(
            invalid,
            tmp_path / "bundle",
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("rpi_ms", 20, "RPI 20 ms"),
        ("output_bytes", 5, "O->T size 5"),
        ("input_bytes", 9, "T->O size 9"),
        ("connection_path", [32, 4, 36, 7], "connection path"),
    ),
)
def test_bundle_rejects_connection_manifest_mismatches(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload["devices"][0][field] = value
    manifest = CodesysPowerFlex525DeploymentManifest.model_validate(payload)

    with pytest.raises(ValueError, match=message):
        CodesysPowerFlex525BundleExporter().export(
            manifest,
            tmp_path / "bundle",
            manifest_directory=MANIFEST.parent,
        )


def test_bundle_rejects_device_configuration_labelled_as_complete_project(
    tmp_path: Path,
) -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload["native_template_scope"] = "complete_project"
    manifest = CodesysPowerFlex525DeploymentManifest.model_validate(payload)

    with pytest.raises(
        ValueError,
        match="complete-project template does not contain PLC_PRG",
    ):
        CodesysPowerFlex525BundleExporter().export(
            manifest,
            tmp_path / "bundle",
            manifest_directory=MANIFEST.parent,
        )
