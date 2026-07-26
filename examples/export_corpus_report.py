"""Generate a deterministic evidence report from a directory of L5X files."""

import argparse
from pathlib import Path

from twinforge.assembly import assemble_corpus_devices
from twinforge.exporters import CorpusMarkdownExporter
from twinforge.parsers.l5x import L5XCorpusParser


def main() -> None:
    """Parse one corpus boundary and write its evidence report."""

    parser = argparse.ArgumentParser(
        description="Export a multi-file L5X corpus evidence report."
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Directory containing the related L5X documents",
    )
    parser.add_argument(
        "destination",
        type=Path,
        help="Destination Markdown file",
    )
    parser.add_argument(
        "--title",
        default="L5X corpus evidence report",
        help="Report heading",
    )
    args = parser.parse_args()

    corpus = L5XCorpusParser().parse_directory(args.source)
    devices = assemble_corpus_devices(corpus)
    report = CorpusMarkdownExporter().export(
        corpus,
        devices=devices,
        title=args.title,
    )
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(report, encoding="utf-8")
    print(
        f"Exported {len(corpus.documents)} documents and "
        f"{len(devices)} assembled devices to {args.destination}"
    )


if __name__ == "__main__":
    main()
