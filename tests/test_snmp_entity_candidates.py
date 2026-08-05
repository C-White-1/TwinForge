from datetime import datetime, timezone

from twinforge.discovery import (
    DiscoveryOperation,
    DiscoverySnapshot,
    DiscoveryTarget,
    SnmpNodeObservation,
    SnmpPhysicalEntityObservation,
    TopologyConfidence,
    correlate_physical_entities,
    physical_candidate_json,
)


CAPTURED_AT = datetime(2026, 8, 5, tzinfo=timezone.utc)
BASE = "1.3.6.1.2.1.47.1.1.1.1"


def _snapshot(*entities: SnmpPhysicalEntityObservation) -> DiscoverySnapshot:
    target = DiscoveryTarget(address="fixture:entity")
    return DiscoverySnapshot(
        schema_version="1.0",
        engagement="authorized-lab",
        authorization_reference="lab-ticket-entity",
        captured_at=CAPTURED_AT,
        operations=(DiscoveryOperation.SNMP_NETWORK,),
        targets=(target,),
        identities=(),
        snmp_nodes=(
            SnmpNodeObservation(
                target=target,
                captured_at=CAPTURED_AT,
                physical_entities=entities,
            ),
        ),
    )


def test_builds_evidence_backed_assets_and_resolved_containment() -> None:
    result = correlate_physical_entities(
        _snapshot(
            SnmpPhysicalEntityObservation(
                index=100,
                physical_class=3,
                name="Chassis",
                manufacturer_name="Example Corp",
                model_name="EX-1000",
                raw_oids={f"{BASE}.5.100": 3},
            ),
            SnmpPhysicalEntityObservation(
                index=200,
                contained_in=100,
                physical_class=9,
                parent_relative_position=2,
                name="I/O module",
                raw_oids={
                    f"{BASE}.4.200": 100,
                    f"{BASE}.6.200": 2,
                    f"{BASE}.7.200": "I/O module",
                },
            ),
        )
    )

    assert [asset.entity_index for asset in result.assets] == [100, 200]
    assert result.assets[0].confidence is TopologyConfidence.PROTOCOL_REPORTED
    assert result.assets[0].manufacturer_name == "Example Corp"
    assert len(result.containments) == 1
    containment = result.containments[0]
    assert containment.parent_asset_key.endswith("entity:100")
    assert containment.child_asset_key.endswith("entity:200")
    assert containment.parent_relative_position == 2
    assert {item.identifier for item in containment.evidence} == {
        f"{BASE}.4.200",
        f"{BASE}.6.200",
    }
    assert result.issues == ()


def test_withholds_invalid_edges_but_retains_assets_and_findings() -> None:
    result = correlate_physical_entities(
        _snapshot(
            SnmpPhysicalEntityObservation(index=1, contained_in=99),
            SnmpPhysicalEntityObservation(index=2, contained_in=3),
            SnmpPhysicalEntityObservation(index=3, contained_in=2),
        )
    )

    assert [asset.entity_index for asset in result.assets] == [1, 2, 3]
    assert result.containments == ()
    assert {issue.code for issue in result.issues} == {
        "missing_parent",
        "containment_cycle",
    }


def test_physical_candidate_serialization_is_deterministic() -> None:
    snapshot = _snapshot(
        SnmpPhysicalEntityObservation(index=2, name="Second"),
        SnmpPhysicalEntityObservation(index=1, name="First"),
    )

    first = physical_candidate_json(correlate_physical_entities(snapshot))
    second = physical_candidate_json(correlate_physical_entities(snapshot))

    assert first == second
    assert first.endswith("\n")
    assert first.index('"entity_index": 1') < first.index('"entity_index": 2')
