from pathlib import Path

from twinforge.discovery import (
    SnmpCorpusEntry,
    SnmpCorpusManifest,
    measure_snmp_corpus,
    read_snmpwalk,
)


def write_walk(path: Path) -> None:
    path.write_text(
        "\n".join(
            (
                "SNMPv2-MIB::sysDescr.0 = STRING: Example switch",
                "SNMPv2-MIB::sysName.0 = STRING: switch-01",
                "DISMAN-EVENT-MIB::sysUpTimeInstance = Timeticks: (12345) 0:02:03.45",
                "IF-MIB::ifIndex.1 = INTEGER: 1",
                "IF-MIB::ifDescr.1 = STRING: Ethernet 1",
                "IF-MIB::ifName.1 = STRING: eth1",
                "IF-MIB::ifAdminStatus.1 = INTEGER: up(1)",
                "IF-MIB::ifOperStatus.1 = INTEGER: up(1)",
                "IP-MIB::ipAdEntAddr.192.0.2.10 = IpAddress: 192.0.2.10",
                "IP-MIB::ipAdEntIfIndex.192.0.2.10 = INTEGER: 1",
                "IP-MIB::ipAdEntNetMask.192.0.2.10 = IpAddress: 255.255.255.0",
                "VENDOR-MIB::unknownThing.0 = STRING: retained",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def test_reads_symbolic_snmpwalk_and_retains_unknown_evidence(tmp_path: Path):
    path = tmp_path / "switch.snmpwalk"
    write_walk(path)

    recording = read_snmpwalk(path)

    assert recording.records["1.3.6.1.2.1.1.5.0"].value == "switch-01"
    assert recording.records["1.3.6.1.2.1.2.2.1.7.1"].value == 1
    assert recording.unparsed_lines[0].number == 12
    assert recording.unparsed_lines[0].text.endswith("STRING: retained")


def test_corpus_measures_snmpwalk_through_shared_lowering(tmp_path: Path):
    path = tmp_path / "switch.snmpwalk"
    write_walk(path)
    entry = SnmpCorpusEntry(
        identifier="walk-switch",
        path=path.name,
        source_url="https://example.invalid/source",
        license="BSD-2-Clause",
        device_category="switch",
        sanitized=True,
    )

    report = measure_snmp_corpus(
        SnmpCorpusManifest(entries=(entry,)),
        tmp_path / "manifest.json",
    )

    result = report.results[0]
    assert result.status == "measured"
    assert result.format == "snmpwalk"
    assert result.interfaces == 1
    assert result.addresses == 1
    assert result.unparsed_lines == 1
