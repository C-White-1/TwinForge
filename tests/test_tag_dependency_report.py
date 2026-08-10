import csv
from io import StringIO

from twinforge.analysis import (
    TagDependencyGraph,
    TagReference,
    TagReferenceAccess,
    UnresolvedTagReference,
)
from twinforge.exporters import (
    TagDependencyCSVExporter,
    TagDependencyMarkdownExporter,
)
from twinforge.model import SoftwareTagScope


def _graph() -> TagDependencyGraph:
    return TagDependencyGraph(
        references=(
            TagReference(
                tag_key="controller:Result",
                tag_name="Result",
                tag_scope=SoftwareTagScope.CONTROLLER,
                member_path=None,
                access=TagReferenceAccess.WRITE,
                instruction="OTE",
                argument_position=0,
                operand="Result",
                program_name="MainProgram",
                routine_name="MainRoutine",
                rung_number=4,
                line_number=None,
            ),
            TagReference(
                tag_key="controller:Result",
                tag_name="Result",
                tag_scope=SoftwareTagScope.CONTROLLER,
                member_path=".Value",
                access=TagReferenceAccess.ALIAS,
                instruction="ALIAS",
                argument_position=0,
                operand="Result.Value",
                program_name="<controller>",
                routine_name="<tag-definition>",
                rung_number=None,
                line_number=None,
                source_tag_key="controller:ResultAlias",
            ),
        ),
        unresolved_references=(
            UnresolvedTagReference(
                identifier="Local:1:I.Data.0",
                instruction="XIC",
                argument_position=0,
                operand="Local:1:I.Data.0",
                program_name="MainProgram",
                routine_name="MainRoutine",
                rung_number=4,
                line_number=None,
            ),
        ),
    )


def test_exports_dependency_report_as_markdown() -> None:
    result = TagDependencyMarkdownExporter().export(_graph())

    assert "- Resolved references: 2" in result
    assert "- Alias dependencies: 1" in result
    assert "| Result | controller | — | write |" in result
    assert "| Local:1:I.Data.0 | — | MainProgram |" in result


def test_exports_complete_dependency_evidence_as_csv() -> None:
    result = TagDependencyCSVExporter().export(_graph())
    rows = list(csv.DictReader(StringIO(result)))

    assert len(rows) == 3
    assert rows[0]["Status"] == "resolved"
    assert rows[0]["Access"] == "write"
    assert rows[1]["SourceTagKey"] == "controller:ResultAlias"
    assert rows[2]["Status"] == "unresolved"
    assert rows[2]["Identifier"] == "Local:1:I.Data.0"
