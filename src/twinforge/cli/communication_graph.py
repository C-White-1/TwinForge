"""Installed command adapter for multi-controller communication graphs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from twinforge.assembly import (
    ControllerCommunicationBinding,
    ControllerCommunicationGraphError,
    build_controller_communication_graph,
    controller_communication_graph_json,
)
from twinforge.parsers.l5x import L5XCorpusParser


class CommunicationGraphCommandError(RuntimeError):
    """Raised when communication graph input or output is invalid."""


def export_communication_graph(
    source: Path,
    destination: Path,
    *,
    bindings_source: Path | None,
    recursive: bool,
    stdout: TextIO,
) -> Path:
    """Build an evidence-only graph from an explicit L5X corpus directory."""

    try:
        if not source.is_dir():
            raise CommunicationGraphCommandError(
                f"L5X corpus directory does not exist: {source}"
            )
        bindings = (
            _load_bindings(bindings_source)
            if bindings_source is not None
            else ()
        )
        corpus = L5XCorpusParser().parse_directory(
            source,
            recursive=recursive,
        )
        graph = build_controller_communication_graph(corpus, bindings)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            controller_communication_graph_json(graph),
            encoding="utf-8",
        )
    except CommunicationGraphCommandError:
        raise
    except (
        ControllerCommunicationGraphError,
        json.JSONDecodeError,
        OSError,
        TypeError,
        ValueError,
    ) as error:
        raise CommunicationGraphCommandError(
            f"cannot generate controller communication graph: {error}"
        ) from error

    stdout.write(
        f"Exported controller communication graph to {destination}\n"
        f"- Controller workspaces: {len(graph.nodes)}\n"
        f"- Confirmed edges: {len(graph.edges)}\n"
        f"- Unbound messages: {len(graph.unbound_messages)}\n"
    )
    return destination


def _load_bindings(
    source: Path,
) -> tuple[ControllerCommunicationBinding, ...]:
    """Load the versioned explicit-binding contract without inference."""

    document = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("binding document must be a JSON object")
    if document.get("schema_version") != "1.0":
        raise ValueError("binding schema_version must be '1.0'")
    records = document.get("bindings")
    if not isinstance(records, list):
        raise ValueError("binding document 'bindings' must be an array")
    bindings: list[ControllerCommunicationBinding] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"binding {index} must be an object")
        evidence_key = record.get("evidence_key")
        target_key = record.get("target_workspace_key")
        if not isinstance(evidence_key, str) or not evidence_key.strip():
            raise ValueError(
                f"binding {index} evidence_key must be a non-empty string"
            )
        if not isinstance(target_key, str) or not target_key.strip():
            raise ValueError(
                "binding "
                f"{index} target_workspace_key must be a non-empty string"
            )
        bindings.append(
            ControllerCommunicationBinding(
                evidence_key=evidence_key,
                target_workspace_key=target_key,
            )
        )
    return tuple(bindings)
