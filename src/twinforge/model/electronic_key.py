from dataclasses import dataclass, field
from enum import Enum

from .identity import Identity
from .source_extension import SourceExtension


class KeyingMode(str, Enum):
    """Vendor-neutral electronic-key matching strategies."""

    COMPATIBLE_MODULE = "compatible_module"
    EXACT_MATCH = "exact_match"
    DISABLED = "disabled"
    CUSTOM = "custom"


@dataclass
class ElectronicKey:
    """Identity matching requirements applied when connecting to a device.

    ``unknown_mode`` preserves an unrecognized source-format value without
    forcing it into a known TwinForge keying strategy.
    """

    mode: KeyingMode | None = None
    identity: Identity | None = None
    unknown_mode: str | None = None
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)
