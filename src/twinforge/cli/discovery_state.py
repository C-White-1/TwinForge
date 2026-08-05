"""Command handlers for persisted discovery lifecycle state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from twinforge.discovery import (
    CorePromotionResult,
    DiscoveryStateFileStore,
    DiscoveryStatePersistenceError,
    IdentityLifecycleState,
    PersistedDiscoveryState,
    STATE_SCHEMA_VERSION,
)


def _require_file(path: Path) -> None:
    if not path.is_file():
        raise DiscoveryStatePersistenceError(
            f"discovery state file does not exist: {path}"
        )


def state_summary_data(state: PersistedDiscoveryState) -> dict[str, object]:
    """Return a stable, non-sensitive summary of persisted state."""
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "revision": state.revision,
        "active_identity_keys": list(state.lifecycle.active_identity_keys),
        "inactive_identity_keys": list(
            state.lifecycle.inactive_identity_keys
        ),
        "generation_count": len(state.lifecycle.generations),
        "event_count": len(state.lifecycle.events),
        "promotion_count": len(state.promotions.records),
        "promoted_asset_ids": sorted(
            item.core_asset.id for item in state.promotions.records
        ),
        "unpromoted_identity_keys": list(
            state.promotions.unpromoted_identity_keys
        ),
    }


def inspect_state(path: Path, *, output_format: str, stdout: TextIO) -> None:
    """Validate and display a deterministic discovery-state summary."""
    _require_file(path)
    state = DiscoveryStateFileStore(path).load()
    summary = state_summary_data(state)
    promoted_asset_ids = sorted(
        item.core_asset.id for item in state.promotions.records
    )
    if output_format == "json":
        stdout.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
        return
    stdout.write(f"Schema version: {summary['schema_version']}\n")
    stdout.write(f"Revision: {summary['revision']}\n")
    stdout.write(f"Active identities: {len(state.lifecycle.active_identity_keys)}\n")
    stdout.write(
        f"Inactive identities: {len(state.lifecycle.inactive_identity_keys)}\n"
    )
    stdout.write(f"Generations: {summary['generation_count']}\n")
    stdout.write(f"Lifecycle events: {summary['event_count']}\n")
    stdout.write(f"Promotions: {summary['promotion_count']}\n")
    stdout.write(
        "Promoted asset IDs: "
        + (", ".join(promoted_asset_ids) or "-")
        + "\n"
    )


def validate_state(path: Path, *, stdout: TextIO) -> None:
    """Validate one state document and report its schema and revision."""
    _require_file(path)
    state = DiscoveryStateFileStore(path).load()
    stdout.write(
        f"Valid TwinForge discovery state "
        f"{STATE_SCHEMA_VERSION}, revision {state.revision}.\n"
    )


def initialise_state(path: Path, *, stdout: TextIO) -> None:
    """Create a new empty revision-one state without overwriting a file."""
    if path.exists():
        raise DiscoveryStatePersistenceError(
            f"refusing to overwrite existing path: {path}"
        )
    state = DiscoveryStateFileStore(path).save(
        IdentityLifecycleState(),
        CorePromotionResult(records=(), unpromoted_identity_keys=()),
        expected_revision=0,
    )
    stdout.write(
        f"Created TwinForge discovery state {path} at revision "
        f"{state.revision}.\n"
    )
