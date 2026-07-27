"""Vendor-neutral device-parameter and setpoint reporting."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from twinforge.model import Device, DeviceParameterDefinition


@dataclass(frozen=True)
class ParameterReportEntry:
    """One observed device parameter enriched with available semantics."""

    number: int
    code: str | None
    name: str | None
    group: str | None
    purpose: str | None
    engineering_unit: str | None
    minimum: str | None
    maximum: str | None
    default: str | None
    resolution: str | None
    observed_read: bool
    observed_write: bool
    read_only: bool | None
    change_requires_stop: bool | None
    configured_value: str | None = None
    configured_value_label: str | None = None
    configured_value_assessment: str | None = None
    configured_value_source: str | None = None
    configuration_note: str | None = None
    runtime_value: str | None = None
    runtime_value_source: str | None = None
    reference: str | None = None
    evidence: tuple[str, ...] = ()
    advisory_codes: tuple[str, ...] = ()
    advisory_severity: str | None = None
    advisory_summaries: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParameterSetpointReport:
    """Deterministic parameter report for one assembled physical device."""

    device_name: str
    entries: tuple[ParameterReportEntry, ...]


def build_parameter_setpoint_report(device: Device) -> ParameterSetpointReport:
    """Combine observed access and catalogue facts without inventing values."""

    entries: list[ParameterReportEntry] = []
    for observed in sorted(
        device.observed_parameters,
        key=lambda item: item.number,
    ):
        definition = observed.definition
        entries.append(
            ParameterReportEntry(
                number=observed.number,
                code=(
                    observed.code
                    or (definition.code if definition is not None else None)
                ),
                name=(
                    observed.display_name
                    or (definition.name if definition is not None else None)
                ),
                group=(
                    observed.group_name
                    or observed.group_prefix
                    or (
                        definition.group_name
                        if definition is not None
                        else None
                    )
                ),
                purpose=(
                    definition.description
                    if definition is not None
                    else None
                ),
                engineering_unit=(
                    definition.engineering_unit
                    if definition is not None
                    else None
                ),
                minimum=(
                    definition.minimum if definition is not None else None
                ),
                maximum=(
                    definition.maximum if definition is not None else None
                ),
                default=(
                    definition.default if definition is not None else None
                ),
                resolution=(
                    definition.resolution if definition is not None else None
                ),
                observed_read=observed.observed_read,
                observed_write=observed.observed_write,
                read_only=(
                    definition.read_only if definition is not None else None
                ),
                change_requires_stop=(
                    definition.change_requires_stop
                    if definition is not None
                    else None
                ),
                configured_value=(
                    observed.configured_value.lexical_value
                    if observed.configured_value is not None
                    else None
                ),
                configured_value_label=_configured_value_label(
                    observed.configured_value.lexical_value
                    if observed.configured_value is not None
                    else None,
                    definition,
                ),
                configured_value_assessment=_configured_value_assessment(
                    observed.configured_value.lexical_value
                    if observed.configured_value is not None
                    else None,
                    definition,
                ),
                configured_value_source=(
                    observed.configured_value.source
                    if observed.configured_value is not None
                    else None
                ),
                configuration_note=observed.configuration_note,
                runtime_value=(
                    observed.runtime_value.lexical_value
                    if observed.runtime_value is not None
                    else None
                ),
                runtime_value_source=(
                    observed.runtime_value.source
                    if observed.runtime_value is not None
                    else None
                ),
                reference=(
                    observed.reference
                    or (
                        definition.reference
                        if definition is not None
                        else None
                    )
                ),
                evidence=(
                    observed.evidence
                    + (
                        observed.configured_value.evidence
                        if observed.configured_value is not None
                        else ()
                    )
                ),
                advisory_codes=tuple(
                    advisory.code for advisory in observed.advisories
                ),
                advisory_severity=_highest_advisory_severity(
                    tuple(
                        advisory.severity.value
                        for advisory in observed.advisories
                    )
                ),
                advisory_summaries=tuple(
                    advisory.summary for advisory in observed.advisories
                ),
            )
        )
    return ParameterSetpointReport(
        device_name=device.name,
        entries=tuple(entries),
    )


def _configured_value_label(
    lexical_value: str | None,
    definition: DeviceParameterDefinition | None,
) -> str | None:
    """Resolve an enumerated option without changing the source value."""

    if lexical_value is None or definition is None:
        return None
    for option in definition.options:
        if _equivalent_value(lexical_value, option.value):
            return option.label
    return None


def _equivalent_value(left: str, right: str) -> bool:
    if left.strip().casefold() == right.strip().casefold():
        return True
    try:
        return Decimal(left.strip()) == Decimal(right.strip())
    except InvalidOperation:
        return False


def _configured_value_assessment(
    lexical_value: str | None,
    definition: DeviceParameterDefinition | None,
) -> str | None:
    """Assess only constraints that are explicit and mechanically decidable."""

    if lexical_value is None:
        return None
    if definition is None:
        return "No curated semantics"
    if definition.options:
        if _configured_value_label(lexical_value, definition) is not None:
            return "Documented option"
        return "Undocumented option"
    value = _decimal(lexical_value)
    minimum = _decimal(definition.minimum)
    maximum = _decimal(definition.maximum)
    if value is None or minimum is None or maximum is None:
        return "Not automatically verifiable"
    if minimum <= value <= maximum:
        return "Within documented range"
    return "Outside documented range"


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value.strip())
    except InvalidOperation:
        return None


def _highest_advisory_severity(
    severities: tuple[str, ...],
) -> str | None:
    order = {"Low": 1, "Medium": 2, "High": 3}
    if not severities:
        return None
    return max(severities, key=lambda item: order[item])
