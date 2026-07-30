"""Regression checks for the user-verified two-drive CODESYS export."""

from pathlib import Path
import xml.etree.ElementTree as ET


EXPORT = (
    Path(__file__).parents[1]
    / "examples"
    / "CODESYS"
    / "45_powerflex525_two_drive_project.export"
)


def _root() -> ET.Element:
    return ET.parse(EXPORT).getroot()


def test_native_export_contains_two_distinct_powerflex_devices() -> None:
    names = {
        element.text
        for element in _root().findall(".//Single[@Name='Name']")
    }

    assert "Dev_PF525_01" in names
    assert "Dev_PF525_02" in names


def test_native_export_preserves_distinct_device_addresses() -> None:
    values = {
        element.text
        for element in _root().findall(".//Single[@Name='Value']")
    }

    assert "[16#C0,16#A8,16#01,16#50]" in values
    assert "[16#C0,16#A8,16#01,16#51]" in values


def test_native_export_contains_isolated_generated_drive_calls() -> None:
    bodies = [
        element.text or ""
        for element in _root().findall(
            ".//Single[@Name='TextBlobForSerialisation']"
        )
    ]
    program = next(
        body
        for body in bodies
        if "fbPowerFlex525_PF525_01(" in body
    )

    assert program.count("fbPowerFlex525_PF525_01(") == 1
    assert program.count("fbPowerFlex525_PF525_02(") == 1
    assert program.count("PF525_01_fbModuleBinding(") == 1
    assert program.count("PF525_02_fbModuleBinding(") == 1
    assert "Dev_PF525_01.GetDeviceState()" in program
    assert "Dev_PF525_02.GetDeviceState()" in program
