"""Build a validated, self-contained PowerFlex 525 CODESYS bundle."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.targets.codesys import (
    CodesysPowerFlex525BundleExporter,
    load_codesys_powerflex525_manifest,
)


def main() -> int:
    """Validate a JSON manifest and write its deployment bundle."""

    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    manifest = load_codesys_powerflex525_manifest(args.manifest)
    bundle = CodesysPowerFlex525BundleExporter().export(
        manifest,
        args.destination,
        manifest_directory=args.manifest.parent,
    )
    print(f"Wrote {bundle.directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
