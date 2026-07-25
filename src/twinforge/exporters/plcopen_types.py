"""Public types and target profiles for PLCopen XML export."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from twinforge.converters import ConversionDiagnostic


PLCOPEN_201_NAMESPACE = "http://www.plcopen.org/xml/tc6_0201"
PLCOPEN_CODESYS_NAMESPACE = "http://www.plcopen.org/xml/tc6_0200"


class PLCopenProfile(str, Enum):
    """Supported output dialects.

    The standard profile contains no target-vendor extensions. Target-specific
    profiles select a dedicated adapter; a future OpenPLC adapter can therefore
    be introduced without treating CODESYS conventions as generic PLCopen.
    """

    STANDARD_201 = "standard_201"
    CODESYS = "codesys"

    @property
    def namespace(self) -> str:
        """Return the namespace required by this target dialect."""

        if self is PLCopenProfile.CODESYS:
            return PLCOPEN_CODESYS_NAMESPACE
        return PLCOPEN_201_NAMESPACE


@dataclass
class PLCopenExportResult:
    """Serialized PLCopen XML and non-fatal conversion diagnostics."""

    xml: str
    diagnostics: list[ConversionDiagnostic] = field(default_factory=list)
