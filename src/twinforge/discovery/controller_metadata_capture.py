"""Permission-gated execution and lowering of controller metadata plans."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Callable, Protocol

from .cip_pycomm3_routed import (
    RoutedExecutionPermit,
    validate_routed_execution,
)
from .cip_routes import CipRouteDeclaration
from .contracts import DiscoveryProviderError, DiscoveryTarget
from .controller import (
    CipControllerObservation,
    CipObjectEvidence,
    JsonEvidence,
)
from .controller_metadata import (
    CipControllerMetadataPlan,
    CipControllerMetadataRequest,
    ControllerMetadataField,
    cip_controller_metadata_plan_data,
)


MetadataDecoder = Callable[[bytes], JsonEvidence]


@dataclass(frozen=True)
class CipMetadataTransportResult:
    """Raw result of one allowlisted metadata object request."""

    general_status: int
    response_payload: bytes
    additional_status: tuple[int, ...] = ()
    raw_reply: bytes | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        if self.general_status < 0 or any(
            value < 0 for value in self.additional_status
        ):
            raise ValueError("CIP metadata status values must not be negative")


class CipMetadataTransport(Protocol):
    """Injectable boundary for one exact metadata request."""

    def read_metadata(
        self,
        target: DiscoveryTarget,
        route: CipRouteDeclaration,
        request: CipControllerMetadataRequest,
        timeout: float,
    ) -> CipMetadataTransportResult:
        """Return raw status and payload evidence for one planned request."""
        ...


@dataclass(frozen=True)
class CipControllerMetadataCapture:
    """Complete object evidence and decoded fields for one metadata plan."""

    plan: CipControllerMetadataPlan
    captured_at: datetime
    values: dict[ControllerMetadataField, str]
    object_evidence: tuple[CipObjectEvidence, ...]

    def __post_init__(self) -> None:
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must include a timezone")


class PermittedControllerMetadataExecutor:
    """Execute a metadata plan once after complete authorization preflight."""

    def __init__(
        self,
        plan: CipControllerMetadataPlan,
        *,
        permit: RoutedExecutionPermit | None,
        transport: CipMetadataTransport,
        decoders: dict[str, MetadataDecoder] | None = None,
        timeout: float = 2.0,
    ) -> None:
        if plan.route is None:
            raise ValueError("metadata executor currently requires a routed plan")
        if timeout <= 0 or timeout > 10:
            raise ValueError("timeout must be greater than 0 and at most 10 seconds")
        self._plan = plan
        self._permit = permit
        self._transport = transport
        self._decoders = decoders or {}
        self._timeout = timeout
        self._executed = False

    def capture(self, *, captured_at: datetime) -> CipControllerMetadataCapture:
        """Execute every request once, retaining failures as object evidence."""
        if captured_at.tzinfo is None:
            raise ValueError("captured_at must include a timezone")
        assert self._plan.route is not None
        validate_routed_execution(
            self._permit,
            self._plan.authorization_reference,
            (self._plan.route.key,),
        )
        missing_decoders = sorted(
            {
                request.decoder
                for request in self._plan.requests
                if request.decoder is not None
                and request.decoder not in self._decoders
            }
        )
        if missing_decoders:
            raise DiscoveryProviderError(
                "cip_metadata_decoder_missing",
                "metadata plan references unregistered decoders: "
                + ", ".join(missing_decoders),
            )
        if self._executed:
            raise DiscoveryProviderError(
                "cip_metadata_request_budget_exceeded",
                "the controller metadata plan request budget is exhausted",
            )
        self._executed = True

        values: dict[ControllerMetadataField, str] = {}
        evidence: list[CipObjectEvidence] = []
        for request in _ordered_requests(self._plan):
            result = self._transport.read_metadata(
                self._plan.target,
                self._plan.route,
                request,
                self._timeout,
            )
            decoded: dict[str, JsonEvidence] = {}
            if result.general_status == 0 and request.decoder is not None:
                value = self._decoders[request.decoder](result.response_payload)
                decoded[request.decoder] = value
                if request.semantic_field is not None:
                    if not isinstance(value, str):
                        raise DiscoveryProviderError(
                            "cip_metadata_semantic_type_mismatch",
                            "vendor-neutral controller metadata must decode to text",
                        )
                    values[request.semantic_field] = value
            evidence.append(
                CipObjectEvidence(
                    class_code=request.class_code,
                    instance=request.instance,
                    attribute=request.attribute,
                    service=request.service.value,
                    general_status=result.general_status,
                    additional_status=result.additional_status,
                    response_payload_hex=result.response_payload.hex(),
                    raw_reply_hex=(
                        result.raw_reply.hex()
                        if result.raw_reply is not None
                        else None
                    ),
                    message=result.message,
                    decoded=decoded,
                )
            )
        return CipControllerMetadataCapture(
            plan=self._plan,
            captured_at=captured_at,
            values=values,
            object_evidence=tuple(evidence),
        )


def apply_controller_metadata(
    observation: CipControllerObservation,
    capture: CipControllerMetadataCapture,
) -> CipControllerObservation:
    """Merge only explicitly decoded fields into matching controller evidence."""
    if observation.target.key != capture.plan.target.key:
        raise ValueError("metadata capture target does not match controller")
    if observation.route != capture.plan.route:
        raise ValueError("metadata capture route does not match controller")
    field_values = {
        field.value: value for field, value in capture.values.items()
    }
    return replace(
        observation,
        logical_name=field_values.get(
            ControllerMetadataField.LOGICAL_NAME.value,
            observation.logical_name,
        ),
        project_name=field_values.get(
            ControllerMetadataField.PROJECT_NAME.value,
            observation.project_name,
        ),
        project_revision=field_values.get(
            ControllerMetadataField.PROJECT_REVISION.value,
            observation.project_revision,
        ),
        firmware_revision=field_values.get(
            ControllerMetadataField.FIRMWARE_REVISION.value,
            observation.firmware_revision,
        ),
        operating_mode=field_values.get(
            ControllerMetadataField.OPERATING_MODE.value,
            observation.operating_mode,
        ),
        object_evidence=observation.object_evidence + capture.object_evidence,
    )


def cip_controller_metadata_capture_data(
    capture: CipControllerMetadataCapture,
) -> dict[str, Any]:
    """Return deterministic decoded values and raw object evidence."""
    return {
        "schema_version": "1.0",
        "captured_at": capture.captured_at.isoformat(),
        "plan": cip_controller_metadata_plan_data(capture.plan),
        "values": {
            field.value: value
            for field, value in sorted(
                capture.values.items(),
                key=lambda item: item[0].value,
            )
        },
        "object_evidence": [
            {
                "class_code": item.class_code,
                "instance": item.instance,
                "attribute": item.attribute,
                "service": item.service,
                "general_status": item.general_status,
                "additional_status": list(item.additional_status),
                "response_payload_hex": item.response_payload_hex,
                "raw_reply_hex": item.raw_reply_hex,
                "message": item.message,
                "decoded": dict(sorted(item.decoded.items())),
            }
            for item in capture.object_evidence
        ],
    }


def cip_controller_metadata_capture_json(
    capture: CipControllerMetadataCapture,
) -> str:
    """Serialize metadata capture evidence with a final newline."""
    return json.dumps(
        cip_controller_metadata_capture_data(capture),
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def _ordered_requests(
    plan: CipControllerMetadataPlan,
) -> tuple[CipControllerMetadataRequest, ...]:
    return tuple(
        sorted(
            plan.requests,
            key=lambda item: (
                item.service.value,
                item.class_code,
                item.instance,
                item.attribute if item.attribute is not None else -1,
            ),
        )
    )
