"""Legacy API example for the localhost-only cpppo identity laboratory.

Prefer the public ``twinforge discover identity`` command documented in the
laboratory procedure. This example remains useful when developing the Python
API directly.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.discovery import (
    DiscoveryOperation,
    DiscoveryScope,
    DiscoveryTarget,
    Pycomm3CipIdentityProvider,
    capture_snapshot,
    snapshot_json,
)


LAB_ADDRESS = "127.0.0.1"


def main() -> int:
    """Require explicit execution consent, then make one bounded request."""
    parser = argparse.ArgumentParser(
        description="Capture one CIP identity from the local cpppo laboratory.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="confirm the single live request to 127.0.0.1",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="optional path for the resulting Discovery Snapshot JSON",
    )
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required; no network request was made")

    target = DiscoveryTarget(address=LAB_ADDRESS, label="cpppo identity lab")
    scope = DiscoveryScope(
        engagement="TwinForge localhost cpppo identity laboratory",
        authorization_reference="operator --execute confirmation",
        targets=(target,),
        operations=(DiscoveryOperation.CIP_IDENTITY,),
    )
    provider = Pycomm3CipIdentityProvider((target,), timeout=2.0)
    document = snapshot_json(capture_snapshot(scope, provider))
    if args.output is None:
        print(document, end="")
    else:
        args.output.write_text(document, encoding="utf-8")
        print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
