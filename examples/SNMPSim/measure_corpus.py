"""Measure a local, explicitly sourced SNMP recording corpus."""

from __future__ import annotations

import argparse
from pathlib import Path

from twinforge.discovery import (
    load_snmp_corpus_manifest,
    measure_snmp_corpus,
    snmp_corpus_json,
    snmp_corpus_markdown,
)


def main() -> None:
    """Load a manifest and write its offline compatibility report."""
    parser = argparse.ArgumentParser(
        description="Measure local SNMP recordings without network access."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="markdown",
        dest="output_format",
    )
    parser.add_argument(
        "--max-recording-mib",
        type=int,
        default=16,
        help="Maximum decompressed size of each recording (default: 16 MiB)",
    )
    args = parser.parse_args()
    manifest = load_snmp_corpus_manifest(args.manifest)
    report = measure_snmp_corpus(
        manifest,
        args.manifest,
        max_recording_bytes=args.max_recording_mib * 1024 * 1024,
    )
    rendered = (
        snmp_corpus_json(report)
        if args.output_format == "json"
        else snmp_corpus_markdown(report)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Measured {len(report.results)} recordings: {args.output}")


if __name__ == "__main__":
    main()
