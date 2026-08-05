from pathlib import Path
from datetime import datetime, timezone

from twinforge.discovery import DiscoveryTarget, SnmprecDiscoveryProvider


FIXTURE = (
    Path(__file__).parents[1]
    / "examples"
    / "SNMPSim"
    / "data"
    / "twinforge-switch.snmprec"
)


def oid_key(oid: str) -> tuple[int, ...]:
    return tuple(int(part) for part in oid.split("."))


def test_sanitized_snmpsim_fixture_is_ordered_and_well_formed() -> None:
    records = [
        line.split("|", maxsplit=2)
        for line in FIXTURE.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    oids = [record[0] for record in records]

    assert all(len(record) == 3 for record in records)
    assert len(oids) == len(set(oids))
    assert oids == sorted(oids, key=oid_key)
    assert "1.3.6.1.2.1.1.5.0" in oids
    assert any(oid.startswith("1.0.8802.1.1.2") for oid in oids)
    assert any(oid.startswith("1.3.6.1.2.1.17.4.3") for oid in oids)


def test_recording_provider_builds_evidence_without_inferring_port_numbers() -> None:
    target = DiscoveryTarget(address="127.0.0.1", label="local-snmpsim")
    provider = SnmprecDiscoveryProvider({target.key: FIXTURE})

    node = provider.read_snmp_node(
        target,
        captured_at=datetime(2026, 8, 4, tzinfo=timezone.utc),
    )

    assert node.system_name == "SW-LAB-01"
    assert len(node.interfaces) == 3
    assert node.interfaces[0].addresses[0].prefix_length == 24
    assert node.neighbours[0].local_port_number == 2
    assert node.neighbours[0].local_interface_index == 3
    assert node.neighbours[0].remote_system_name == "PLC-LAB-01"
    assert node.forwarding_entries[0].bridge_port == 2
    assert node.forwarding_entries[0].interface_index == 3
