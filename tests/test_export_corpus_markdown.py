from pathlib import Path

from twinforge.assembly import assemble_corpus_devices
from twinforge.exporters import CorpusMarkdownExporter
from twinforge.exporters.corpus_markdown import (
    _append_evidence,
    _append_parameter_inventory,
    _append_parameter_semantics,
)
from twinforge.model import ObservedParameterAccess
from twinforge.knowledge.powerflex525_parameters import (
    PowerFlex525ParameterCatalogue,
)
from twinforge.parsers.l5x import L5XCorpusParser


DATA = Path(__file__).parent / "data/standalone"


def test_exports_deterministic_corpus_evidence_report():
    corpus = L5XCorpusParser().parse_directory(DATA)
    report = CorpusMarkdownExporter().export(
        corpus,
        devices=assemble_corpus_devices(corpus),
        title="Standalone evidence",
    )

    assert report.startswith("# Standalone evidence\n")
    assert "- Documents: 3" in report
    assert "| --- | --- | --- |" in report
    assert "|---" not in report
    assert "| Program | DriveProgram | program.L5X |" in report
    assert "`Dvc_PF525` in `DriveProgram.Main`" in report
    assert (
        "| Dvc | instance | — | unknown | Dvc | program | — | — |"
        in report
    )
    assert "No corpus diagnostics or unassigned documents." in report
    assert report == CorpusMarkdownExporter().export(
        corpus,
        devices=(),
        title="Standalone evidence",
    )


def test_appends_normalized_parameter_inventory():
    lines: list[str] = []
    _append_parameter_inventory(
        lines,
        [
            ObservedParameterAccess(
                number=38,
                code="P038",
                group_prefix="P",
                group_name="Basic Program",
                display_name="VoltageClass",
                reference=(
                    "Rockwell Automation 520-UM001, "
                    "PowerFlex 520-Series AC Drive User Manual"
                ),
                definition=PowerFlex525ParameterCatalogue().definition(38),
                observed_read=True,
                read_buffer_indices=(0,),
            ),
            ObservedParameterAccess(number=34, observed_write=True),
        ],
    )
    report = "\n".join(lines)

    assert "| ---: | --- | --- | --- | :---: | :---: | --- |" in report
    assert "|---" not in report
    assert "- Parameter groups: Basic Program (1), Unclassified (1)" in report
    assert (
        "- Parameter references: Rockwell Automation 520-UM001, "
        "PowerFlex 520-Series AC Drive User Manual"
        in report
    )
    assert (
        "| 38 | P038 | VoltageClass | Basic Program | yes | no | 0 |"
        in report
    )
    assert "Curated parameter semantics:" in report
    assert (
        "| P038 | Sets the voltage class of 600 V drives. "
        "| 2 = Low Voltage (480 V); 3 = High Voltage (600 V) "
        "| — | 3 | — | Read/write | yes |"
        in report
    )


def test_appends_evidence_with_blank_lines_around_list():
    lines = ["Previous content"]

    _append_evidence(lines, ("First item", "Second item"))

    assert "\n".join(lines) == (
        "Previous content\n\nEvidence:\n\n- First item\n- Second item"
    )


def test_appends_evidence_without_duplicating_existing_blank_line():
    lines = ["Previous content", ""]

    _append_evidence(lines, ("First item",))

    assert "\n".join(lines) == (
        "Previous content\n\nEvidence:\n\n- First item"
    )


def test_renders_a_shared_parameter_option_set_once():
    catalogue = PowerFlex525ParameterCatalogue()
    first = catalogue.definition(46)
    second = catalogue.definition(48)
    assert first is not None
    assert second is not None
    lines: list[str] = []

    _append_parameter_semantics(
        lines,
        [
            ObservedParameterAccess(number=46, definition=first),
            ObservedParameterAccess(number=48, definition=second),
        ],
    )
    report = "\n".join(lines)

    assert report.count("#### Start Source") == 1
    assert report.count("| 5 | EtherNet/IP |") == 1
    assert report.count("See option set: Start Source") == 2
