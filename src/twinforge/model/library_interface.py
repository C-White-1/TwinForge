"""Library signature evidence, separate from executable block definitions."""
from dataclasses import dataclass, field

from .source_extension import SourceExtension


@dataclass
class LibraryParameter:
    name: str | None
    data_type: str | None
    direction: str
    comment: str | None = None


@dataclass
class LibraryInterface:
    name: str | None
    kind: str
    parameters: list[LibraryParameter] = field(default_factory=list)
    # Schneider's own first-party documentation text for this block, verbatim
    # from its `TypeDescriptiveForm` attribute (e.g. "The function block is
    # used as the On delay..."). An empty attribute value is treated the same
    # as an absent one -- both mean "not documented", not "documented as
    # blank".
    description: str | None = None
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
