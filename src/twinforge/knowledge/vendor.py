"""Canonical vendor display knowledge that preserves source spelling."""

from __future__ import annotations


def canonical_vendor_name(vendor_id: int | None, source_name: str | None) -> str | None:
    """Return a stable display name where vendor identity is authoritative.

    The caller must retain ``source_name`` separately. This function only
    supplies a normalized display value and never rewrites source evidence.
    """

    if vendor_id == 1:
        return "Allen-Bradley / Rockwell Automation"
    normalized = source_name.strip() if source_name is not None else ""
    return normalized or None
