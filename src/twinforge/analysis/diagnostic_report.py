"""Build evidence-backed device diagnostic and fault reports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from twinforge.model import AddOnInstruction, Device, ObservedParameterAccess


@dataclass(frozen=True)
class DiagnosticIndicator:
    """One live diagnostic indication exposed by controller logic."""

    layer: str
    name: str
    source: str | None
    meaning: str | None
    visible: bool | None


@dataclass(frozen=True)
class DiagnosticPolicy:
    """One observed configuration governing abnormal behavior."""

    code: str
    name: str
    purpose: str | None
    configured_value: str | None
    configured_label: str | None
    source: str | None


@dataclass(frozen=True)
class FaultHistoryEntry:
    """Parameter-backed values captured for one historical fault position."""

    position: int
    code_parameter: str | None = None
    frequency_parameter: str | None = None
    current_parameter: str | None = None
    bus_voltage_parameter: str | None = None


@dataclass(frozen=True)
class DiagnosticCommand:
    """One command path that changes fault or reset state."""

    name: str
    source: str | None
    effect: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class DeviceDiagnosticReport:
    """Separated live, historical, policy, and command evidence."""

    device_name: str
    implementation_name: str
    indicators: tuple[DiagnosticIndicator, ...]
    policies: tuple[DiagnosticPolicy, ...]
    fault_history: tuple[FaultHistoryEntry, ...]
    commands: tuple[DiagnosticCommand, ...]
    limitations: tuple[str, ...]


def build_device_diagnostic_report(
    device: Device,
    implementation: AddOnInstruction,
    *,
    supporting_implementations: Iterable[AddOnInstruction] = (),
) -> DeviceDiagnosticReport:
    """Build a neutral report without treating offline values as runtime data."""

    implementations = (implementation, *tuple(supporting_implementations))
    return DeviceDiagnosticReport(
        device_name=device.name,
        implementation_name=implementation.name,
        indicators=_indicators(implementations),
        policies=_policies(device.observed_parameters),
        fault_history=_fault_history(device.observed_parameters),
        commands=_commands(implementation),
        limitations=(
            "No online drive values were supplied; active fault codes and "
            "history contents are therefore unavailable.",
            "Logix module FaultCode and FaultInfo are controller-module "
            "diagnostics, not PowerFlex drive fault-history codes.",
            "Explicit-message ER status proves a message failure occurred but "
            "the AOI does not expose a decoded user-facing error catalogue.",
            "The commented F661–F670 fault-status snapshot requests are not "
            "active observations and are not reported as available values.",
            "The AOI exposes fault-code aliases Val_Fault01 through "
            "Val_Fault10; frequency, current, and DC-bus snapshots remain "
            "inside Local.Params rather than separate AOI output parameters.",
        ),
    )


def _indicators(
    implementations: tuple[AddOnInstruction, ...],
) -> tuple[DiagnosticIndicator, ...]:
    concepts = {
        "sts_fault": ("drive", "Active drive fault"),
        "sts_commloss": ("communication", "Module connection is disconnected"),
        "sts_connected": ("communication", "Module connection is established"),
        "sts_resetready": (
            "drive",
            "Drive is faulted and the module connection is established",
        ),
        "sts_faulted": ("module", "Controller module object is faulted"),
        "val_faultcode": ("module", "Raw controller module FaultCode"),
        "val_faultinfo": ("module", "Raw controller module FaultInfo"),
    }
    result: list[DiagnosticIndicator] = []
    seen: set[tuple[str, str]] = set()
    for item in implementations:
        for parameter in item.parameters.values():
            concept = concepts.get(parameter.name.casefold())
            if concept is None or (item.name, parameter.name) in seen:
                continue
            layer, meaning = concept
            result.append(
                DiagnosticIndicator(
                    layer=layer,
                    name=f"{item.name}.{parameter.name}",
                    source=parameter.alias_for,
                    meaning=parameter.description or meaning,
                    visible=parameter.visible,
                )
            )
            seen.add((item.name, parameter.name))
    return tuple(result)


def _policies(
    observed: list[ObservedParameterAccess],
) -> tuple[DiagnosticPolicy, ...]:
    result: list[DiagnosticPolicy] = []
    for item in observed:
        definition = item.definition
        if definition is None or definition.code.casefold() not in {
            "c143",
            "c144",
        }:
            continue
        configured = item.configured_value
        value = configured.lexical_value if configured else None
        label = next(
            (
                option.label
                for option in definition.options
                if _numeric_equal(option.value, value)
            ),
            None,
        )
        result.append(
            DiagnosticPolicy(
                code=definition.code,
                name=definition.name,
                purpose=definition.description,
                configured_value=value,
                configured_label=label,
                source=configured.source if configured else None,
            )
        )
    return tuple(result)


def _fault_history(
    observed: list[ObservedParameterAccess],
) -> tuple[FaultHistoryEntry, ...]:
    fields: dict[int, dict[str, str]] = {}
    pattern = re.compile(
        r"^Fault\s*(\d+)\s+(Code|Frequency|Current|DC Bus Voltage)$",
        re.IGNORECASE,
    )
    for item in observed:
        definition = item.definition
        if definition is None:
            continue
        match = pattern.match(definition.name)
        if match is None:
            continue
        position = int(match.group(1))
        field_name = {
            "code": "code_parameter",
            "frequency": "frequency_parameter",
            "current": "current_parameter",
            "dc bus voltage": "bus_voltage_parameter",
        }[match.group(2).casefold()]
        fields.setdefault(position, {})[field_name] = definition.code
    return tuple(
        FaultHistoryEntry(position=position, **values)
        for position, values in sorted(fields.items())
    )


def _commands(
    implementation: AddOnInstruction,
) -> tuple[DiagnosticCommand, ...]:
    evidence = tuple(
        line.strip()
        for routine in implementation.iter_routines()
        for line in routine.structured_text.splitlines()
        if any(
            token in line
            for token in (
                "Local.DataOut.ClearFault",
                "Local.Params.FaultClear.SP",
                "Sts_ResetReady :=",
            )
        )
    )
    reset_sources = tuple(
        parameter.name
        for parameter in implementation.parameters.values()
        if parameter.usage == "Input"
        and re.match(r"^[POMX]Cmd_Reset$", parameter.name)
    )
    clear_sources = tuple(
        parameter.name
        for parameter in implementation.parameters.values()
        if parameter.usage == "Input"
        and parameter.name.endswith("Cmd_ClearFaultBuffer")
    )
    return (
        DiagnosticCommand(
            name="Reset active fault",
            source=", ".join(reset_sources) or None,
            effect="Sets cyclic LogicCommand bit 3 (ClearFault).",
            evidence=tuple(
                item for item in evidence if "DataOut.ClearFault" in item
            ),
        ),
        DiagnosticCommand(
            name="Clear fault-history buffer",
            source=", ".join(clear_sources) or None,
            effect="Requests A551 value 2 through the explicit write path.",
            evidence=tuple(
                item for item in evidence if "FaultClear.SP" in item
            ),
        ),
    )


def _numeric_equal(left: str, right: str | None) -> bool:
    if right is None:
        return False
    try:
        return float(left) == float(right)
    except ValueError:
        return left == right
