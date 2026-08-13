from __future__ import annotations

from datetime import datetime, timezone

import pytest

from twinforge.discovery.cip_infrastructure_capture import CipInfrastructureCapture
from twinforge.discovery.cip_infrastructure_decode import (
    CipBinaryField,
    CipBinaryFieldType,
    CipInfrastructureDecodeProfile,
    decode_cip_infrastructure_capture,
)
from twinforge.discovery.cip_infrastructure_plan import (
    CipInfrastructureDiscoveryPlan,
    CipInfrastructureObject,
    CipInfrastructureReadRequest,
)
from twinforge.discovery.contracts import DiscoveryTarget
from twinforge.discovery.controller import CipObjectEvidence
from twinforge.discovery.controller_metadata import CipMetadataReadService


NOW = datetime(2026, 8, 14, tzinfo=timezone.utc)


def _capture(status: int = 0) -> CipInfrastructureCapture:
    target = DiscoveryTarget(address="192.0.2.25")
    request = CipInfrastructureReadRequest(
        object_type=CipInfrastructureObject.ASSEMBLY,
        instance=101,
        attribute=3,
        service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
        specification_reference="Example EDS Assembly 101",
    )
    plan = CipInfrastructureDiscoveryPlan(
        target=target,
        engagement="offline-fixture",
        authorization_reference="fixture",
        requests=(request,),
        maximum_requests=1,
    )
    return CipInfrastructureCapture(
        plan=plan,
        captured_at=NOW,
        object_evidence=(
            CipObjectEvidence(
                class_code=4,
                instance=101,
                attribute=3,
                service=14,
                general_status=status,
                response_payload_hex="3412fe99",
            ),
        ),
    )


def _profile() -> CipInfrastructureDecodeProfile:
    return CipInfrastructureDecodeProfile(
        name="Example input assembly",
        object_type=CipInfrastructureObject.ASSEMBLY,
        instance=101,
        attribute=3,
        service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
        specification_reference="Example EDS Assembly 101",
        expected_payload_size=4,
        fields=(
            CipBinaryField(
                name="status_word",
                offset=0,
                width=2,
                field_type=CipBinaryFieldType.UNSIGNED_INTEGER,
                specification_reference="Example manual table 7",
            ),
            CipBinaryField(
                name="signed_value",
                offset=2,
                width=1,
                field_type=CipBinaryFieldType.SIGNED_INTEGER,
                specification_reference="Example manual table 7",
            ),
        ),
    )


def test_decodes_only_cited_fields_and_retains_unclaimed_bytes() -> None:
    decoded = decode_cip_infrastructure_capture(_capture(), (_profile(),))
    evidence = decoded.object_evidence[0]

    assert evidence.response_payload_hex == "3412fe99"
    assert evidence.decoded["profile_name"] == "Example input assembly"
    fields = evidence.decoded["fields"]
    assert isinstance(fields, dict)
    status_word = fields["status_word"]
    signed_value = fields["signed_value"]
    assert isinstance(status_word, dict)
    assert isinstance(signed_value, dict)
    assert status_word["value"] == 0x1234
    assert signed_value["value"] == -2
    assert evidence.decoded["unclaimed_payload_hex"] == "99"


def test_does_not_decode_failed_response() -> None:
    decoded = decode_cip_infrastructure_capture(_capture(5), (_profile(),))

    assert decoded.object_evidence[0].decoded == {}
    assert decoded.object_evidence[0].response_payload_hex == "3412fe99"


def test_rejects_profile_mismatch_overlap_and_wrong_payload_size() -> None:
    profile = _profile()
    wrong_instance = CipInfrastructureDecodeProfile(
        name="Wrong instance",
        object_type=CipInfrastructureObject.ASSEMBLY,
        instance=102,
        attribute=3,
        service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
        specification_reference="Example EDS Assembly 102",
        fields=profile.fields,
    )
    with pytest.raises(ValueError, match="planned request"):
        decode_cip_infrastructure_capture(_capture(), (wrong_instance,))

    with pytest.raises(ValueError, match="must not overlap"):
        CipInfrastructureDecodeProfile(
            name="Overlap",
            object_type=CipInfrastructureObject.ASSEMBLY,
            instance=101,
            attribute=3,
            service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
            specification_reference="Example EDS Assembly 101",
            fields=(
                profile.fields[0],
                CipBinaryField(
                    name="overlap",
                    offset=1,
                    width=2,
                    field_type=CipBinaryFieldType.BYTES,
                    specification_reference="Example manual table 7",
                ),
            ),
        )

    wrong_size = CipInfrastructureDecodeProfile(
        name="Wrong size",
        object_type=CipInfrastructureObject.ASSEMBLY,
        instance=101,
        attribute=3,
        service=CipMetadataReadService.GET_ATTRIBUTE_SINGLE,
        specification_reference="Example EDS Assembly 101",
        expected_payload_size=5,
        fields=profile.fields,
    )
    with pytest.raises(ValueError, match="payload size"):
        decode_cip_infrastructure_capture(_capture(), (wrong_size,))
