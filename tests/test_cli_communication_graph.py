import json
from io import StringIO
from pathlib import Path

from twinforge.cli import main


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


def _corpus(tmp_path: Path) -> Path:
    source = tmp_path / "corpus"
    source.mkdir()
    _controller(source / "PLC_A.L5X", "PLC_A", message=True)
    _controller(source / "PLC_B.L5X", "PLC_B")
    return source


def test_inventory_then_explicitly_bind_controller_message(tmp_path: Path) -> None:
    source = _corpus(tmp_path)
    inventory = tmp_path / "inventory.json"
    output = StringIO()

    result = main(
        (
            "communication",
            "graph",
            str(source),
            "--output",
            str(inventory),
        ),
        stdout=output,
    )

    assert result == 0
    data = json.loads(inventory.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0"
    assert data["edges"] == []
    assert len(data["nodes"]) == 2
    assert len(data["unbound_messages"]) == 1
    assert "Unbound messages: 1" in output.getvalue()

    target = next(
        node for node in data["nodes"] if node["controller_name"] == "PLC_B"
    )
    bindings = tmp_path / "bindings.json"
    bindings.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "bindings": [
                    {
                        "evidence_key": data["unbound_messages"][0]["key"],
                        "target_workspace_key": target["key"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    graph = tmp_path / "graph.json"

    result = main(
        (
            "communication",
            "graph",
            str(source),
            "--output",
            str(graph),
            "--bindings",
            str(bindings),
        )
    )

    assert result == 0
    bound = json.loads(graph.read_text(encoding="utf-8"))
    assert len(bound["edges"]) == 1
    assert bound["edges"][0]["target_workspace_key"] == target["key"]
    assert bound["unbound_messages"] == []


def test_rejects_invalid_binding_contract_without_writing(tmp_path: Path) -> None:
    source = _corpus(tmp_path)
    bindings = tmp_path / "bindings.json"
    bindings.write_text(
        '{"schema_version":"2.0","bindings":[]}',
        encoding="utf-8",
    )
    destination = tmp_path / "graph.json"
    errors = StringIO()

    result = main(
        (
            "communication",
            "graph",
            str(source),
            "--output",
            str(destination),
            "--bindings",
            str(bindings),
        ),
        stderr=errors,
    )

    assert result == 1
    assert "schema_version must be '1.0'" in errors.getvalue()
    assert not destination.exists()
