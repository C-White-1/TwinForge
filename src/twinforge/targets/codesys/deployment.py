"""Validated CODESYS deployment manifests and reproducible bundle export."""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import IPv4Address
import json
from pathlib import Path
import re
import shutil
from typing import Literal
import xml.etree.ElementTree as ET

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from twinforge.exporters import (
    CodesysIRPLCopenExporter,
    PowerFlex525CodesysDevice,
    build_codesys_sys_module_binding_unit,
    build_powerflex525_iec_unit,
    powerflex525_codesys_multi_application_integration,
)


_IEC_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_POWERFLEX_CONNECTION_PATH = (
    0x20,
    0x04,
    0x24,
    0x06,
    0x2C,
    0x02,
    0x2C,
    0x01,
)


class CodesysPowerFlex525DeviceManifest(BaseModel):
    """External configuration for one PowerFlex 525 deployment instance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    device_variable: str
    ip_address: IPv4Address
    rpi_ms: int = Field(default=10, gt=0)
    output_bytes: int = Field(default=4, gt=0)
    input_bytes: int = Field(default=8, gt=0)
    connection_path: tuple[int, ...] = _POWERFLEX_CONNECTION_PATH

    @field_validator("name", "device_variable")
    @classmethod
    def _identifier(cls, value: str) -> str:
        if _IEC_IDENTIFIER.fullmatch(value) is None:
            raise ValueError("must be an IEC 61131-3 identifier")
        return value

    @field_validator("connection_path")
    @classmethod
    def _connection_path(
        cls,
        value: tuple[int, ...],
    ) -> tuple[int, ...]:
        if not value:
            raise ValueError("must not be empty")
        if any(item < 0 or item > 0xFF for item in value):
            raise ValueError("bytes must be between 0 and 255")
        return value


class CodesysPowerFlex525DeploymentManifest(BaseModel):
    """Validated boundary model for a CODESYS PowerFlex deployment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    project_name: str = "TwinForgePowerFlex525Application"
    native_template: Path
    native_template_scope: Literal[
        "complete_project",
        "device_configuration",
    ]
    devices: tuple[CodesysPowerFlex525DeviceManifest, ...] = Field(
        min_length=1
    )

    @field_validator("project_name")
    @classmethod
    def _project_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def _unique_devices(self) -> CodesysPowerFlex525DeploymentManifest:
        names = [item.name.casefold() for item in self.devices]
        if len(names) != len(set(names)):
            raise ValueError("device names must be unique")
        variables = [
            item.device_variable.casefold() for item in self.devices
        ]
        if len(variables) != len(set(variables)):
            raise ValueError("device variables must be unique")
        addresses = [item.ip_address for item in self.devices]
        if len(addresses) != len(set(addresses)):
            raise ValueError("device IP addresses must be unique")
        return self


@dataclass(frozen=True)
class CodesysDeploymentBundle:
    """Files written for one self-contained CODESYS deployment bundle."""

    directory: Path
    manifest: Path
    application: Path
    native_template: Path
    instructions: Path


