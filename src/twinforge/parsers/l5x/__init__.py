"""
L5X parser package.
"""

from typing import TYPE_CHECKING, Any

from .capture import (
    CapturedSection,
    capture_section,
)
from .document import L5XDocument, L5XTarget, L5XTargetType
if TYPE_CHECKING:
    from .corpus import (
        ControllerWorkspace,
        L5XCorpus,
        L5XCorpusDiagnostic,
        L5XCorpusParser,
        WorkspaceEvidence,
    )
    from .parser import L5XParser

__all__ = [
    "L5XParser",
    "CapturedSection",
    "capture_section",
    "L5XDocument",
    "L5XTarget",
    "L5XTargetType",
    "ControllerWorkspace",
    "L5XCorpus",
    "L5XCorpusDiagnostic",
    "L5XCorpusParser",
    "WorkspaceEvidence",
]


def __getattr__(name: str) -> Any:
    if name == "L5XParser":
        from .parser import L5XParser

        return L5XParser
    if name in {
        "ControllerWorkspace",
        "L5XCorpus",
        "L5XCorpusDiagnostic",
        "L5XCorpusParser",
        "WorkspaceEvidence",
    }:
        from . import corpus

        return getattr(corpus, name)
    raise AttributeError(name)
