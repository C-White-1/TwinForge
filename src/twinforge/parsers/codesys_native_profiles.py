"""Verified profile-specific mappings for CODESYS native object archives."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class CodesysNativeProfile:
    """Mappings verified for one exact CODESYS serialization profile."""

    name: str
    property_names: Mapping[str, str]
    evidence: str


_SP22_PATCH_2 = CodesysNativeProfile(
    name="CODESYS V3.5 SP22 Patch 2",
    property_names=MappingProxyType(
        {
            "1649127785": "x",
            "357335551": "y",
            "2422045748": "width",
            "2134141914": "height",
            "390574330": "text",
            "550940142": "center_x",
            "1473355128": "center_y",
            "2340015797": "horizontal_alignment",
            "3729828405": "font",
        }
    ),
    evidence=(
        "reports/Dev_PF525_Program/"
        "codesys_visualization_property_evidence.md"
    ),
)

CODESYS_NATIVE_PROFILES: Mapping[str, CodesysNativeProfile] = (
    MappingProxyType({_SP22_PATCH_2.name: _SP22_PATCH_2})
)


def codesys_native_profile(name: str | None) -> CodesysNativeProfile | None:
    """Return an exact verified profile; never guess a compatible version."""
    if name is None:
        return None
    return CODESYS_NATIVE_PROFILES.get(name)
