"""Public AutomationML export types and shared CAEX constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


CAEX_NAMESPACE = "http://www.dke.de/CAEX"
AUTOMATIONML_VERSION = "2.1"
CAEX_SCHEMA_VERSION = "3.0"
AUTOMATIONML_BASE_ALIAS = "AutomationMLBaseLibraries"
TWINFORGE_INTERFACE_LIBRARY = "TwinForgeInterfaceClassLib"
TWINFORGE_ROLE_LIBRARY = "TwinForgeRoleClassLib"
TWINFORGE_ATTRIBUTE_LIBRARY = "TwinForgeAttributeTypeLib"
TWINFORGE_SYSTEM_UNIT_LIBRARY = "TwinForgeSystemUnitClassLib"
ROCKWELL_SYSTEM_UNIT_LIBRARY = "RockwellSystemUnitClassLib"

BASE_INTERFACE_PATH = (
    f"{AUTOMATIONML_BASE_ALIAS}@AutomationMLInterfaceClassLib/"
    "AutomationMLBaseInterface"
)
BASE_SIGNAL_PATH = f"{BASE_INTERFACE_PATH}/Communication/SignalInterface"
BASE_PLCOPEN_PATH = (
    f"{BASE_INTERFACE_PATH}/ExternalDataConnector/PLCopenXMLInterface"
)
BASE_RESOURCE_ROLE_PATH = (
    f"{AUTOMATIONML_BASE_ALIAS}@AutomationMLBaseRoleClassLib/"
    "AutomationMLBaseRole/Resource"
)
BASE_DIRECTION_TYPE_PATH = (
    f"{AUTOMATIONML_BASE_ALIAS}@AutomationMLBaseAttributeTypeLib/Direction"
)
BASE_REF_URI_TYPE_PATH = (
    f"{AUTOMATIONML_BASE_ALIAS}@AutomationMLBaseAttributeTypeLib/refURI"
)


@dataclass(frozen=True)
class AutomationMLExportResult:
    """Serialized CAEX and its optional output location."""

    xml: str
    destination: Path | None = None
