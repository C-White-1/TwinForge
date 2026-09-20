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
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
