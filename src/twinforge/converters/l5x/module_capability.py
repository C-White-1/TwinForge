"""Pluggable module-capability inference from explicit vendor evidence."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Protocol

from twinforge.model import (
    EngineeringRangeEvidence,
    Identity,
    IODirection,
    IOSignalType,
    ModuleCapability,
)
from twinforge.parsers.l5x.capture import CapturedSection


class ModuleCapabilityProvider(Protocol):
    """Infer a capability only when a provider recognizes its evidence."""

    def infer(
        self,
        module: CapturedSection,
        identity: Identity,
        engineering_ranges: Mapping[str, EngineeringRangeEvidence],
    ) -> ModuleCapability | None:
        """Return a supported capability, otherwise defer to another provider."""


class Rockwell1756CatalogCapabilityProvider:
    """Decode recognized Rockwell 1756 I/O catalog-number conventions."""

    _catalog_pattern = re.compile(
        r"1756-(?P<direction>[IO])(?P<signal>[BF])"
        r"(?P<count>\d+)[A-Z0-9]*",
        re.IGNORECASE,
    )

    def infer(
        self,
        module: CapturedSection,
        identity: Identity,
        engineering_ranges: Mapping[str, EngineeringRangeEvidence],
    ) -> ModuleCapability | None:
        """Infer nominal capacity for Vendor ID 1 and recognized 1756 I/O."""

        vendor = identity.vendor
        if vendor is None or vendor.id != 1:
            return None
        match = self._catalog_pattern.fullmatch(
            module.attributes.get("CatalogNumber", "")
        )
        if match is None:
            return None

        direction = (
            IODirection.INPUT
            if match.group("direction").upper() == "I"
            else IODirection.OUTPUT
        )
        signal_type = (
            IOSignalType.DIGITAL
            if match.group("signal").upper() == "B"
            else IOSignalType.ANALOG
        )
        nominal_count = int(match.group("count"))
        configured_count = self._configured_count(
            direction,
            signal_type,
            nominal_count,
            engineering_ranges,
        )
        return ModuleCapability(
            signal_type=signal_type,
            direction=direction,
            nominal_channel_count=nominal_count,
            configured_channel_count=configured_count,
            source="rockwell_1756_catalog_convention+l5x_configuration",
        )

    @staticmethod
    def _configured_count(
        direction: IODirection,
        signal_type: IOSignalType,
        nominal_count: int,
        engineering_ranges: Mapping[str, EngineeringRangeEvidence],
    ) -> int | None:
        """Count configured analogue members; digital points use capacity."""

        if signal_type is IOSignalType.DIGITAL:
            return nominal_count
        prefix = "i." if direction is IODirection.INPUT else "o."
        configured_count = sum(
            1 for key in engineering_ranges if key.startswith(prefix)
        )
        return configured_count or None


DEFAULT_CAPABILITY_PROVIDERS: tuple[ModuleCapabilityProvider, ...] = (
    Rockwell1756CatalogCapabilityProvider(),
)


def infer_module_capability(
    module: CapturedSection,
    identity: Identity,
    engineering_ranges: Mapping[str, EngineeringRangeEvidence],
    providers: Sequence[ModuleCapabilityProvider] = DEFAULT_CAPABILITY_PROVIDERS,
) -> ModuleCapability | None:
    """Return the first capability supported by the configured providers."""

    for provider in providers:
        capability = provider.infer(module, identity, engineering_ranges)
        if capability is not None:
            return capability
    return None
