"""CLI planning and explicit experimental execution for CIP software inventory."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from twinforge.discovery import (
    CipRouteDeclaration,
    CipRouteSegment,
    CipSoftwareInventoryCapability,
    CipSoftwareInventoryPlan,
    DiscoveryProviderError,
    DiscoveryTarget,
    ExperimentalPycomm3LogixSymbolTransport,
    PermittedSoftwareInventoryExecutor,
    RoutedExecutionPermit,
    cip_software_inventory_observation_json,
    cip_software_inventory_plan_json,
)


class CipSoftwareCommandError(RuntimeError):
    """A safe, user-facing CIP software command failure."""


def discover_cip_software(
    address: str,
    *,
    route_segments: tuple[str, ...],
    authorization_reference: str,
    capability_names: tuple[str, ...],
    maximum_requests: int,
    execute_experimental: bool,
    confirmed_by: str | None,
    confirmed_at: str | None,
    laboratory_evidence_reference: str | None,
    destination: Path | None,
    stdout: TextIO,
) -> None:
    """Write a dry-run plan or explicitly execute the experimental adapter."""
    try:
        target = DiscoveryTarget(address=address)
        route = CipRouteDeclaration(
            gateway=target,
            segments=tuple(_parse_route_segment(item) for item in route_segments),
            maximum_depth=len(route_segments),
        )
        capabilities = tuple(
            sorted(
                {
                    CipSoftwareInventoryCapability(name)
                    for name in capability_names
                },
                key=lambda item: item.value,
            )
        )
        plan = CipSoftwareInventoryPlan(
            target=target,
            route=route,
            authorization_reference=authorization_reference,
            capabilities=capabilities,
            maximum_requests=maximum_requests,
        )
        if not execute_experimental:
            _write_output(cip_software_inventory_plan_json(plan), destination, stdout)
            return
        missing = [
            name
            for name, value in (
                ("--confirmed-by", confirmed_by),
                ("--confirmed-at", confirmed_at),
                ("--laboratory-evidence-reference", laboratory_evidence_reference),
            )
            if value is None
        ]
        if missing:
            raise CipSoftwareCommandError(
                "experimental execution also requires " + ", ".join(missing)
            )
        assert confirmed_by is not None
        assert confirmed_at is not None
        assert laboratory_evidence_reference is not None
        confirmation = datetime.fromisoformat(confirmed_at)
        if confirmation.tzinfo is None:
            raise CipSoftwareCommandError(
                "--confirmed-at must include a timezone offset"
            )
        permit = RoutedExecutionPermit(
            authorization_reference=authorization_reference,
            confirmed_by=confirmed_by,
            confirmed_at=confirmation,
            allowed_route_keys=(route.key,),
        )
        transport = ExperimentalPycomm3LogixSymbolTransport(
            laboratory_evidence_reference=laboratory_evidence_reference,
        )
        observation = PermittedSoftwareInventoryExecutor(
            plan,
            permit=permit,
            transport=transport,
        ).capture(captured_at=datetime.now(timezone.utc))
        _write_output(
            cip_software_inventory_observation_json(observation),
            destination,
            stdout,
        )
    except (DiscoveryProviderError, ValueError) as error:
        if isinstance(error, CipSoftwareCommandError):
            raise
        raise CipSoftwareCommandError(str(error)) from error


def _parse_route_segment(value: str) -> CipRouteSegment:
    try:
        port_text, link_text = value.split("/", maxsplit=1)
        port = int(port_text)
        link: int | str = int(link_text) if link_text.isdecimal() else link_text
        return CipRouteSegment(port=port, link=link)
    except (TypeError, ValueError) as error:
        raise CipSoftwareCommandError(
            f"invalid route segment {value!r}; expected PORT/LINK"
        ) from error


def _write_output(document: str, destination: Path | None, stdout: TextIO) -> None:
    if destination is None:
        stdout.write(document)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    stdout.write(f"Wrote {destination}\n")
