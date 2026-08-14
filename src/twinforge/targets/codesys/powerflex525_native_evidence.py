"""Validate native CODESYS evidence for PowerFlex 525 deployments."""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import IPv4Address
from pathlib import Path
from typing import Literal
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class PowerFlex525NativeDeviceExpectation:
    """Expected native CODESYS evidence for one PowerFlex 525 device."""

    device_variable: str
    ip_address: IPv4Address
    rpi_ms: int
    output_bytes: int
    input_bytes: int
    connection_path: tuple[int, ...]


class PowerFlex525NativeEvidenceValidator:
    """Check a CODESYS export against PowerFlex deployment expectations."""

    def validate(
        self,
        native_source: str | Path,
        *,
        template_scope: Literal["complete_project", "device_configuration"],
        devices: tuple[PowerFlex525NativeDeviceExpectation, ...],
    ) -> None:
        """Require matching scope, identity, address, and connection evidence."""

        root = ET.parse(native_source).getroot()
        problems = self._scope_problems(root, template_scope)
        for device in devices:
            problems.extend(self._device_problems(root, device))
        if problems:
            raise ValueError(
                "native CODESYS template is inconsistent with manifest: "
                + "; ".join(problems)
            )

    @staticmethod
    def _scope_problems(
        root: ET.Element,
        template_scope: Literal["complete_project", "device_configuration"],
    ) -> list[str]:
        """Report application objects inconsistent with the declared scope."""

        object_names = {
            element.text
            for element in root.findall(".//Single[@Name='Name']")
            if element.text
        }
        application_objects = {
            "PLC_PRG",
            "TF_PowerFlex525_Core",
            "TF_Codesys_ENIP_ModuleBinding",
        }
        present = application_objects & object_names
        if template_scope == "device_configuration" and present:
            names = ", ".join(sorted(present))
            return [
                "device-configuration template contains application "
                f"objects: {names}"
            ]
        if template_scope == "complete_project" and "PLC_PRG" not in object_names:
            return ["complete-project template does not contain PLC_PRG"]
        return []

    def _device_problems(
        self,
        root: ET.Element,
        expected: PowerFlex525NativeDeviceExpectation,
    ) -> list[str]:
        """Report mismatched evidence for one expected native device."""

        native_device = self._native_device(root, expected.device_variable)
        if native_device is None:
            return [f"device {expected.device_variable}"]

        problems: list[str] = []
        address = "[" + ",".join(
            f"16#{octet:02X}" for octet in expected.ip_address.packed
        ) + "]"
        if self._native_value(native_device, "IP address of Target") != address:
            problems.append(
                f"address {expected.ip_address} for {expected.device_variable}"
            )

        rpi = self._native_value(native_device, "Requested packet interval")
        if rpi != str(expected.rpi_ms * 1000):
            problems.append(
                f"RPI {expected.rpi_ms} ms for {expected.device_variable}"
            )

        path = "[" + ",".join(
            f"16#{item:02X}" for item in expected.connection_path
        ) + "]"
        if self._native_value(native_device, "Connection Path") != path:
            problems.append(f"connection path for {expected.device_variable}")

        native_text = ET.tostring(native_device, encoding="unicode")
        if not self._parameter_count_matches(
            native_text, "Output_Param", expected.output_bytes
        ):
            problems.append(
                f"O->T size {expected.output_bytes} for {expected.device_variable}"
            )
        if not self._parameter_count_matches(
            native_text, "Input_Param", expected.input_bytes
        ):
            problems.append(
                f"T->O size {expected.input_bytes} for {expected.device_variable}"
            )
        return problems

    @staticmethod
    def _parameter_count_matches(
        native_text: str,
        prefix: str,
        expected_count: int,
    ) -> bool:
        """Return whether zero-based native parameters match the expected size."""

        found = sum(
            f">{prefix}{index}<" in native_text
            for index in range(expected_count)
        )
        return (
            found == expected_count
            and f">{prefix}{expected_count}<" not in native_text
        )

    @classmethod
    def _native_device(
        cls,
        root: ET.Element,
        device_variable: str,
    ) -> ET.Element | None:
        """Find the native object that owns one generated IEC variable."""

        parents = {
            child: parent
            for parent in root.iter()
            for child in parent
        }
        for name in root.findall(".//Single[@Name='Name']"):
            if name.text != device_variable:
                continue
            element = parents.get(name)
            while element is not None:
                if cls._native_value(element, "IP address of Target") is not None:
                    return element
                element = parents.get(element)
        return None

    @staticmethod
    def _native_value(root: ET.Element, visible_name: str) -> str | None:
        """Read a named CODESYS property from one native object."""

        for data in root.findall(".//Single"):
            name = data.find(
                "./Single[@Name='VisibleName']/Single[@Name='Default']"
            )
            value = data.find("./Single[@Name='Value']")
            if name is not None and name.text == visible_name and value is not None:
                return value.text
        return None
