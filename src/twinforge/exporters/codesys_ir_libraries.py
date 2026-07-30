"""Discover and serialize CODESYS libraries required by executable IR."""

from __future__ import annotations

from collections.abc import Callable, Iterable
import xml.etree.ElementTree as ET

from twinforge.ir import IRReusableUnit

from .plcopen_codesys import CODESYS_NAMESPACE
from .plcopen_types import PLCOPEN_CODESYS_NAMESPACE
from .plcopen_xml import qualified_name as q


ObjectIdProvider = Callable[[str], str]
ObjectIdAppender = Callable[[ET.Element, str], None]

_WALL_CLOCK_TYPES = frozenset({"SysTime", "SysTypes.RTS_IEC_RESULT"})
_WALL_CLOCK_LIBRARIES = (
    {
        "Name": "#SysTimeRtc",
        "Namespace": "SysTimeRtc",
        "DefaultResolution": "SysTimeRtc, * (System)",
    },
    {
        "Name": "SysTime, 3.5.17.0 (System)",
        "Namespace": "SysTime",
    },
    {
        "Name": "SysTypes2 Interfaces, * (System)",
        "Namespace": "SysTypes",
    },
)
_LIBRARY_DEFAULTS = {
    "HideWhenReferencedAsDependency": "false",
    "PublishSymbolsInContainer": "false",
    "SystemLibrary": "false",
    "LinkAllContent": "false",
}


class CodesysIRLibraryEmitter:
    """Keep library discovery, metadata, and project identity consistent."""

    def __init__(
        self,
        *,
        object_id: ObjectIdProvider,
        append_object_id: ObjectIdAppender,
    ) -> None:
        self._object_id = object_id
        self._append_object_id = append_object_id

    @staticmethod
    def required(units: Iterable[IRReusableUnit]) -> bool:
        """Return whether any unit requires the proven wall-clock libraries."""

        return any(
            variable.data_type in _WALL_CLOCK_TYPES
            for unit in units
            for variable in unit.variables
        )

    def emit(
        self,
        parent: ET.Element,
        units: Iterable[IRReusableUnit],
    ) -> bool:
        """Append required library metadata and return whether it was added."""

        if not self.required(units):
            return False
        ns = PLCOPEN_CODESYS_NAMESPACE
        data = ET.SubElement(
            parent,
            q(ns, "data"),
            {
                "name": f"{CODESYS_NAMESPACE}/libraries",
                "handleUnknown": "implementation",
            },
        )
        libraries = ET.SubElement(data, q(ns, "Libraries"))
        for definition in _WALL_CLOCK_LIBRARIES:
            ET.SubElement(
                libraries,
                q(ns, "Library"),
                {**definition, **_LIBRARY_DEFAULTS},
            )
        self._append_object_id(
            libraries,
            self.library_manager_object_id(),
        )
        return True

    def append_project_object(
        self,
        application: ET.Element,
        units: Iterable[IRReusableUnit],
    ) -> bool:
        """Append the Library Manager navigator object when required."""

        if not self.required(units):
            return False
        ET.SubElement(
            application,
            q(PLCOPEN_CODESYS_NAMESPACE, "Object"),
            {
                "Name": "Library Manager",
                "ObjectId": self.library_manager_object_id(),
            },
        )
        return True

    def library_manager_object_id(self) -> str:
        """Return the deterministic CODESYS Library Manager identity."""

        return self._object_id("Application/Library Manager")
