"""Deterministic identities for generated AutomationML objects."""

from __future__ import annotations

import uuid


AUTOMATIONML_ID_NAMESPACE = uuid.UUID(
    "88c16573-13ec-55cb-a5e4-18537fd58938"
)


def deterministic_id(kind: str, identity_path: str) -> uuid.UUID:
    """Return a stable UUID for an object kind and logical identity path."""

    return uuid.uuid5(
        AUTOMATIONML_ID_NAMESPACE,
        f"{kind}:{identity_path}",
    )
