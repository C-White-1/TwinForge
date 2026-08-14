"""Validated CODESYS deployment manifests and reproducible bundle export."""

from __future__ import annotations

from ipaddress import IPv4Address
from pathlib import Path
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from twinforge.exporters.codesys_plcopen_ir import CodesysIRPLCopenExporter
from twinforge.exporters.codesys_sys_module_iec import (
    build_codesys_sys_module_binding_unit,
)
from twinforge.exporters.powerflex525_core import build_powerflex525_iec_unit

from .powerflex525 import (
    PowerFlex525CodesysDevice,
    powerflex525_codesys_multi_application_integration,
)
from .ethernetip_manifest import CodesysEtherNetIPConnectionManifest
from .deployment_bundle import (
    CodesysDeploymentBundle,
    CodesysDeploymentBundlePackager,
)
from .powerflex525_native_evidence import (
    PowerFlex525NativeDeviceExpectation,
    PowerFlex525NativeEvidenceValidator,
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


class CodesysPowerFlex525DeviceManifest(CodesysEtherNetIPConnectionManifest):
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
        PowerFlex525NativeEvidenceValidator().validate(
            native_source,
            template_scope=manifest.native_template_scope,
            devices=tuple(
                PowerFlex525NativeDeviceExpectation(
                    device_variable=item.device_variable,
                    ip_address=item.ip_address,
                    rpi_ms=item.rpi_ms,
                    output_bytes=item.output_bytes,
                    input_bytes=item.input_bytes,
                    connection_path=item.connection_path,
                )
                for item in manifest.devices
            ),
        )

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

        payload = manifest.model_dump(mode="json")
        return CodesysDeploymentBundlePackager().package(
            directory,
            manifest_payload=payload,
            application_xml=result.xml,
            native_template_source=native_source,
            instructions_markdown=self._instructions(manifest),
        )

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
