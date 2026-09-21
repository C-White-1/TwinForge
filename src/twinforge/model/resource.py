"""A controller resource and the variables declared in its own namespace."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .source_extension import SourceExtension

if TYPE_CHECKING:
    from .tag import Tag


@dataclass
class Resource:
    """One processing resource (for example a process or safety CPU).

    Its variables are visible to the programs its tasks schedule, not to other
    resources: two resources may declare the same name independently, so they
    are never merged into the controller-wide tag list.
    """

    name: str = ""
    identifier: str | None = None
    tags: dict[str, Tag] = field(default_factory=dict)
    # Casefolded names declared more than once here; never bound to either declaration.
    ambiguous_names: set[str] = field(default_factory=set)
    task_names: list[str] = field(default_factory=list)
    parent: object | None = field(default=None, repr=False)
    metadata: dict = field(default_factory=dict)
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)

    def add_tag(self, tag: Tag) -> None:
        if tag.name in self.tags:
            raise ValueError(f"Tag '{tag.name}' already exists in resource '{self.name}'")
        tag.parent = self
        self.tags[tag.name] = tag
