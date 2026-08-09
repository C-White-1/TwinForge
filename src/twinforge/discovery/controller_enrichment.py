"""Composition of routed controller Identity and metadata providers."""

from __future__ import annotations

from datetime import datetime

from .cip_routes import CipRouteDeclaration
from .contracts import DiscoveryProviderError, DiscoveryTarget
from .controller import (
    CipControllerDiscoveryProvider,
    CipControllerObservation,
)
from .controller_metadata_capture import (
    PermittedControllerMetadataExecutor,
    apply_controller_metadata,
)


class MetadataEnrichedControllerProvider:
    """Decorate controller Identity evidence with explicitly planned metadata."""

    def __init__(
        self,
        identity_provider: CipControllerDiscoveryProvider,
        metadata_executor: PermittedControllerMetadataExecutor,
    ) -> None:
        self._identity_provider = identity_provider
        self._metadata_executor = metadata_executor

    def read_controller(
        self,
        target: DiscoveryTarget,
        *,
        route: CipRouteDeclaration | None,
        captured_at: datetime,
    ) -> CipControllerObservation:
        """Preflight both layers, then capture and merge their evidence."""
        plan = self._metadata_executor.plan
        if plan.target.key != target.key or plan.route != route:
            raise DiscoveryProviderError(
                "cip_metadata_plan_controller_mismatch",
                "metadata plan does not match the requested controller",
            )
        self._metadata_executor.preflight()
        observation = self._identity_provider.read_controller(
            target,
            route=route,
            captured_at=captured_at,
        )
        required_vendor_id = plan.required_vendor_id
        if (
            required_vendor_id is not None
            and observation.identity.vendor_id != required_vendor_id
        ):
            raise DiscoveryProviderError(
                "cip_metadata_vendor_mismatch",
                "controller Identity vendor does not match the metadata plan",
            )
        metadata = self._metadata_executor.capture(captured_at=captured_at)
        return apply_controller_metadata(observation, metadata)
