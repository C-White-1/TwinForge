from pathlib import Path

import pytest

from twinforge.assembly import (
    ControllerCommunicationBinding,
    ControllerCommunicationGraphError,
    build_controller_communication_graph,
    controller_communication_graph_json,
)
from twinforge.parsers.l5x import L5XCorpusParser


def _controller(path: Path, name: str, *, message: bool = False) -> None:
    tag = (
        """
        <Tag Name="ReadRemote" TagType="Base" DataType="MESSAGE">
          <Data Format="Message">
            <MessageParameters MessageType="CIP Data Table Read"
             ConnectionPath="RemoteController"
             DestinationTag="RemoteValue"/>
          </Data>
        </Tag>
        """
        if message
        else ""
    )
    path.write_text(
        f"""
        <RSLogix5000Content TargetType="Controller" TargetName="{name}">
          <Controller Use="Target" Name="{name}">
            <Tags>{tag}</Tags>
          </Controller>
        </RSLogix5000Content>
        """,
        encoding="utf-8",
    )


def _corpus(tmp_path: Path):
    first = tmp_path / "PLC_A.L5X"
    second = tmp_path / "PLC_B.L5X"
    _controller(first, "PLC_A", message=True)
    _controller(second, "PLC_B")
    return L5XCorpusParser().parse_files((first, second))


def test_unbound_message_is_retained_without_inferred_edge(tmp_path) -> None:
    graph = build_controller_communication_graph(_corpus(tmp_path), ())

    assert len(graph.nodes) == 2
    assert graph.edges == ()
    assert graph.unbound_messages[0].connection_path == "RemoteController"


def test_explicit_message_binding_creates_evidence_backed_edge(tmp_path) -> None:
    corpus = _corpus(tmp_path)
    unbound = build_controller_communication_graph(corpus, ())
    target = next(item for item in corpus.workspaces if item.controller_name == "PLC_B")

    graph = build_controller_communication_graph(
        corpus,
        (
            ControllerCommunicationBinding(
                evidence_key=unbound.unbound_messages[0].key,
                target_workspace_key=target.key,
            ),
        ),
    )

    assert len(graph.edges) == 1
    assert graph.edges[0].target_workspace_key == target.key
    assert graph.edges[0].evidence[0].tag_name == "ReadRemote"
    assert graph.unbound_messages == ()
    assert "CIP Data Table Read" in controller_communication_graph_json(graph)


def test_unknown_target_workspace_is_rejected(tmp_path) -> None:
    corpus = _corpus(tmp_path)
    evidence = build_controller_communication_graph(corpus, ()).unbound_messages[0]

    with pytest.raises(ControllerCommunicationGraphError, match="unknown target"):
        build_controller_communication_graph(
            corpus,
            (
                ControllerCommunicationBinding(
                    evidence_key=evidence.key,
                    target_workspace_key="controller:missing",
                ),
            ),
        )


def test_duplicate_binding_is_rejected(tmp_path) -> None:
    corpus = _corpus(tmp_path)
    initial = build_controller_communication_graph(corpus, ())
    target = next(item for item in corpus.workspaces if item.controller_name == "PLC_B")
    binding = ControllerCommunicationBinding(
        evidence_key=initial.unbound_messages[0].key,
        target_workspace_key=target.key,
    )

    with pytest.raises(ControllerCommunicationGraphError, match="duplicate binding"):
        build_controller_communication_graph(corpus, (binding, binding))
