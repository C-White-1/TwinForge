"""Evidence-based portability analysis for reusable controller instructions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from twinforge.model import AddOnInstruction, Controller

from .behaviour import PLCopenBehaviourAssessment, assess_plcopen_behaviour
from .runtime import RuntimeCapability, RuntimeRequirement


_CALL = re.compile(r"(?<![\w.])([A-Za-z_]\w*)\s*\(")
_GSV_OBJECT = re.compile(r"\bGSV\s*\(\s*([^,)]*)", re.IGNORECASE)
_CONTROL_WORDS = {"IF", "ELSIF", "FOR", "WHILE", "CASE"}
_ROCKWELL_SERVICES = {"GSV", "SSV", "MSG"}
_ROCKWELL_DATA_TYPES = {"MESSAGE", "MODULE"}
_SERVICE_CAPABILITIES = {
    "GSV": RuntimeCapability.CONTROLLER_OBJECT_READ,
    "MSG": RuntimeCapability.EXPLICIT_MESSAGING,
    "SSV": RuntimeCapability.CONTROLLER_OBJECT_WRITE,
}
_DATA_TYPE_CAPABILITIES = {
    "MESSAGE": RuntimeCapability.EXPLICIT_MESSAGING,
    "MODULE": RuntimeCapability.MODULE_REFERENCE,
}
_LIFECYCLE_CAPABILITIES = {
    "prescan": RuntimeCapability.PRESCAN_HOOK,
    "postscan": RuntimeCapability.POSTSCAN_HOOK,
    "enable_in_false": RuntimeCapability.DISABLED_SCAN_HOOK,
}


class AOIPortability(str, Enum):
    """Conservative disposition for an AOI conversion candidate."""

    PORTABLE_CANDIDATE = "portable_candidate"
    ADAPTER_REQUIRED = "adapter_required"
    MANUAL_REVIEW = "manual_review"


class RecommendedPOU(str, Enum):
    """Closest generic IEC 61131-3 implementation shape."""

    FUNCTION = "function"
    FUNCTION_BLOCK = "function_block"


@dataclass(frozen=True)
class AOIPortabilityFinding:
    """Portability evidence collected for one Add-On Instruction."""

    name: str
    disposition: AOIPortability
    recommended_pou: RecommendedPOU
    plcopen_behaviour: PLCopenBehaviourAssessment
    stateful: bool
    lifecycle_hooks: tuple[str, ...]
    dependencies: tuple[str, ...]
    unresolved_dependencies: tuple[str, ...]
    referenced_data_types: tuple[str, ...]
    structured_text_calls: tuple[str, ...]
    rockwell_services: tuple[str, ...]
    rockwell_data_types: tuple[str, ...]
    runtime_requirements: tuple[RuntimeRequirement, ...]
    unanalyzed_routines: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class AOIPortabilityReport:
    """Portability findings for all AOIs in one controller."""

    controller_name: str
    findings: tuple[AOIPortabilityFinding, ...]

    def render_text(self) -> str:
        """Render a deterministic, human-readable evidence report."""

        lines = [
            f"AOI portability analysis: {self.controller_name}",
            "",
            "Disposition is evidence-based and does not prove semantic equivalence.",
        ]
        if not self.findings:
            lines.extend(["", "No Add-On Instructions were captured."])
            return "\n".join(lines) + "\n"

        for finding in self.findings:
            lines.extend(
                [
                    "",
                    f"Instruction: {finding.name}",
                    f"  Disposition: {finding.disposition.value}",
                    f"  Recommended IEC POU: {finding.recommended_pou.value}",
                    "  PLCopen behaviour: "
                    f"{finding.plcopen_behaviour.model.value} "
                    f"({finding.plcopen_behaviour.match.value})",
                    "  Common Behaviour wrapper: "
                    f"{_yes_no(finding.plcopen_behaviour.wrapper_recommended)}",
                    "  Missing behaviour parameters: "
                    f"{_items(finding.plcopen_behaviour.missing_parameters)}",
                    f"  Retained local state: {_yes_no(finding.stateful)}",
                    f"  Lifecycle hooks: {_items(finding.lifecycle_hooks)}",
                    f"  Dependencies: {_items(finding.dependencies)}",
                    "  Unresolved dependencies: "
                    f"{_items(finding.unresolved_dependencies)}",
                    "  Referenced data types: "
                    f"{_items(finding.referenced_data_types)}",
                    f"  Structured Text calls: "
                    f"{_items(finding.structured_text_calls)}",
                    f"  Rockwell services: {_items(finding.rockwell_services)}",
                    "  Rockwell data types: "
                    f"{_items(finding.rockwell_data_types)}",
                    "  Runtime capabilities: "
                    f"{_requirements(finding.runtime_requirements)}",
                    f"  Unanalyzed routines: "
                    f"{_items(finding.unanalyzed_routines)}",
                    f"  Reasons: {_items(finding.reasons)}",
                ]
            )
        return "\n".join(lines) + "\n"


def analyze_aoi_portability(controller: Controller) -> AOIPortabilityReport:
    """Assess AOIs using only evidence preserved in the neutral model."""

    findings = tuple(
        _analyze_instruction(instruction)
        for instruction in sorted(
            controller.add_on_instructions.values(),
            key=lambda item: item.name.casefold(),
        )
    )
    return AOIPortabilityReport(controller.name, findings)


def extract_structured_text_calls(text: str) -> tuple[str, ...]:
    """Return distinct call-like identifiers found in Structured Text."""

    calls = {
        match.group(1)
        for match in _CALL.finditer(_without_st_comments(text))
        if match.group(1).upper() not in _CONTROL_WORDS
    }
    return tuple(sorted(calls, key=str.casefold))


def _analyze_instruction(
    instruction: AddOnInstruction,
) -> AOIPortabilityFinding:
    lifecycle = _lifecycle_hooks(instruction)
    behaviour = assess_plcopen_behaviour(instruction)
    data_types = {
        item.data_type
        for item in (*instruction.parameters.values(), *instruction.local_tags.values())
        if item.data_type
    }
    calls: set[str] = set()
    unanalyzed: list[str] = []
    for routine in instruction.routines.values():
        if (routine.language or "").lower() in {"st", "structuredtext"}:
            calls.update(extract_structured_text_calls(routine.structured_text))
        else:
            unanalyzed.append(
                f"{routine.name} ({routine.language or 'unknown language'})"
            )

    rockwell_services = tuple(
        sorted(
            (call for call in calls if call.upper() in _ROCKWELL_SERVICES),
            key=str.casefold,
        )
    )
    rockwell_types = tuple(
        sorted(
            (
                data_type
                for data_type in data_types
                if data_type.upper() in _ROCKWELL_DATA_TYPES
            ),
            key=str.casefold,
        )
    )
    gsv_objects = _gsv_objects(instruction)
    runtime_requirements = _runtime_requirements(
        lifecycle, rockwell_services, rockwell_types, gsv_objects
    )
    dependencies = tuple(
        sorted(
            (
                f"{dependency.dependency_type}:{dependency.name}"
                for dependency in instruction.dependencies
            ),
            key=str.casefold,
        )
    )
    unresolved = tuple(
        sorted(
            (
                f"{dependency.dependency_type}:{dependency.name}"
                for dependency in instruction.dependencies
                if dependency.target is None
            ),
            key=str.casefold,
        )
    )

    reasons: list[str] = []
    if rockwell_services:
        reasons.append("Rockwell controller services require a target adapter")
    if rockwell_types:
        reasons.append("Rockwell-specific data types require a target adapter")
    if lifecycle:
        reasons.append("AOI lifecycle hooks require target-runtime integration")
    if unresolved:
        reasons.append("one or more declared dependencies are unresolved")
    if unanalyzed:
        reasons.append("one or more routine languages were not analyzed")
    if not instruction.routines:
        reasons.append("no implementation routine was captured")

    if unanalyzed or unresolved or not instruction.routines:
        disposition = AOIPortability.MANUAL_REVIEW
    elif runtime_requirements:
        disposition = AOIPortability.ADAPTER_REQUIRED
    else:
        disposition = AOIPortability.PORTABLE_CANDIDATE
        reasons.append("no known Rockwell-only dependency was detected")

    stateful = bool(instruction.local_tags)
    recommended = (
        RecommendedPOU.FUNCTION_BLOCK
        if stateful or lifecycle
        else RecommendedPOU.FUNCTION
    )
    return AOIPortabilityFinding(
        name=instruction.name,
        disposition=disposition,
        recommended_pou=recommended,
        plcopen_behaviour=behaviour,
        stateful=stateful,
        lifecycle_hooks=lifecycle,
        dependencies=dependencies,
        unresolved_dependencies=unresolved,
        referenced_data_types=tuple(sorted(data_types, key=str.casefold)),
        structured_text_calls=tuple(sorted(calls, key=str.casefold)),
        rockwell_services=rockwell_services,
        rockwell_data_types=rockwell_types,
        runtime_requirements=runtime_requirements,
        unanalyzed_routines=tuple(sorted(unanalyzed, key=str.casefold)),
        reasons=tuple(reasons),
    )


def _lifecycle_hooks(instruction: AddOnInstruction) -> tuple[str, ...]:
    hooks: list[str] = []
    if instruction.execute_prescan:
        hooks.append("prescan")
    if instruction.execute_postscan:
        hooks.append("postscan")
    if instruction.execute_enable_in_false:
        hooks.append("enable_in_false")
    return tuple(hooks)


def _without_st_comments(text: str) -> str:
    text = re.sub(r"\(\*.*?\*\)", " ", text, flags=re.DOTALL)
    return re.sub(r"//.*?$", " ", text, flags=re.MULTILINE)


def _runtime_requirements(
    lifecycle: tuple[str, ...],
    services: tuple[str, ...],
    data_types: tuple[str, ...],
    gsv_objects: tuple[str, ...],
) -> tuple[RuntimeRequirement, ...]:
    evidence: dict[RuntimeCapability, set[str]] = {}
    for service in services:
        if service.upper() == "GSV" and gsv_objects:
            for object_name in gsv_objects:
                capability = (
                    RuntimeCapability.WALL_CLOCK_READ
                    if _normalized_operand(object_name) == "wallclocktime"
                    else RuntimeCapability.CONTROLLER_OBJECT_READ
                )
                evidence.setdefault(capability, set()).add(
                    f"service:GSV({object_name})"
                )
        else:
            capability = _SERVICE_CAPABILITIES[service.upper()]
            evidence.setdefault(capability, set()).add(f"service:{service}")
    for data_type in data_types:
        capability = _DATA_TYPE_CAPABILITIES[data_type.upper()]
        evidence.setdefault(capability, set()).add(f"data_type:{data_type}")
    for hook in lifecycle:
        capability = _LIFECYCLE_CAPABILITIES[hook]
        evidence.setdefault(capability, set()).add(f"lifecycle:{hook}")
    return tuple(
        RuntimeRequirement(
            capability=capability,
            evidence=tuple(sorted(items, key=str.casefold)),
        )
        for capability, items in sorted(
            evidence.items(), key=lambda item: item[0].value
        )
    )


def _gsv_objects(
    instruction: AddOnInstruction,
) -> tuple[str, ...]:
    objects = {
        match.group(1).strip()
        for routine in instruction.routines.values()
        if (routine.language or "").lower() in {"st", "structuredtext"}
        for match in _GSV_OBJECT.finditer(
            _without_st_comments(routine.structured_text)
        )
        if match.group(1).strip()
    }
    return tuple(sorted(objects, key=str.casefold))


def _normalized_operand(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _items(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"


def _requirements(values: tuple[RuntimeRequirement, ...]) -> str:
    if not values:
        return "none"
    return ", ".join(
        f"{item.capability.value} [{'; '.join(item.evidence)}]"
        for item in values
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
