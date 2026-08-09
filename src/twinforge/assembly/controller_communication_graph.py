"""Evidence-backed configured communication graph for L5X controller corpora."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from twinforge.model import Controller, Program, Tag
from twinforge.parsers.l5x.corpus import L5XCorpus
from twinforge.parsers.l5x.document import L5XTargetType


@dataclass(frozen=True)
class ConfiguredMessageEvidence:
    """One MESSAGE tag retained as configured intent, not observed traffic."""

    key: str
    source_workspace_key: str
    source_path: str
    owner: str
    tag_name: str
    message_type: str | None
    connection_path: str | None
    destination_tag: str | None


@dataclass(frozen=True)
class ControllerCommunicationBinding:
    """Explicit mapping from exact message evidence to a target workspace."""

    evidence_key: str
    target_workspace_key: str


@dataclass(frozen=True)
class ControllerCommunicationNode:
    """Controller workspace represented in the communication graph."""

    key: str
    controller_name: str
    confirmed: bool


@dataclass(frozen=True)
class ControllerCommunicationEdge:
    """Directed configured communication intent with retained source evidence."""

    source_workspace_key: str
    target_workspace_key: str
    evidence: tuple[ConfiguredMessageEvidence, ...]


@dataclass(frozen=True)
class ControllerCommunicationGraph:
    """Resolved configured edges plus messages still requiring a binding."""

    nodes: tuple[ControllerCommunicationNode, ...]
    edges: tuple[ControllerCommunicationEdge, ...]
    unbound_messages: tuple[ConfiguredMessageEvidence, ...]


class ControllerCommunicationGraphError(ValueError):
    """An explicit graph binding is invalid or ambiguous."""


def _message_key(
    workspace_key: str,
    source_path: Path,
    owner: str,
    tag_name: str,
) -> str:
    return f"{workspace_key}|{source_path}|{owner}|tag:{tag_name}"


def _message(
    workspace_key: str,
    source_path: Path,
    owner: str,
    tag: Tag,
) -> ConfiguredMessageEvidence:
    configuration = tag.message_configuration
    assert configuration is not None
    return ConfiguredMessageEvidence(
        key=_message_key(workspace_key, source_path, owner, tag.name),
        source_workspace_key=workspace_key,
        source_path=str(source_path),
        owner=owner,
        tag_name=tag.name,
        message_type=configuration.message_type,
        connection_path=configuration.connection_path,
        destination_tag=configuration.destination_tag,
    )


def _workspace_messages(corpus: L5XCorpus) -> tuple[ConfiguredMessageEvidence, ...]:
    evidence: list[ConfiguredMessageEvidence] = []
    for workspace in corpus.workspaces:
        for document in workspace.documents:
            target = document.target
            if document.target_type is L5XTargetType.CONTROLLER and isinstance(
                target, Controller
            ):
                evidence.extend(
                    _message(workspace.key, document.source_path, "controller", tag)
                    for tag in target.iter_tags()
                    if tag.message_configuration is not None
                )
                evidence.extend(
                    _message(
                        workspace.key,
                        document.source_path,
                        f"program:{program.name}",
                        tag,
                    )
                    for program in target.iter_programs()
                    for tag in program.iter_tags()
                    if tag.message_configuration is not None
                )
            elif document.target_type is L5XTargetType.PROGRAM and isinstance(
                target, Program
            ):
                evidence.extend(
                    _message(
                        workspace.key,
                        document.source_path,
                        f"program:{target.name}",
                        tag,
                    )
                    for tag in target.iter_tags()
                    if tag.message_configuration is not None
                )
    ordered = tuple(sorted(evidence, key=lambda item: item.key))
    if len({item.key for item in ordered}) != len(ordered):
        raise ControllerCommunicationGraphError(
            "configured message evidence keys must be unique"
        )
    return ordered


def build_controller_communication_graph(
    corpus: L5XCorpus,
    bindings: tuple[ControllerCommunicationBinding, ...],
) -> ControllerCommunicationGraph:
    """Build only explicitly bound configured communication relationships."""
    nodes = tuple(
        sorted(
            (
                ControllerCommunicationNode(
                    key=workspace.key,
                    controller_name=workspace.controller_name,
                    confirmed=workspace.confirmed,
                )
                for workspace in corpus.workspaces
            ),
            key=lambda item: item.key,
        )
    )
    node_keys = {item.key for item in nodes}
    messages = _workspace_messages(corpus)
    by_key = {item.key: item for item in messages}
    bound: dict[str, ControllerCommunicationBinding] = {}
    grouped: dict[tuple[str, str], list[ConfiguredMessageEvidence]] = {}
    for binding in bindings:
        if binding.evidence_key in bound:
            raise ControllerCommunicationGraphError(
                f"duplicate binding for evidence {binding.evidence_key!r}"
            )
        evidence = by_key.get(binding.evidence_key)
        if evidence is None:
            raise ControllerCommunicationGraphError(
                f"unknown message evidence key {binding.evidence_key!r}"
            )
        if binding.target_workspace_key not in node_keys:
            raise ControllerCommunicationGraphError(
                f"unknown target workspace {binding.target_workspace_key!r}"
            )
        bound[binding.evidence_key] = binding
        grouped.setdefault(
            (evidence.source_workspace_key, binding.target_workspace_key), []
        ).append(evidence)

    edges = tuple(
        ControllerCommunicationEdge(
            source_workspace_key=source,
            target_workspace_key=target,
            evidence=tuple(sorted(items, key=lambda item: item.key)),
        )
        for (source, target), items in sorted(grouped.items())
    )
    return ControllerCommunicationGraph(
        nodes=nodes,
        edges=edges,
        unbound_messages=tuple(
            item for item in messages if item.key not in bound
        ),
    )


def controller_communication_graph_data(
    graph: ControllerCommunicationGraph,
) -> dict[str, Any]:
    """Return deterministic, JSON-compatible graph evidence."""
    def message(item: ConfiguredMessageEvidence) -> dict[str, Any]:
        return {
            "key": item.key,
            "source_workspace_key": item.source_workspace_key,
            "source_path": item.source_path,
            "owner": item.owner,
            "tag_name": item.tag_name,
            "message_type": item.message_type,
            "connection_path": item.connection_path,
            "destination_tag": item.destination_tag,
        }

    return {
        "nodes": [item.__dict__ for item in graph.nodes],
        "edges": [
            {
                "source_workspace_key": item.source_workspace_key,
                "target_workspace_key": item.target_workspace_key,
                "evidence": [message(evidence) for evidence in item.evidence],
            }
            for item in graph.edges
        ],
        "unbound_messages": [message(item) for item in graph.unbound_messages],
    }


def controller_communication_graph_json(
    graph: ControllerCommunicationGraph,
) -> str:
    """Serialize the configured communication graph deterministically."""
    return json.dumps(
        controller_communication_graph_data(graph), indent=2, ensure_ascii=False
    ) + "\n"
