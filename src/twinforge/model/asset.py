# model/asset.py

import uuid
from dataclasses import dataclass, field
from typing import Any

from .source_extension import SourceExtension


@dataclass
class Asset:
    """
    Base class for every object in the digital twin
    """

    name: str = field(default="", kw_only=True)

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    parent: Any | None = field(default=None, repr=False)

    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)

    def path(self) -> str:
        if self.parent is None:
            return self.name
        return f"{self.parent.path()}/{self.name}"
