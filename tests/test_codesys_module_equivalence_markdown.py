from pathlib import Path

from twinforge.exporters import CodesysModuleEquivalenceMarkdownExporter


def test_equivalence_report_is_complete_and_deterministic():
    exporter = CodesysModuleEquivalenceMarkdownExporter()

    first = exporter.export()
    second = exporter.export()

    assert first == second
    assert first.count("\n| ") == 9
    assert "| `EntryStatus` |" in first
    assert "| Set inhibited " in first
    assert "| Hardware validation required |" in first
    assert "exactly equivalent" not in first


def test_architecture_document_contains_the_generated_table():
    document = (
        Path(__file__).parents[1]
        / "docs/architecture/codesys-ethernetip-module-adapter.md"
    ).read_text(encoding="utf-8")

    assert CodesysModuleEquivalenceMarkdownExporter().table() in document


def test_checked_in_equivalence_report_matches_the_exporter():
    report = (
        Path(__file__).parents[1]
        / "reports/Dev_PF525_Program/sys_module_codesys_equivalence.md"
    ).read_text(encoding="utf-8")

    assert report == CodesysModuleEquivalenceMarkdownExporter().export()
