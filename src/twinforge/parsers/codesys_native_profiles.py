"""Verified profile-specific mappings for CODESYS native object archives."""

from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class CodesysNativeProfile:
    """Mappings verified for one exact CODESYS serialization profile."""

    name: str
    property_names: Mapping[str, str]
    evidence: str
    font_dpi: int | None = None


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
    font_dpi=96,
)

CODESYS_NATIVE_PROFILES: Mapping[str, CodesysNativeProfile] = (
    MappingProxyType({_SP22_PATCH_2.name: _SP22_PATCH_2})
)


def codesys_native_profile(name: str | None) -> CodesysNativeProfile | None:
    """Return an exact verified profile; never guess a compatible version."""
    if name is None:
        return None
    return CODESYS_NATIVE_PROFILES.get(name)


def codesys_font_points(
    serialized_size: int,
    profile: CodesysNativeProfile,
) -> float:
    """Convert a verified native pixel font size to typographic points."""

    if profile.font_dpi is None:
        raise ValueError(f"font DPI is not established for {profile.name}")
    return serialized_size * 72 / profile.font_dpi


def codesys_font_serialized_size(
    points: float,
    profile: CodesysNativeProfile,
) -> int:
    """Convert points using the verified CODESYS half-up pixel rounding."""

    if profile.font_dpi is None:
        raise ValueError(f"font DPI is not established for {profile.name}")
    return math.floor(points * profile.font_dpi / 72 + 0.5)
