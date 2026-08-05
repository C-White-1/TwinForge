"""Create a provenance manifest for an external SNMP recording directory."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.discovery import discover_snmp_corpus, snmp_corpus_manifest_json


def main() -> None:
    """Inventory recognized recordings without copying or opening them."""
    parser = argparse.ArgumentParser(
        description="Inventory an external SNMP corpus with SHA-256 checksums."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--license", required=True, dest="license_name")
    parser.add_argument("--sanitized", action="store_true")
    args = parser.parse_args()
    manifest = discover_snmp_corpus(
        args.source,
        source_url=args.source_url,
        license_name=args.license_name,
        sanitized=args.sanitized,
        path_base=args.output.resolve().parent,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(snmp_corpus_manifest_json(manifest), encoding="utf-8")
    print(f"Inventoried {len(manifest.entries)} recordings: {args.output}")


if __name__ == "__main__":
    main()
