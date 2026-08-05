import hashlib
import json
import bz2
from pathlib import Path

from twinforge.discovery import (
    SnmpCorpusEntry,
    SnmpCorpusManifest,
    aggregate_snmp_oid_families,
    discover_snmp_corpus,
    measure_snmp_corpus,
    snmp_corpus_json,
    snmp_corpus_markdown,
    read_snmprec_recording,
)


FIXTURE = (
    Path(__file__).parents[1]
    / "examples"
    / "SNMPSim"
    / "data"
    / "twinforge-switch.snmprec"
)


def entry(path: str, **changes: object) -> SnmpCorpusEntry:
    values: dict[str, object] = {
        "identifier": "switch",
        "path": path,
        "source_url": "https://example.invalid/source",
        "license": "BSD-2-Clause",
        "device_category": "switch",
        "sanitized": True,
    }
    values.update(changes)
    return SnmpCorpusEntry.model_validate(values)


def test_measures_checked_in_snmprec_and_renders_stably(tmp_path: Path):
    manifest_path = tmp_path / "corpus.json"
    relative = Path("fixture.snmprec")
    fixture = tmp_path / relative
    fixture.write_bytes(FIXTURE.read_bytes())
    checksum = hashlib.sha256(fixture.read_bytes()).hexdigest()
    manifest = SnmpCorpusManifest(entries=(entry(str(relative), sha256=checksum),))

    report = measure_snmp_corpus(manifest, manifest_path)

    assert report.results[0].status == "measured"
    assert report.results[0].interfaces == 3
    assert report.results[0].addresses == 1
    assert report.results[0].neighbours == 1
    assert report.results[0].forwarding_entries == 2
    assert report.results[0].physical_entities == 0
    assert json.loads(snmp_corpus_json(report))["results"][0]["oid_count"] > 0
    assert "| switch | measured | snmprec |" in snmp_corpus_markdown(report)
    assert aggregate_snmp_oid_families(report)["mib-2.system"] == 6
    assert "| `mib-2.system` | 6 | Yes |" in snmp_corpus_markdown(report)


def test_reports_missing_unsupported_and_checksum_evidence(tmp_path: Path):
    walk = tmp_path / "sample.dump"
    walk.write_text("SNMPv2-MIB::sysName.0 = STRING: demo\n", encoding="utf-8")
    fixture = tmp_path / "fixture.snmprec"
    fixture.write_bytes(FIXTURE.read_bytes())
    manifest = SnmpCorpusManifest(
        entries=(
            entry("missing.snmprec", identifier="missing"),
            entry("sample.dump", identifier="walk"),
            entry("fixture.snmprec", identifier="changed", sha256="0" * 64),
        )
    )

    report = measure_snmp_corpus(manifest, tmp_path / "corpus.json")

    assert [result.identifier for result in report.results] == [
        "changed",
        "missing",
        "walk",
    ]
    assert [result.status for result in report.results] == [
        "checksum_mismatch",
        "missing",
        "unsupported_format",
    ]


def test_discovers_and_measures_compressed_corpus_recording(tmp_path: Path):
    category = tmp_path / "network"
    category.mkdir()
    compressed = category / "switch.snmprec.bz2"
    compressed.write_bytes(bz2.compress(FIXTURE.read_bytes()))

    manifest = discover_snmp_corpus(
        tmp_path,
        source_url="https://example.invalid/corpus",
        license_name="BSD-2-Clause",
    )
    report = measure_snmp_corpus(manifest, tmp_path / "manifest.json")

    assert manifest.entries[0].device_category == "network"
    assert manifest.entries[0].path == "network/switch.snmprec.bz2"
    assert report.results[0].status == "measured"
    assert report.results[0].format == "snmprec.bz2"
    assert report.results[0].interfaces == 3


def test_reports_decompressed_resource_limit(tmp_path: Path):
    recording = tmp_path / "large.snmprec.bz2"
    recording.write_bytes(bz2.compress(FIXTURE.read_bytes()))
    manifest = SnmpCorpusManifest(entries=(entry(recording.name),))

    report = measure_snmp_corpus(
        manifest,
        tmp_path / "manifest.json",
        max_recording_bytes=10,
    )

    assert report.max_recording_bytes == 10
    assert report.results[0].status == "resource_limit"


def test_snmprec_preserves_non_utf8_octets(tmp_path: Path):
    recording = tmp_path / "octets.snmprec"
    recording.write_bytes(b"1.3.6.1.2.1.1.5.0|4|switch-\x80\n")
    manifest = SnmpCorpusManifest(entries=(entry(recording.name),))

    report = measure_snmp_corpus(manifest, tmp_path / "manifest.json")

    assert report.results[0].status == "measured"
    assert report.results[0].system_fields == 1


def test_tolerant_corpus_retains_malformed_snmprec_lines(tmp_path: Path):
    recording = tmp_path / "legacy.snmprec"
    recording.write_text(
        "1.3.6.1.2.1.1.5.0|4|switch\nraw-fragment\n",
        encoding="utf-8",
    )
    decoded = read_snmprec_recording(recording)
    manifest = SnmpCorpusManifest(entries=(entry(recording.name),))

    report = measure_snmp_corpus(manifest, tmp_path / "manifest.json")

    assert decoded.unparsed_lines[0].text == "raw-fragment"
    assert report.results[0].status == "measured"
    assert report.results[0].system_fields == 1
    assert report.results[0].unparsed_lines == 1
