import json
from pathlib import Path

from twinforge.analysis import (
    analyze_produced_consumed_tags,
    produced_consumed_tag_analysis_json,
)
from twinforge.parsers.l5x import L5XCorpusParser


def _controller(path: Path, name: str, tag_xml: str) -> None:
    path.write_text(
        f"""
<RSLogix5000Content TargetType="Controller" TargetName="{name}">
  <Controller Use="Target" Name="{name}"><Tags>{tag_xml}</Tags></Controller>
</RSLogix5000Content>
""",
        encoding="utf-8",
    )


def test_parses_and_resolves_exact_produced_consumed_relationship(tmp_path: Path):
    _controller(
        tmp_path / "producer.L5X",
        "ProducerPLC",
        """
<Tag Name="SharedData" TagType="Produced" DataType="DINT">
  <ProduceInfo ProduceCount="2" MinimumRPI="2.0" MaximumRPI="1000.0"
   DefaultRPI="20.0" ProgrammaticallySendEventTrigger="false"
   UnicastPermitted="true" FutureProducedField="retain" />
</Tag>
""",
    )
    _controller(
        tmp_path / "consumer.L5X",
        "ConsumerPLC",
        """
<Tag Name="RemoteData" TagType="Consumed" DataType="DINT">
  <ConsumeInfo Producer="ProducerPLC" RemoteTag="SharedData" RPI="25.0"
   ProgrammaticallySendEventTrigger="false" FutureConsumedField="retain" />
</Tag>
""",
    )

    analysis = analyze_produced_consumed_tags(
        L5XCorpusParser().parse_directory(tmp_path)
    )

    assert analysis.unresolved == ()
    assert len(analysis.relationships) == 1
    relationship = analysis.relationships[0]
    assert relationship.produced_tag.name == "SharedData"
    assert relationship.consumed_tag.name == "RemoteData"
    assert relationship.requested_packet_interval_ms == 25.0
    produced = relationship.produced_tag.produced_configuration
    consumed = relationship.consumed_tag.consumed_configuration
    assert produced is not None
    assert produced.produce_count == 2
    assert produced.unicast_permitted is True
    assert produced.raw_attributes["FutureProducedField"] == "retain"
    assert consumed is not None
    assert consumed.raw_attributes["FutureConsumedField"] == "retain"
    document = json.loads(produced_consumed_tag_analysis_json(analysis))
    assert document["schema_version"] == "1.0"
    assert document["relationships"][0]["evidence_class"] == (
        "configured_intent"
    )


def test_retains_unresolved_consumed_tag_when_producer_is_absent(tmp_path: Path):
    _controller(
        tmp_path / "consumer.L5X",
        "ConsumerPLC",
        """
<Tag Name="LegacyData" TagType="Consumed" DataType="DINT">
  <ConsumeInfo Producer="LegacyPLC" RemoteFile="7" RPI="50" />
</Tag>
<Tag Name="MissingData" TagType="Consumed" DataType="DINT">
  <ConsumeInfo Producer="MissingPLC" RemoteTag="SharedData" RPI="20" />
</Tag>
""",
    )

    analysis = analyze_produced_consumed_tags(
        L5XCorpusParser().parse_directory(tmp_path)
    )

    assert analysis.relationships == ()
    assert len(analysis.unresolved) == 2
    assert analysis.unresolved[0].remote_file == 7
    assert all("producer controller" in item.reason for item in analysis.unresolved)
