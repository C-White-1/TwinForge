"""Socket-free CLI demonstration of the Discovery Snapshot contract."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TextIO

from twinforge.discovery import (
    DiscoveryScope,
    DiscoveryTarget,
    FakeCipIdentity,
    FakeDiscoveryProvider,
    capture_snapshot,
    snapshot_json,
)


class FakeSnapshotCommandError(RuntimeError):
    """A stable, user-facing fake-snapshot command failure."""


def generate_fake_snapshot(
    *,
    engagement: str,
    authorization_reference: str,
    captured_at: str,
    destination: Path | None,
    stdout: TextIO,
) -> None:
    """Generate deterministic sanitized evidence without network activity."""
    try:
        timestamp = datetime.fromisoformat(captured_at)
        if timestamp.tzinfo is None:
            raise FakeSnapshotCommandError(
                "--captured-at must include a timezone offset"
            )
        target = DiscoveryTarget(
            address="192.0.2.10",
            label="sanitized-demo-controller",
        )
        scope = DiscoveryScope(
            engagement=engagement,
            authorization_reference=authorization_reference,
            targets=(target,),
        )
        provider = FakeDiscoveryProvider(
            {
                target.key: FakeCipIdentity(
                    vendor_id=1,
                    device_type=14,
                    product_code=166,
                    major_revision=35,
                    minor_revision=11,
                    status=0x0060,
                    serial_number=0x12345678,
                    product_name="Sanitized Controller",
                    state=3,
                    raw_payload_hex=(
                        "01000e00a600230b6000785634121453616e6974697a656420"
                        "436f6e74726f6c6c657203"
                    ),
                    raw_attributes={"fixture": True, "sanitized": True},
                )
            }
        )
        document = snapshot_json(
            capture_snapshot(scope, provider, captured_at=timestamp)
        )
    except ValueError as error:
        raise FakeSnapshotCommandError(str(error)) from error

    if destination is None:
        stdout.write(document)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    stdout.write(f"Wrote {destination}\n")
