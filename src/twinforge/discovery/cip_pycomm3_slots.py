"""Live routed slot transport with evidence-backed status classification."""

from __future__ import annotations

from dataclasses import dataclass

from pycomm3 import CIPDriver, ClassCode, CommError, Services

from .cip_pycomm3 import CipIdentityReply
from .cip_pycomm3_chassis import RoutedSlotOutcome, RoutedSlotResult
from .cip_pycomm3_packets import extract_pycomm3_cip_packet_evidence
from .cip_pycomm3_routes import encode_pycomm3_route
from .cip_routes import CipRouteDeclaration


@dataclass(frozen=True)
class CipSlotStatusSignature:
    """Exact failed response signature and its evidence-backed interpretation."""

    general_status: int
    additional_status: tuple[int, ...]
    outcome: RoutedSlotOutcome
    source_reference: str

    def __post_init__(self) -> None:
        if self.general_status <= 0:
            raise ValueError("slot failure signature requires a non-zero status")
        if self.outcome not in (
            RoutedSlotOutcome.EMPTY,
            RoutedSlotOutcome.UNSUPPORTED_ROUTE,
            RoutedSlotOutcome.DEVICE_FAULT,
        ):
            raise ValueError("slot signature must classify a failed CIP response")
        if not self.source_reference.strip():
            raise ValueError("slot signature source_reference must not be empty")


@dataclass(frozen=True)
class CipSlotStatusProfile:
    """Named set of exact status signatures from a specification or fixture."""

    name: str
    signatures: tuple[CipSlotStatusSignature, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("slot status profile name must not be empty")
        keys = [
            (item.general_status, item.additional_status)
            for item in self.signatures
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("slot status profile signatures must be unique")

    def classify(
        self,
        general_status: int,
        additional_status: tuple[int, ...],
    ) -> tuple[RoutedSlotOutcome, str | None]:
        """Return an exact match or conservatively retain a device fault."""
        for signature in self.signatures:
            if (
                signature.general_status == general_status
                and signature.additional_status == additional_status
            ):
                return signature.outcome, signature.source_reference
        return RoutedSlotOutcome.DEVICE_FAULT, None


class LivePycomm3RoutedSlotTransport:
    """Read one routed Identity and classify only documented status signatures."""

    def __init__(self, profile: CipSlotStatusProfile | None = None) -> None:
        self._profile = profile or CipSlotStatusProfile(
            name="conservative-unclassified"
        )

    def read_slot_identity(
        self,
        route: CipRouteDeclaration,
        timeout: float,
    ) -> RoutedSlotResult:
        """Issue one exact UCMM Identity read through ``route``."""
        encoding = encode_pycomm3_route(route)
        driver = CIPDriver(route.gateway.address)
        driver.socket_timeout = timeout
        try:
            opened = driver.open()
            if not opened:
                return RoutedSlotResult(
                    outcome=RoutedSlotOutcome.NO_RESPONSE,
                    message="pycomm3 could not connect to the route gateway",
                    raw_attributes={"profile": self._profile.name},
                )
            result = driver.generic_message(
                service=Services.get_attributes_all,
                class_code=ClassCode.identity_object,
                instance=1,
                connected=False,
                unconnected_send=True,
                route_path=encoding.encoded_unconnected_route_path,
                name="Routed slot Identity Object Get_Attributes_All",
                return_response_packet=True,
            )
            packet = result.value
            raw_reply = getattr(packet, "raw", None)
            if not isinstance(raw_reply, bytes):
                return RoutedSlotResult(
                    outcome=RoutedSlotOutcome.NO_RESPONSE,
                    message=str(result.error or "slot request returned no packet"),
                    raw_attributes={"profile": self._profile.name},
                )
            evidence = extract_pycomm3_cip_packet_evidence(raw_reply)
            if evidence.general_status == 0:
                return RoutedSlotResult(
                    outcome=RoutedSlotOutcome.POPULATED,
                    reply=CipIdentityReply(
                        payload=evidence.payload,
                        raw_reply=raw_reply,
                    ),
                    raw_response=raw_reply,
                    general_status=0,
                    raw_attributes={"profile": self._profile.name},
                )
            outcome, source_reference = self._profile.classify(
                evidence.general_status,
                evidence.additional_status,
            )
            return RoutedSlotResult(
                outcome=outcome,
                raw_response=raw_reply,
                general_status=evidence.general_status,
                additional_status=evidence.additional_status,
                message=str(result.error) if result.error else None,
                raw_attributes={
                    "profile": self._profile.name,
                    "classification_source": source_reference,
                    "classification_matched": source_reference is not None,
                },
            )
        except CommError as error:
            return RoutedSlotResult(
                outcome=RoutedSlotOutcome.NO_RESPONSE,
                message=str(error),
                raw_attributes={"profile": self._profile.name},
            )
        finally:
            driver.close()
