"""Deterministic fake provider for routed controller and chassis tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from .chassis import CipChassisObservation, CipChassisSlotPlan
from .cip_routes import CipRouteDeclaration
from .contracts import DiscoveryProviderError, DiscoveryTarget
from .controller import CipControllerObservation


class FakeRoutedCipProvider:
    """Replay routed fixtures and record calls without opening sockets."""

    def __init__(
        self,
        *,
        controllers: dict[str, CipControllerObservation] | None = None,
        chassis: dict[str, CipChassisObservation] | None = None,
        failures: dict[tuple[str, str], tuple[str, str]] | None = None,
    ) -> None:
        self._controllers = controllers or {}
        self._chassis = chassis or {}
        self._failures = failures or {}
        self.calls: list[tuple[str, str]] = []

    def read_controller(
        self,
        target: DiscoveryTarget,
        *,
        route: CipRouteDeclaration | None,
        captured_at: datetime,
    ) -> CipControllerObservation:
        """Replay one direct or routed controller observation."""
        route_key = route.key if route is not None else "direct"
        key = f"{target.key}|{route_key}"
        self.calls.append(("controller", key))
        self._raise_failure("controller", key)
        try:
            fixture = self._controllers[key]
        except KeyError as error:
            raise DiscoveryProviderError(
                "controller_fixture_missing",
                f"no fake controller evidence exists for {key}",
            ) from error
        identity = replace(fixture.identity, captured_at=captured_at)
        return replace(fixture, captured_at=captured_at, identity=identity)

    def read_chassis(
        self,
        plan: CipChassisSlotPlan,
        *,
        captured_at: datetime,
    ) -> CipChassisObservation:
        """Replay one complete bounded chassis observation."""
        key = plan.route.key
        self.calls.append(("chassis", key))
        self._raise_failure("chassis", key)
        try:
            fixture = self._chassis[key]
        except KeyError as error:
            raise DiscoveryProviderError(
                "chassis_fixture_missing",
                f"no fake chassis evidence exists for {key}",
            ) from error
        slots = tuple(
            replace(
                item,
                identity=(
                    replace(item.identity, captured_at=captured_at)
                    if item.identity is not None
                    else None
                ),
            )
            for item in fixture.slots
        )
        return replace(fixture, captured_at=captured_at, slots=slots)

    def _raise_failure(self, kind: str, key: str) -> None:
        failure = self._failures.get((kind, key))
        if failure is not None:
            raise DiscoveryProviderError(*failure)
