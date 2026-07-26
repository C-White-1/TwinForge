"""Conservative detection of PLCopen Common Behaviour Model signatures."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from twinforge.model import AddOnInstruction, AddOnInstructionParameter


class PLCopenBehaviourModel(str, Enum):
    """PLCopen function-block control model detected from an AOI interface."""

    NONE = "none"
    EDGE_TRIGGERED = "edge_triggered"
    LEVEL_CONTROLLED = "level_controlled"
    AMBIGUOUS = "ambiguous"


class BehaviourMatch(str, Enum):
    """Strength of the interface match to the selected behaviour model."""

    NONE = "none"
    PARTIAL = "partial"
    COMPLETE = "complete"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class BehaviourParameterMapping:
    """Mapping from a PLCopen interface role to a captured AOI parameter."""

    standard_name: str
    source_name: str


@dataclass(frozen=True)
class PLCopenBehaviourAssessment:
    """Evidence and recommendation for one AOI behaviour wrapper."""

    model: PLCopenBehaviourModel
    match: BehaviourMatch
    wrapper_recommended: bool
    parameter_mapping: tuple[BehaviourParameterMapping, ...]
    missing_parameters: tuple[str, ...]
    extensions: tuple[str, ...]
    evidence: tuple[str, ...]


_EDGE_INTERFACE = {
    "Execute": ("execute",),
    "Done": ("done",),
    "Busy": ("busy",),
    "Error": ("error",),
    "ErrorID": ("errorid",),
}
_LEVEL_INTERFACE = {
    "Enable": ("enable",),
    "Valid": ("valid",),
    "Busy": ("busy",),
    "Error": ("error",),
    "ErrorID": ("errorid",),
}
_EXTENSIONS = {
    "Abort": ("abort",),
    "Aborted": ("aborted",),
    "TimeOut": ("timeout",),
    "TimeLimit": ("timelimit",),
}


def assess_plcopen_behaviour(
    instruction: AddOnInstruction,
) -> PLCopenBehaviourAssessment:
    """Detect only explicit PLCopen-style Execute or Enable signatures."""

    parameters = {
        _normalized_name(parameter.name): parameter
        for parameter in instruction.parameters.values()
    }
    has_execute = _find(parameters, _EDGE_INTERFACE["Execute"]) is not None
    has_enable = _find(parameters, _LEVEL_INTERFACE["Enable"]) is not None

    if has_execute and has_enable:
        return PLCopenBehaviourAssessment(
            model=PLCopenBehaviourModel.AMBIGUOUS,
            match=BehaviourMatch.AMBIGUOUS,
            wrapper_recommended=False,
            parameter_mapping=(),
            missing_parameters=(),
            extensions=(),
            evidence=(
                "both Execute and Enable control inputs were captured",
            ),
        )
    if has_execute:
        return _assess_interface(
            PLCopenBehaviourModel.EDGE_TRIGGERED,
            _EDGE_INTERFACE,
            parameters,
        )
    if has_enable:
        return _assess_interface(
            PLCopenBehaviourModel.LEVEL_CONTROLLED,
            _LEVEL_INTERFACE,
            parameters,
        )
    return PLCopenBehaviourAssessment(
        model=PLCopenBehaviourModel.NONE,
        match=BehaviourMatch.NONE,
        wrapper_recommended=False,
        parameter_mapping=(),
        missing_parameters=(),
        extensions=(),
        evidence=(
            "no explicit Execute/xExecute or Enable/xEnable input was captured",
        ),
    )


def _assess_interface(
    model: PLCopenBehaviourModel,
    interface: dict[str, tuple[str, ...]],
    parameters: dict[str, AddOnInstructionParameter],
) -> PLCopenBehaviourAssessment:
    mappings: list[BehaviourParameterMapping] = []
    missing: list[str] = []
    for standard_name, aliases in interface.items():
        parameter = _find(parameters, aliases)
        if parameter is None:
            missing.append(standard_name)
        else:
            source_name = parameter.name
            mappings.append(
                BehaviourParameterMapping(standard_name, source_name)
            )

    extensions = tuple(
        standard_name
        for standard_name, aliases in _EXTENSIONS.items()
        if _find(parameters, aliases) is not None
    )
    complete = not missing and _usages_are_compatible(mappings, parameters)
    evidence = [
        f"captured {mapping.source_name} as PLCopen {mapping.standard_name}"
        for mapping in mappings
    ]
    if missing:
        evidence.append(
            "missing required interface members: " + ", ".join(missing)
        )
    if not complete and not missing:
        evidence.append("one or more parameter directions are incompatible")
    return PLCopenBehaviourAssessment(
        model=model,
        match=BehaviourMatch.COMPLETE if complete else BehaviourMatch.PARTIAL,
        wrapper_recommended=complete,
        parameter_mapping=tuple(mappings),
        missing_parameters=tuple(missing),
        extensions=extensions,
        evidence=tuple(evidence),
    )


def _find(
    parameters: dict[str, AddOnInstructionParameter],
    aliases: tuple[str, ...],
) -> AddOnInstructionParameter | None:
    for alias in aliases:
        for candidate in (alias, f"x{alias}", f"i{alias}", f"udi{alias}"):
            parameter = parameters.get(candidate)
            if parameter is not None:
                return parameter
    return None


def _usages_are_compatible(
    mappings: list[BehaviourParameterMapping],
    parameters: dict[str, AddOnInstructionParameter],
) -> bool:
    input_roles = {"Execute", "Enable", "Abort", "TimeOut", "TimeLimit"}
    for mapping in mappings:
        parameter = parameters[_normalized_name(mapping.source_name)]
        usage = (parameter.usage or "").casefold()
        expected = "input" if mapping.standard_name in input_roles else "output"
        if usage != expected:
            return False
    return True


def _normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())
