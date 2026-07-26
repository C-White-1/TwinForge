"""PlantUML visualization of AOI dependencies and runtime boundaries."""

from __future__ import annotations

import hashlib
import re

from twinforge.analysis import AOIPortability, AOIPortabilityReport


class AOIPlantUMLExporter:
    """Render a deterministic PlantUML component diagram from analysis data."""

    def export(self, report: AOIPortabilityReport) -> str:
        """Return PlantUML source without requiring a PlantUML installation."""

        lines = [
            f"@startuml {_diagram_name(report.controller_name)}",
            f"title {_quote(f'{report.controller_name} AOI portability')}",
            "left to right direction",
            "skinparam componentStyle rectangle",
            "skinparam shadowing false",
            "",
            "legend right",
            "  |= Colour |= Meaning |",
            "  |<#D5F5E3>| Portable candidate |",
            "  |<#FCF3CF>| Target adapter required |",
            "  |<#F5B7B1>| Manual review |",
            "endlegend",
            "",
            'package "Add-On Instructions" {',
        ]

        finding_names = {finding.name for finding in report.findings}
        for finding in report.findings:
            label = (
                f"{finding.name}\\n"
                f"{finding.recommended_pou.value}\\n"
                f"{finding.disposition.value}\\n"
                "PLCopen CBM: "
                f"{finding.plcopen_behaviour.model.value}/"
                f"{finding.plcopen_behaviour.match.value}"
            )
            lines.append(
                f"  component {_quote(label)} as {_id('aoi', finding.name)} "
                f"{_colour(finding.disposition)}"
            )
        lines.append("}")

        datatypes = sorted(
            {
                name
                for finding in report.findings
                for dependency_type, name in map(
                    _dependency_parts, finding.dependencies
                )
                if dependency_type.casefold() == "datatype"
            },
            key=str.casefold,
        )
        if datatypes:
            lines.extend(["", 'package "Referenced data types" {'])
            for name in datatypes:
                lines.append(
                    f"  artifact {_quote(name)} as {_id('datatype', name)}"
                )
            lines.append("}")

        capabilities = sorted(
            {
                requirement.capability
                for finding in report.findings
                for requirement in finding.runtime_requirements
            },
            key=lambda item: item.value,
        )
        if capabilities:
            lines.extend(["", 'package "Target runtime adapter boundary" {'])
            for capability in capabilities:
                lines.append(
                    f"  interface {_quote(_display(capability.value))} "
                    f"as {_id('capability', capability.value)}"
                )
            lines.append("}")

        behaviour_models = sorted(
            {
                finding.plcopen_behaviour.model
                for finding in report.findings
                if finding.plcopen_behaviour.wrapper_recommended
            },
            key=lambda item: item.value,
        )
        if behaviour_models:
            lines.extend(["", 'package "PLCopen Common Behaviour" {'])
            for model in behaviour_models:
                lines.append(
                    f"  interface {_quote(_display(model.value))} "
                    f"as {_id('behaviour', model.value)}"
                )
            lines.append("}")

        lines.append("")
        for finding in report.findings:
            source = _id("aoi", finding.name)
            for dependency in finding.dependencies:
                dependency_type, name = _dependency_parts(dependency)
                if (
                    dependency_type.casefold()
                    == "addoninstructiondefinition"
                    and name in finding_names
                ):
                    lines.append(
                        f"{source} --> {_id('aoi', name)} : uses"
                    )
                elif dependency_type.casefold() == "datatype":
                    lines.append(
                        f"{source} ..> {_id('datatype', name)} : datatype"
                    )
            for requirement in finding.runtime_requirements:
                evidence = "\\n".join(requirement.evidence)
                lines.append(
                    f"{source} --> "
                    f"{_id('capability', requirement.capability.value)} "
                    f": {evidence}"
                )
            if finding.plcopen_behaviour.wrapper_recommended:
                model = finding.plcopen_behaviour.model
                lines.append(
                    f"{source} ..> {_id('behaviour', model.value)} "
                    ": wrapper candidate"
                )

        lines.extend(
            [
                "",
                "note bottom",
                "  Adapter boundaries are inferred from captured evidence.",
                "  They do not prove target-runtime semantic equivalence.",
                "end note",
                "@enduml",
            ]
        )
        return "\n".join(lines) + "\n"


def _id(category: str, value: str) -> str:
    digest = hashlib.sha256(f"{category}:{value}".encode()).hexdigest()[:12]
    return f"{category}_{digest}"


def _diagram_name(controller_name: str) -> str:
    """Return a PlantUML-safe, deterministic diagram identifier."""

    normalized = re.sub(r"[^A-Za-z0-9_]+", "_", controller_name).strip("_")
    if not normalized:
        normalized = "Controller"
    return f"{normalized}_AOI_Portability"


def _quote(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def _dependency_parts(value: str) -> tuple[str, str]:
    dependency_type, separator, name = value.partition(":")
    if not separator:
        return "", value
    return dependency_type, name


def _display(value: str) -> str:
    return value.replace("_", " ").title()


def _colour(disposition: AOIPortability) -> str:
    return {
        AOIPortability.PORTABLE_CANDIDATE: "#D5F5E3",
        AOIPortability.ADAPTER_REQUIRED: "#FCF3CF",
        AOIPortability.MANUAL_REVIEW: "#F5B7B1",
    }[disposition]
