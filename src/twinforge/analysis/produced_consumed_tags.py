"""Resolve explicit Logix produced/consumed tag relationships in a corpus."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from twinforge.model import Controller, Tag

if TYPE_CHECKING:
    from twinforge.parsers.l5x.corpus import ControllerWorkspace, L5XCorpus


@dataclass(frozen=True)
class ProducedConsumedTagRelationship:
    """One uniquely resolved producer-to-consumer tag relationship."""

    producer_workspace_key: str
    producer_controller: str
    produced_tag: Tag
    consumer_workspace_key: str
    consumer_controller: str
    consumed_tag: Tag
    requested_packet_interval_ms: float | None


@dataclass(frozen=True)
class UnresolvedConsumedTag:
    """Consumed-tag configuration that cannot be resolved uniquely."""

    consumer_workspace_key: str
    consumer_controller: str
    consumed_tag: Tag
    producer_name: str | None
    remote_tag: str | None
    remote_file: int | None
    reason: str


@dataclass(frozen=True)
class ProducedConsumedTagAnalysis:
    """Resolved relationships and retained unresolved consumed tags."""

    relationships: tuple[ProducedConsumedTagRelationship, ...]
    unresolved: tuple[UnresolvedConsumedTag, ...]


def analyze_produced_consumed_tags(
    corpus: L5XCorpus,
) -> ProducedConsumedTagAnalysis:
    """Resolve only exact controller and produced-tag evidence."""

    controllers = [
        (workspace, workspace.controller_document.target)
        for workspace in corpus.workspaces
        if workspace.controller_document is not None
        and isinstance(workspace.controller_document.target, Controller)
    ]
    by_name: dict[str, list[tuple[ControllerWorkspace, Controller]]] = {}
    for workspace, controller in controllers:
        by_name.setdefault(controller.name.casefold(), []).append(
            (workspace, controller)
        )
    relationships: list[ProducedConsumedTagRelationship] = []
    unresolved: list[UnresolvedConsumedTag] = []
    for consumer_workspace, consumer in controllers:
        for consumed_tag in consumer.iter_tags():
            configuration = consumed_tag.consumed_configuration
            if configuration is None:
                continue
            producer_matches = by_name.get(
                (configuration.producer or "").casefold(),
                [],
            )
            if len(producer_matches) != 1:
                unresolved.append(
                    _unresolved(
                        consumer_workspace.key,
                        consumer,
                        consumed_tag,
                        f"producer controller resolved to {len(producer_matches)} workspaces",
                    )
                )
                continue
            producer_workspace, producer = producer_matches[0]
            if configuration.remote_tag is None:
                unresolved.append(
                    _unresolved(
                        consumer_workspace.key,
                        consumer,
                        consumed_tag,
                        "RemoteTag is absent; RemoteFile relationships are retained only",
                    )
                )
                continue
            produced_matches = [
                tag
                for tag in producer.iter_tags()
                if tag.name.casefold() == configuration.remote_tag.casefold()
                and tag.produced_configuration is not None
            ]
            if len(produced_matches) != 1:
                unresolved.append(
                    _unresolved(
                        consumer_workspace.key,
                        consumer,
                        consumed_tag,
                        f"remote produced tag resolved to {len(produced_matches)} tags",
                    )
                )
                continue
            relationships.append(
                ProducedConsumedTagRelationship(
                    producer_workspace_key=producer_workspace.key,
                    producer_controller=producer.name,
                    produced_tag=produced_matches[0],
                    consumer_workspace_key=consumer_workspace.key,
                    consumer_controller=consumer.name,
                    consumed_tag=consumed_tag,
                    requested_packet_interval_ms=configuration.rpi,
                )
            )
    return ProducedConsumedTagAnalysis(
        relationships=tuple(relationships),
        unresolved=tuple(unresolved),
    )


def produced_consumed_tag_analysis_data(
    analysis: ProducedConsumedTagAnalysis,
) -> dict[str, Any]:
    """Return deterministic, JSON-compatible relationship evidence."""

    return {
        "schema_version": "1.0",
        "relationships": [
            {
                "producer_workspace_key": item.producer_workspace_key,
                "producer_controller": item.producer_controller,
                "produced_tag": item.produced_tag.name,
                "consumer_workspace_key": item.consumer_workspace_key,
                "consumer_controller": item.consumer_controller,
                "consumed_tag": item.consumed_tag.name,
                "requested_packet_interval_ms": (
                    item.requested_packet_interval_ms
                ),
                "evidence_class": "configured_intent",
            }
            for item in analysis.relationships
        ],
        "unresolved": [
            {
                "consumer_workspace_key": item.consumer_workspace_key,
                "consumer_controller": item.consumer_controller,
                "consumed_tag": item.consumed_tag.name,
                "producer_name": item.producer_name,
                "remote_tag": item.remote_tag,
                "remote_file": item.remote_file,
                "reason": item.reason,
            }
            for item in analysis.unresolved
        ],
    }


def produced_consumed_tag_analysis_json(
    analysis: ProducedConsumedTagAnalysis,
) -> str:
    """Serialize the versioned analysis with a final newline."""

    return json.dumps(
        produced_consumed_tag_analysis_data(analysis),
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def _unresolved(
    workspace_key: str,
    controller: Controller,
    tag: Tag,
    reason: str,
) -> UnresolvedConsumedTag:
    configuration = tag.consumed_configuration
    assert configuration is not None
    return UnresolvedConsumedTag(
        consumer_workspace_key=workspace_key,
        consumer_controller=controller.name,
        consumed_tag=tag,
        producer_name=configuration.producer,
        remote_tag=configuration.remote_tag,
        remote_file=configuration.remote_file,
        reason=reason,
    )
