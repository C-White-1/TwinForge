"""Tests for the installed CODESYS deployment command."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

from twinforge.cli import main


ROOT = Path(__file__).parents[1]
MANIFEST = ROOT / "examples/deployment/powerflex525_two_drive.json"


def test_codesys_bundle_command_writes_validated_artifacts(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "bundle"
    output = StringIO()
    errors = StringIO()

    result = main(
        (
            "codesys",
            "bundle",
            str(MANIFEST),
            "--output",
            str(destination),
        ),
        stdout=output,
        stderr=errors,
    )

    assert result == 0
    assert errors.getvalue() == ""
    assert (destination / "manifest.json").is_file()
    assert (destination / "application.xml").is_file()
    assert (destination / "native-device-template.export").is_file()
    assert (destination / "IMPORT.md").is_file()
    assert "Exported CODESYS deployment bundle" in output.getvalue()


def test_codesys_bundle_command_reports_invalid_manifest(
    tmp_path: Path,
) -> None:
    errors = StringIO()

    result = main(
        (
            "codesys",
            "bundle",
            str(tmp_path / "missing.json"),
            "--output",
            str(tmp_path / "bundle"),
        ),
        stderr=errors,
    )

    assert result == 1
    assert "cannot export CODESYS deployment manifest" in errors.getvalue()
    assert not (tmp_path / "bundle").exists()
