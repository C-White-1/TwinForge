"""OpenPLC export foundation backed by standard PLCopen XML 2.01."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

from twinforge.exporters.plcopen import PLCopenExporter
from twinforge.exporters.plcopen_types import (
    PLCopenExportResult,
    PLCopenProfile,
)
from twinforge.model import Controller


class OpenPLCExporter:
    """Emit standard PLCopen XML for native OpenPLC evaluation.

    No unverified OpenPLC extensions are added. Native import compatibility
    remains a separate evidence milestone.
    """

    def __init__(self) -> None:
        self._plcopen = PLCopenExporter(PLCopenProfile.STANDARD_201)

    def build(
        self,
        controller: Controller,
        *,
        project_name: str | None = None,
        creation_time: datetime | None = None,
    ) -> ET.Element:
        """Build a standard PLCopen 2.01 document."""

        return self._plcopen.build(
            controller,
            project_name=project_name,
            creation_time=creation_time,
        )

    def export(
        self,
        controller: Controller,
        *,
        destination: str | Path | None = None,
        project_name: str | None = None,
        creation_time: datetime | None = None,
    ) -> PLCopenExportResult:
        """Serialize standard PLCopen XML without CODESYS extensions."""

        return self._plcopen.export(
            controller,
            destination=destination,
            project_name=project_name,
            creation_time=creation_time,
        )
