"""Markdown rendering for CODESYS module-service equivalence evidence."""

from __future__ import annotations

from twinforge.ir import IRControllerObjectIntent

from .codesys_module_services import (
    CODESYSModuleProfile,
    classify_codesys_module_service,
)


_ROCKWELL_INTENT_LABELS = {
    IRControllerObjectIntent.INSTANCE_IDENTITY: "Module instance",
    IRControllerObjectIntent.CONNECTION_STATUS: "`EntryStatus`",
    IRControllerObjectIntent.FAULT_CODE: "`FaultCode`",
    IRControllerObjectIntent.FAULT_INFORMATION: "`FaultInfo`",
    IRControllerObjectIntent.OPERATING_MODE: "Numeric `Mode`",
    IRControllerObjectIntent.SET_INHIBITED: "Set inhibited",
    IRControllerObjectIntent.SOURCE_SPECIFIC: (
        "Other source-specific attributes"
    ),
}

_CODESYS_EVIDENCE_LABELS = {
    IRControllerObjectIntent.INSTANCE_IDENTITY: "`GetDeviceInfo()` identity",
    IRControllerObjectIntent.CONNECTION_STATUS: (
        "`eState` and `GetDeviceState()`"
    ),
    IRControllerObjectIntent.FAULT_CODE: "CAA Device Diagnosis error",
    IRControllerObjectIntent.FAULT_INFORMATION: (
        "Diagnostic availability and text"
    ),
    IRControllerObjectIntent.OPERATING_MODE: "`Enable` and device state",
    IRControllerObjectIntent.SET_INHIBITED: (
        "`Enable`, capability check, and `DED.Reconfigure`"
    ),
    IRControllerObjectIntent.SOURCE_SPECIFIC: "None established",
}


class CodesysModuleEquivalenceMarkdownExporter:
    """Render the classifier as deterministic, evidence-aware Markdown."""

    def table(
        self,
        profile: CODESYSModuleProfile = (
            CODESYSModuleProfile.ETHERNET_IP_REMOTE_ADAPTER
        ),
    ) -> str:
        """Return the canonical equivalence table for ``profile``."""

        lines = [
            "| Rockwell intent | CODESYS evidence | Support | Equivalence |",
            "| --- | --- | --- | --- |",
        ]
        for intent in IRControllerObjectIntent:
            capability = classify_codesys_module_service(intent, profile)
            lines.append(
                f"| {_ROCKWELL_INTENT_LABELS[intent]} "
                f"| {_CODESYS_EVIDENCE_LABELS[intent]} "
                f"| {_display(capability.support.value)} "
                f"| {_display(capability.equivalence.value)} |"
            )
        return "\n".join(lines)

    def export(
        self,
        profile: CODESYSModuleProfile = (
            CODESYSModuleProfile.ETHERNET_IP_REMOTE_ADAPTER
        ),
    ) -> str:
        """Return a standalone equivalence report."""

        return "\n".join(
            (
                "# CODESYS module-service equivalence",
                "",
                (
                    f"Profile: `{profile.value}`. Support and semantic "
                    "equivalence are classified independently."
                ),
                "",
                self.table(profile),
                "",
                (
                    "No normalized mapping should be interpreted as a raw "
                    "Rockwell controller-object value."
                ),
                "",
            )
        )


def _display(value: str) -> str:
    """Convert a stable enum value into a readable table label."""

    return value.replace("_", " ").capitalize()
