"""Provisional, sample-backed Machine Expert – Basic `.smbp` specifications."""

from .grammar import ENCRYPTED_PROJECT_SPEC, PROJECT_SPEC, SPECS, ElementSpec
from .mapping import BASIC_MAPPING, MappingSpec, SymbolTable

__all__ = [
    "PROJECT_SPEC", "ENCRYPTED_PROJECT_SPEC", "SPECS", "ElementSpec",
    "BASIC_MAPPING", "MappingSpec", "SymbolTable",
]
