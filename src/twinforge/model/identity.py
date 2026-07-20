from dataclasses import dataclass, field

from .revision import Revision
from .source_extension import SourceExtension


@dataclass(frozen=True)
class VendorIdentity:
    """A numeric vendor identity with an optional resolved display name."""

    id: int
    name: str | None = None

    def __str__(self) -> str:
        return self.name or str(self.id)


@dataclass
class Identity:
    vendor: VendorIdentity | None = None
    product_code: int | None = None
    product_type: int | None = None
    product_type_name: str | None = None
    product_name: str | None = None

    revision: Revision | None = None

    serial: str | None = None

    status: bytes | None = None

    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
