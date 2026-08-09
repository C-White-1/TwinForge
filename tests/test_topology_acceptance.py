import json
from datetime import datetime, timezone

import pytest

from twinforge.discovery.acceptance import (
    AcceptancePolicyError,
    CandidateDisposition,
)
from twinforge.discovery.topology import (
    TopologyConfidence,
    TopologyCorrelationResult,
    TopologyEvidenceReference,
    TopologyRelationshipCandidate,
    TopologyRelationshipType,
)
from twinforge.discovery.topology_acceptance import (
    TopologyRelationshipReview,
    apply_topology_reviews,
    topology_acceptance_json,
)


TIMESTAMP = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _candidate(
    key: str,
    relationship_type: TopologyRelationshipType,
) -> TopologyRelationshipCandidate:
    return TopologyRelationshipCandidate(
        key=key,
        relationship_type=relationship_type,
        source_node_key="target:switch",
        target_node_key="target:plc",
        source_interface_index=3,
        source_port_number=2,
        target_port_id="1",
        confidence=(
            TopologyConfidence.PROTOCOL_REPORTED
            if relationship_type is TopologyRelationshipType.REPORTED_NEIGHBOUR
            else TopologyConfidence.INDIRECT
        ),
        evidence=(
            TopologyEvidenceReference(
                protocol="lldp"
                if relationship_type is TopologyRelationshipType.REPORTED_NEIGHBOUR
                else "bridge_fdb",
                observation_target="switch",
                identifier="fixture-oid",
                description="sanitized fixture evidence",
            ),
        ),
    )


def _topology() -> TopologyCorrelationResult:
    return TopologyCorrelationResult(
        nodes=(),
        relationships=(
            _candidate("lldp-link", TopologyRelationshipType.REPORTED_NEIGHBOUR),
            _candidate("fdb-reach", TopologyRelationshipType.MAC_REACHABILITY),
        ),
    )


def test_accepts_reviewed_lldp_link_and_retains_unreviewed_partition() -> None:
    review = TopologyRelationshipReview(
        candidate_key="lldp-link",
        disposition=CandidateDisposition.ACCEPT,
        reviewed_by="operator@example.test",
        reviewed_at=TIMESTAMP,
        rationale="Verified against the controlled lab patching schedule",
        source_asset_key="asset:switch-1",
        target_asset_key="asset:plc-1",
    )

    result = apply_topology_reviews(_topology(), (review,))
    document = json.loads(topology_acceptance_json(result))

    assert result.accepted_relationships[0].candidate_key == "lldp-link"
    assert result.unreviewed_candidate_keys == ("fdb-reach",)
    assert document["accepted_relationships"][0]["source_asset_key"] == (
        "asset:switch-1"
    )
    assert document["accepted_relationships"][0]["evidence_class"] == (
        "operator_accepted"
    )


def test_indirect_mac_reachability_cannot_be_accepted_as_connection() -> None:
    review = TopologyRelationshipReview(
        candidate_key="fdb-reach",
        disposition=CandidateDisposition.ACCEPT,
        reviewed_by="operator@example.test",
        reviewed_at=TIMESTAMP,
        rationale="Attempted invalid promotion",
        source_asset_key="asset:switch-1",
        target_asset_key="asset:plc-1",
    )

    with pytest.raises(AcceptancePolicyError, match="MAC reachability"):
        apply_topology_reviews(_topology(), (review,))


@pytest.mark.parametrize(
    "disposition",
    (CandidateDisposition.REJECT, CandidateDisposition.DEFER),
)
def test_nonaccepted_reviews_cannot_map_endpoints(
    disposition: CandidateDisposition,
) -> None:
    review = TopologyRelationshipReview(
        candidate_key="lldp-link",
        disposition=disposition,
        reviewed_by="operator@example.test",
        reviewed_at=TIMESTAMP,
        rationale="Needs further verification",
        source_asset_key="asset:switch-1",
    )

    with pytest.raises(AcceptancePolicyError, match="cannot map"):
        apply_topology_reviews(_topology(), (review,))


def test_duplicate_and_unknown_reviews_fail_closed() -> None:
    review = TopologyRelationshipReview(
        candidate_key="lldp-link",
        disposition=CandidateDisposition.DEFER,
        reviewed_by="operator@example.test",
        reviewed_at=TIMESTAMP,
        rationale="Awaiting drawing review",
    )

    with pytest.raises(AcceptancePolicyError, match="duplicate"):
        apply_topology_reviews(_topology(), (review, review))
    unknown = TopologyRelationshipReview(
        candidate_key="unknown",
        disposition=CandidateDisposition.DEFER,
        reviewed_by="operator@example.test",
        reviewed_at=TIMESTAMP,
        rationale="No matching evidence",
    )
    with pytest.raises(AcceptancePolicyError, match="unknown"):
        apply_topology_reviews(_topology(), (unknown,))
