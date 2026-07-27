"""Importers and file parsers."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .codesys_native import CodesysNativeExportParser
    from .codesys_native_profiles import CodesysNativeProfile
    from .l5x.parser import L5XParser

__all__ = [
    "L5XParser",
    "CodesysNativeExportParser",
    "CodesysNativeProfile",
]


def __getattr__(name: str) -> Any:
    if name == "CodesysNativeExportParser":
        from .codesys_native import CodesysNativeExportParser

        return CodesysNativeExportParser
    if name == "CodesysNativeProfile":
        from .codesys_native_profiles import CodesysNativeProfile

        return CodesysNativeProfile
    if name == "L5XParser":
        from .l5x.parser import L5XParser

        return L5XParser
    raise AttributeError(name)
