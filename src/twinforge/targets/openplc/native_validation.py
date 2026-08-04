"""Validate native OpenPLC located-variable and telemetry requests."""

from __future__ import annotations

from collections.abc import Mapping
import re

from twinforge.exporters.plcopen_operands import PLCopenOperandPlan
from twinforge.model import Program

from .native_errors import OpenPLCNativeUnsupportedError


_EVIDENCED_BOOL_LOCATION = re.compile(r"%[IQ]X\d+\.\d+")
_EVIDENCED_DINT_MEMORY_LOCATION = re.compile(r"%MD\d+")


def validate_locations(program: Program, locations: Mapping[str, str]) -> None:
    """Validate local Boolean locations against the captured native format."""

    unknown = sorted(set(locations).difference(program.tags))
    if unknown:
        raise OpenPLCNativeUnsupportedError(
            "locations reference unknown local variables: " + ", ".join(unknown)
        )
    unsupported = [
        f"{name}={location}"
        for name, location in locations.items()
        if _EVIDENCED_BOOL_LOCATION.fullmatch(location) is None
    ]
    if unsupported:
        raise OpenPLCNativeUnsupportedError(
            "only evidenced %IX/%QX byte.bit BOOL locations are supported: "
            + ", ".join(unsupported)
        )


def validate_timer_elapsed_locations(
    operands: PLCopenOperandPlan,
    locations: Mapping[str, str],
    timer_types: Mapping[str, str],
) -> None:
    """Validate elapsed-time telemetry names, addresses, and proven types."""

    unknown = sorted(set(locations).difference(operands.timers))
    if unknown:
        raise OpenPLCNativeUnsupportedError(
            "elapsed locations reference unknown TIMER tags: " + ", ".join(unknown)
        )
    unsupported = [
        f"{name}={location}"
        for name, location in locations.items()
        if _EVIDENCED_DINT_MEMORY_LOCATION.fullmatch(location) is None
    ]
    if unsupported:
        raise OpenPLCNativeUnsupportedError(
            "timer elapsed telemetry requires evidenced %MD DINT locations: "
            + ", ".join(unsupported)
        )
    unevidenced = [name for name in locations if timer_types.get(name) != "TON"]
    if unevidenced:
        raise OpenPLCNativeUnsupportedError(
            "elapsed telemetry is currently runtime-evidenced only for TON: "
            + ", ".join(unevidenced)
        )


def validate_counter_accumulator_locations(
    counter_names: set[str],
    locations: Mapping[str, str],
) -> None:
    """Validate optional COUNTER accumulator telemetry locations."""

    unknown = sorted(set(locations).difference(counter_names))
    if unknown:
        raise OpenPLCNativeUnsupportedError(
            "accumulator locations reference unknown COUNTER tags: "
            + ", ".join(unknown)
        )
    unsupported = [
        f"{name}={location}"
        for name, location in locations.items()
        if _EVIDENCED_DINT_MEMORY_LOCATION.fullmatch(location) is None
    ]
    if unsupported:
        raise OpenPLCNativeUnsupportedError(
            "counter accumulator telemetry requires evidenced %MD DINT locations: "
            + ", ".join(unsupported)
        )


def validate_counter_status_locations(
    counter_names: set[str],
    locations: Mapping[str, Mapping[str, str]],
) -> None:
    """Validate optional OV and UN Boolean telemetry locations."""

    unknown = sorted(set(locations).difference(counter_names))
    if unknown:
        raise OpenPLCNativeUnsupportedError(
            "status locations reference counters without shared state: "
            + ", ".join(unknown)
        )
    unsupported_members = sorted(
        f"{counter}.{member}"
        for counter, members in locations.items()
        for member in members
        if member not in {"OV", "UN"}
    )
    if unsupported_members:
        raise OpenPLCNativeUnsupportedError(
            "only OV/UN counter status telemetry is evidenced: "
            + ", ".join(unsupported_members)
        )
    unsupported_locations = sorted(
        f"{counter}.{member}={location}"
        for counter, members in locations.items()
        for member, location in members.items()
        if _EVIDENCED_BOOL_LOCATION.fullmatch(location) is None
    )
    if unsupported_locations:
        raise OpenPLCNativeUnsupportedError(
            "counter status telemetry requires evidenced %IX/%QX locations: "
            + ", ".join(unsupported_locations)
        )
