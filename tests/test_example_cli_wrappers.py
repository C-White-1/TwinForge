from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
DATA = ROOT / "tests/data"
CONTROLLER = DATA / "basic/BoosterCompressor_20260128.L5X"


def _run(script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "examples" / script), *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("profile", ("standard_201", "codesys"))
def test_plcopen_wrapper_delegates_to_installed_target(
    tmp_path: Path,
    profile: str,
) -> None:
    destination = tmp_path / f"{profile}.xml"

    result = _run(
        "export_plcopen.py",
        str(CONTROLLER),
        str(destination),
        "--profile",
        profile,
    )

    assert result.returncode == 0, result.stderr
    assert destination.is_file()
    assert "Exported" in result.stdout


def test_automationml_wrapper_delegates_to_installed_target(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "plant.aml"

    result = _run(
        "export_automationml.py",
        str(CONTROLLER),
        str(destination),
        "--base-library",
        str(DATA / "automationml_base_libraries.aml"),
    )

    assert result.returncode == 0, result.stderr
    assert destination.is_file()
    assert "Exported AutomationML 2.1" in result.stdout


def test_report_wrapper_delegates_to_installed_command(tmp_path: Path) -> None:
    destination = tmp_path / "reports"

    result = _run("export_reports.py", str(CONTROLLER), str(destination))

    assert result.returncode == 0, result.stderr
    assert destination.is_dir()
    assert "Exported" in result.stdout
