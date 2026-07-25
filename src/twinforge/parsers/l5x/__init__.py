"""
L5X parser package.
"""

from typing import TYPE_CHECKING, Any

from .capture import (
    CapturedSection,
    capture_section,
)

if TYPE_CHECKING:
    from .parser import L5XParser

__all__ = [
    "L5XParser",
    "CapturedSection",
    "capture_section",
]


def __getattr__(name: str) -> Any:
    if name == "L5XParser":
        from .parser import L5XParser

        return L5XParser
    raise AttributeError(name)
