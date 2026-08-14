"""Generic file packaging for reproducible CODESYS deployment bundles."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
from typing import Any


@dataclass(frozen=True)
class CodesysDeploymentBundle:
    """Files written for one self-contained CODESYS deployment bundle."""

    directory: Path
    manifest: Path
    application: Path
    native_template: Path
    instructions: Path


class CodesysDeploymentBundlePackager:
    """Write profile-independent CODESYS bundle files deterministically."""

    def package(
        self,
        destination: str | Path,
        *,
        manifest_payload: dict[str, Any],
        application_xml: str,
        native_template_source: str | Path,
        instructions_markdown: str,
    ) -> CodesysDeploymentBundle:
        """Write supplied, already-validated artifacts using stable names."""
        directory = Path(destination)
        directory.mkdir(parents=True, exist_ok=True)
        native_source = Path(native_template_source)
        if not native_source.is_file():
            raise FileNotFoundError(
                f"native CODESYS template does not exist: {native_source}"
            )

        application = directory / "application.xml"
        application.write_text(application_xml, encoding="utf-8")
        native_template = directory / "native-device-template.export"
        shutil.copyfile(native_source, native_template)
        manifest = directory / "manifest.json"
        normalized_payload = dict(manifest_payload)
        normalized_payload["native_template"] = native_template.name
        manifest.write_text(
            json.dumps(normalized_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        instructions = directory / "IMPORT.md"
        instructions.write_text(instructions_markdown, encoding="utf-8")
        return CodesysDeploymentBundle(
            directory=directory,
            manifest=manifest,
            application=application,
            native_template=native_template,
            instructions=instructions,
        )
