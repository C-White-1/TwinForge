"""Capture the checked-in SNMPSim fixture through a bounded live adapter."""

import argparse
import os
from datetime import datetime, timezone

from twinforge.discovery import (
    DiscoveryOperation,
    DiscoveryScope,
    DiscoveryTarget,
    FakeDiscoveryProvider,
    SnmpDiscoveryProvider,
    capture_snapshot,
    correlate_topology,
    snapshot_json,
    topology_json,
)
from twinforge.discovery.snmp_pysnmp import (
    PySnmpLoopbackDiscoveryProvider,
    PySnmpV3LoopbackDiscoveryProvider,
    SnmpV3Credentials,
)


def _provider(version: str) -> SnmpDiscoveryProvider:
    if version == "2c":
        return PySnmpLoopbackDiscoveryProvider()
    return PySnmpV3LoopbackDiscoveryProvider(
        SnmpV3Credentials(
            username="twinforge-local",
            authentication_key=os.getenv(
                "TWINFORGE_SNMP_AUTH_KEY",
                "TwinForgeAuth2026",
            ),
            privacy_key=os.getenv(
                "TWINFORGE_SNMP_PRIVACY_KEY",
                "TwinForgePrivacy2026",
            ),
        )
    )


def main() -> None:
    """Print one deterministic-shape snapshot captured from local SNMPSim."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", choices=("2c", "3"), default="3")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--topology", action="store_true")
    arguments = parser.parse_args()
    target = DiscoveryTarget(address="127.0.0.1", label="local-snmpsim")
    scope = DiscoveryScope(
        engagement="TwinForge local SNMP laboratory",
        authorization_reference="loopback-only-example",
        targets=(target,),
        operations=(DiscoveryOperation.SNMP_NETWORK,),
    )
    snmp_provider = _provider(arguments.version)
    snapshot = capture_snapshot(
        scope,
        FakeDiscoveryProvider({}),
        snmp_provider=snmp_provider,
        captured_at=datetime.now(timezone.utc),
    )
    topology = correlate_topology(snapshot)
    if arguments.summary:
        node = snapshot.snmp_nodes[0] if snapshot.snmp_nodes else None
        print(f"nodes={len(snapshot.snmp_nodes)}")
        print(f"interfaces={len(node.interfaces) if node else 0}")
        print(f"neighbours={len(node.neighbours) if node else 0}")
        print(
            "forwarding_entries="
            f"{len(node.forwarding_entries) if node else 0}"
        )
        print(f"diagnostics={len(snapshot.diagnostics)}")
        print(f"topology_nodes={len(topology.nodes)}")
        print(f"topology_relationships={len(topology.relationships)}")
    elif arguments.topology:
        print(topology_json(topology), end="")
    else:
        print(snapshot_json(snapshot), end="")


if __name__ == "__main__":
    main()
