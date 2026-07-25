"""Importers and file parsers."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .l5x.parser import L5XParser

__all__ = [
    "L5XParser",
]


def __getattr__(name: str) -> Any:
    if name == "L5XParser":
        from .l5x.parser import L5XParser

        return L5XParser
    raise AttributeError(name)
