"""Experimental page-level Logix Symbol transport using public pycomm3 APIs."""

from __future__ import annotations

from importlib.metadata import version
from urllib.parse import quote, unquote

from pycomm3 import LogixDriver

from .cip_routes import CipRouteDeclaration
from .cip_target_policy import validate_live_cip_target_address
from .contracts import DiscoveryProviderError
from .controller import JsonEvidence
from .logix_symbol_codec import (
    GET_INSTANCE_ATTRIBUTE_LIST,
    LOGIX_SYMBOL_CLASS,
    LogixSymbolRecord,
    build_logix_symbol_page_request,
    decode_logix_symbol_page,
)
from .software_inventory_capture import CipSoftwareInventoryPage
from .software_inventory_plan import (
    CipSoftwareInventoryCapability,
    CipSoftwareInventoryPlan,
)


class ExperimentalPycomm3LogixSymbolTransport:
    """Read exactly one Symbol page per call; live validation is still pending."""

    def __init__(
        self,
        *,
        laboratory_evidence_reference: str,
        include_external_access: bool = True,
    ) -> None:
        if (
            not laboratory_evidence_reference
            or laboratory_evidence_reference
            != laboratory_evidence_reference.strip()
        ):
            raise ValueError(
                "laboratory_evidence_reference must be non-empty and trimmed"
            )
        self.laboratory_evidence_reference = laboratory_evidence_reference
        self.include_external_access = include_external_access
        self._programs: list[str] = []

    @property
    def capabilities(self) -> tuple[CipSoftwareInventoryCapability, ...]:
        """Return structural capabilities implemented by the page state machine."""
        return (
            CipSoftwareInventoryCapability.PROGRAMS,
            CipSoftwareInventoryCapability.ROUTINES,
            CipSoftwareInventoryCapability.TAG_DEFINITIONS,
            CipSoftwareInventoryCapability.TASKS,
        )

    @property
    def provider_metadata(self) -> dict[str, JsonEvidence]:
        """Identify the experimental adapter without exposing credentials."""
        return {
            "adapter": "ExperimentalPycomm3LogixSymbolTransport",
            "library": "pycomm3",
            "library_version": version("pycomm3"),
            "laboratory_evidence_reference": self.laboratory_evidence_reference,
            "experimental": True,
        }

    def read_inventory_page(
        self,
        plan: CipSoftwareInventoryPlan,
        cursor: str | None,
        timeout: float,
    ) -> CipSoftwareInventoryPage:
        """Issue one connected Symbol request and return one controlled page."""
        validate_live_cip_target_address(plan.target)
        if plan.route is None:
            raise DiscoveryProviderError(
                "logix_symbol_route_required",
                "the experimental Logix Symbol transport requires a route",
            )
        scope, program_index, start_instance = _decode_cursor(cursor)
        try:
            scope_program = (
                self._programs[program_index] if scope == "program" else None
            )
        except IndexError as error:
            raise DiscoveryProviderError(
                "logix_symbol_cursor_invalid",
                "Logix Symbol cursor references an unknown program scope",
            ) from error
        request = build_logix_symbol_page_request(
            start_instance,
            include_external_access=self.include_external_access,
        )
        driver = LogixDriver(
            pycomm3_logix_path(plan.route),
            init_tags=False,
            init_program_tags=False,
        )
        driver.socket_timeout = timeout
        try:
            if not driver.open():
                raise DiscoveryProviderError(
                    "logix_symbol_connection_failed",
                    f"pycomm3 could not connect to {plan.target.address}",
                )
            result = driver.generic_message(
                service=GET_INSTANCE_ATTRIBUTE_LIST,
                class_code=LOGIX_SYMBOL_CLASS,
                instance=start_instance,
                request_data=request.request_data,
                connected=True,
                name="TwinForge bounded Logix Symbol page",
                return_response_packet=True,
            )
            packet = result.value
            payload = getattr(packet, "data", None)
            status = getattr(packet, "service_status", None)
            raw_reply = getattr(packet, "raw", None)
            if not isinstance(payload, bytes) or not isinstance(status, int):
                raise DiscoveryProviderError(
                    "logix_symbol_invalid_reply",
                    str(result.error or "pycomm3 returned no Symbol page packet"),
                )
            decoded = decode_logix_symbol_page(
                payload,
                general_status=status,
                requested_capabilities=plan.capabilities,
                scope_program=scope_program,
                include_external_access=self.include_external_access,
                raw_reply=raw_reply if isinstance(raw_reply, bytes) else None,
                request_instance=start_instance,
            )
        finally:
            driver.close()

        if scope == "controller":
            self._remember_programs(decoded.records)
        next_cursor = self._next_cursor(
            scope,
            program_index,
            decoded.page.next_cursor,
            plan,
        )
        return CipSoftwareInventoryPage(
            items=decoded.page.items,
            next_cursor=next_cursor,
            object_evidence=decoded.page.object_evidence,
        )

    def _remember_programs(
        self,
        records: tuple[LogixSymbolRecord, ...],
    ) -> None:
        for record in records:
            if record.name.startswith("Program:"):
                name = record.name.removeprefix("Program:")
                if name not in self._programs:
                    self._programs.append(name)

    def _next_cursor(
        self,
        scope: str,
        program_index: int,
        numeric_cursor: str | None,
        plan: CipSoftwareInventoryPlan,
    ) -> str | None:
        if numeric_cursor is not None:
            return _encode_cursor(scope, program_index, int(numeric_cursor))
        program_scopes_required = bool(
            {
                CipSoftwareInventoryCapability.ROUTINES,
                CipSoftwareInventoryCapability.TAG_DEFINITIONS,
            }
            & set(plan.capabilities)
        )
        if scope == "controller":
            if program_scopes_required and self._programs:
                return _encode_cursor("program", 0, 0)
            return None
        next_program = program_index + 1
        if next_program < len(self._programs):
            return _encode_cursor("program", next_program, 0)
        return None


def pycomm3_logix_path(route: CipRouteDeclaration) -> str:
    """Translate an integer/text route into LogixDriver's public path syntax."""
    parts = [route.gateway.address]
    for segment in route.segments:
        if isinstance(segment.link, bytes):
            raise ValueError("LogixDriver path does not accept binary route links")
        link = str(segment.link)
        if "/" in link or "," in link or "\\" in link:
            raise ValueError("LogixDriver text route links must not contain separators")
        parts.extend((str(segment.port), link))
    return "/".join(parts)


def _encode_cursor(scope: str, program_index: int, instance: int) -> str:
    return f"{scope}:{program_index}:{instance}"


def _decode_cursor(cursor: str | None) -> tuple[str, int, int]:
    if cursor is None:
        return "controller", 0, 0
    try:
        scope, program_index, instance = cursor.split(":", maxsplit=2)
        if scope not in {"controller", "program"}:
            raise ValueError("unknown scope")
        return unquote(scope), int(program_index), int(instance)
    except (ValueError, TypeError) as error:
        raise DiscoveryProviderError(
            "logix_symbol_cursor_invalid",
            f"invalid Logix Symbol cursor: {quote(cursor)}",
        ) from error