class CodesysPowerFlex525BundleExporter:
    """Package validated application and native CODESYS deployment evidence."""

    def export(
        self,
        manifest: CodesysPowerFlex525DeploymentManifest,
        destination: str | Path,
        *,
        manifest_directory: str | Path | None = None,
    ) -> CodesysDeploymentBundle:
        """Write a self-contained deployment directory."""

        directory = Path(destination)
        directory.mkdir(parents=True, exist_ok=True)
        source_directory = Path(manifest_directory or ".")
        native_source = manifest.native_template
        if not native_source.is_absolute():
            native_source = source_directory / native_source
        native_source = native_source.resolve()
        if not native_source.is_file():
            raise FileNotFoundError(
                f"native CODESYS template does not exist: {native_source}"
            )
        self._validate_native_template(manifest, native_source)

        application = directory / "application.xml"
        integration = powerflex525_codesys_multi_application_integration(
            tuple(
                PowerFlex525CodesysDevice(
                    item.name,
                    item.device_variable,
                )
                for item in manifest.devices
            )
        )
        result = CodesysIRPLCopenExporter().export(
            build_powerflex525_iec_unit(),
            additional_units=(build_codesys_sys_module_binding_unit(),),
            destination=application,
            project_name=manifest.project_name,
            integration=integration,
        )
        if not result.complete:
            requirements = ", ".join(
                item.value for item in result.requirements
            )
            raise ValueError(
                "PLCopen application export is incomplete"
                + (f": {requirements}" if requirements else "")
            )

        native_destination = directory / "native-device-template.export"
        shutil.copyfile(native_source, native_destination)
        normalized_manifest = directory / "manifest.json"
        payload = manifest.model_dump(mode="json")
        payload["native_template"] = native_destination.name
        normalized_manifest.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        instructions = directory / "IMPORT.md"
        instructions.write_text(
            self._instructions(manifest),
            encoding="utf-8",
        )
        return CodesysDeploymentBundle(
            directory,
            normalized_manifest,
            application,
            native_destination,
            instructions,
        )

    @staticmethod
    def _validate_native_template(
        manifest: CodesysPowerFlex525DeploymentManifest,
        native_source: Path,
    ) -> None:
        """Require matching native identity, address, and connection evidence."""

        root = ET.parse(native_source).getroot()
        missing: list[str] = []
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
        present_application_objects = application_objects & object_names
        if (
            manifest.native_template_scope == "device_configuration"
            and present_application_objects
        ):
            names = ", ".join(sorted(present_application_objects))
            missing.append(
                "device-configuration template contains application "
                f"objects: {names}"
            )
        if (
            manifest.native_template_scope == "complete_project"
            and "PLC_PRG" not in object_names
        ):
            missing.append(
                "complete-project template does not contain PLC_PRG"
            )
        for device in manifest.devices:
            native_device = (
                CodesysPowerFlex525BundleExporter._native_device(
                    root,
                    device.device_variable,
                )
            )
            if native_device is None:
                missing.append(f"device {device.device_variable}")
                continue
            address_evidence = "[" + ",".join(
                f"16#{octet:02X}"
                for octet in device.ip_address.packed
            ) + "]"
            actual_address = CodesysPowerFlex525BundleExporter._native_value(
                native_device,
                "IP address of Target",
            )
            if actual_address != address_evidence:
                missing.append(
                    f"address {device.ip_address} for "
                    f"{device.device_variable}"
                )
            actual_rpi = CodesysPowerFlex525BundleExporter._native_value(
                native_device,
                "Requested packet interval",
            )
            if actual_rpi != str(device.rpi_ms * 1000):
                missing.append(
                    f"RPI {device.rpi_ms} ms for "
                    f"{device.device_variable}"
                )
            path_evidence = "[" + ",".join(
                f"16#{item:02X}" for item in device.connection_path
            ) + "]"
            actual_path = CodesysPowerFlex525BundleExporter._native_value(
                native_device,
                "Connection Path",
            )
            if actual_path != path_evidence:
                missing.append(
                    f"connection path for {device.device_variable}"
                )
            native_text = ET.tostring(
                native_device,
                encoding="unicode",
            )
            output_count = sum(
                f">Output_Param{index}<" in native_text
                for index in range(device.output_bytes)
            )
            input_count = sum(
                f">Input_Param{index}<" in native_text
                for index in range(device.input_bytes)
            )
            if (
                output_count != device.output_bytes
                or f">Output_Param{device.output_bytes}<" in native_text
            ):
                missing.append(
                    f"O->T size {device.output_bytes} for "
                    f"{device.device_variable}"
                )
            if (
                input_count != device.input_bytes
                or f">Input_Param{device.input_bytes}<" in native_text
            ):
                missing.append(
                    f"T->O size {device.input_bytes} for "
                    f"{device.device_variable}"
                )
        if missing:
            raise ValueError(
                "native CODESYS template is inconsistent with manifest: "
                + "; ".join(missing)
            )

    @staticmethod
    def _native_device(
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
                if CodesysPowerFlex525BundleExporter._native_value(
                    element,
                    "IP address of Target",
                ) is not None:
                    return element
                element = parents.get(element)
        return None

    @staticmethod
    def _native_value(
        root: ET.Element,
        visible_name: str,
    ) -> str | None:
        """Read a named CODESYS property from one native object."""

        for data in root.findall(".//Single"):
            name = data.find(
                "./Single[@Name='VisibleName']/Single[@Name='Default']"
            )
            value = data.find("./Single[@Name='Value']")
            if (
                name is not None
                and name.text == visible_name
                and value is not None
            ):
                return value.text
        return None

    @staticmethod
    def _instructions(
        manifest: CodesysPowerFlex525DeploymentManifest,
    ) -> str:
        rows = "\n".join(
            f"| `{item.name}` | `{item.device_variable}` | "
            f"`{item.ip_address}` | {item.rpi_ms} ms | "
            f"{item.output_bytes} | {item.input_bytes} |"
            for item in manifest.devices
        )
        if manifest.native_template_scope == "complete_project":
            workflow = """\
1. Create or open a compatible CODESYS project.
2. Select the top-level device and import `native-device-template.export`.
3. Treat that native export as the complete verified baseline: it already
   contains the application, scanner tasks, POUs, and device tree.
4. Build the imported baseline.
5. Use `application.xml` as the generated application reference. Do not import
   it on top of the baseline unless intentionally replacing its application
   POUs; doing so otherwise creates duplicates.
6. After an intentional replacement, retain the scanner tasks, set the
   original application active, save, run Clean All, and build.
"""
        else:
            workflow = """\
1. Create or open a compatible CODESYS project.
2. Select the top-level device and import `native-device-template.export`.
3. Confirm the EtherNet/IP scanner and every configured device below.
4. Select `PLC Logic` and import `application.xml`. CODESYS creates a separate
   application such as `Application_1`.
5. Move the imported POUs and `MainTask` into the original application while
   retaining its generated scanner tasks, then delete the empty imported
   application.
6. Set the original application active, save, run Clean All, and build.
"""
        workflow = workflow.strip()
        return f"""\
# CODESYS deployment bundle

This bundle combines target-specific native device configuration with a
generated PLCopen application. Native template scope:
`{manifest.native_template_scope}`.

{workflow}

| Instance | Native IEC object | Address | RPI | O->T bytes | T->O bytes |
| --- | --- | --- | ---: | ---: | ---: |
{rows}

The native `.export` file is CODESYS-specific. `application.xml` is PLCopen
XML with CODESYS profile extensions. Do not assume that either file configures
physical hardware safely; verify addresses, assemblies, mappings, and drive
parameters for the installation.
"""


def load_codesys_powerflex525_manifest(
    path: str | Path,
) -> CodesysPowerFlex525DeploymentManifest:
    """Load and validate one JSON deployment manifest."""

    source = Path(path)
    return CodesysPowerFlex525DeploymentManifest.model_validate_json(
        source.read_text(encoding="utf-8")
    )
