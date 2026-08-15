"""CLI planning and explicit execution for bounded CIP Identity capture."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

from twinforge.discovery import (
    DiscoveryOperation,
    DiscoveryProviderError,
    DiscoveryScope,
    DiscoveryTarget,
    Pycomm3CipIdentityProvider,
    capture_snapshot,
    cip_identity_plan_json,
    plan_cip_identity_capture,
    snapshot_json,
)


class CipIdentityCommandError(RuntimeError):
    """A safe, user-facing CIP Identity command failure."""


def discover_cip_identity(
    address: str,
    *,
    engagement: str,
    authorization_reference: str,
    timeout: float,
    execute: bool,
    destination: Path | None,
    stdout: TextIO,
) -> None:
    """Write a dry-run plan or make one explicitly confirmed identity read."""
    try:
        target = DiscoveryTarget(address=address)
        scope = DiscoveryScope(
            engagement=engagement,
            authorization_reference=authorization_reference,
            targets=(target,),
            operations=(DiscoveryOperation.CIP_IDENTITY,),
        )
        plan = plan_cip_identity_capture(scope, timeout=timeout)
        if not execute:
            _write_output(cip_identity_plan_json(plan), destination, stdout)
            return
        provider = Pycomm3CipIdentityProvider((target,), timeout=timeout)
        snapshot = capture_snapshot(scope, provider)
        _write_output(snapshot_json(snapshot), destination, stdout)
    except (DiscoveryProviderError, ValueError) as error:
        raise CipIdentityCommandError(str(error)) from error


def _write_output(document: str, destination: Path | None, stdout: TextIO) -> None:
    if destination is None:
        stdout.write(document)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    stdout.write(f"Wrote {destination}\n")
