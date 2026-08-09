"""Safe human-readable reporting for structural software inventory."""

from __future__ import annotations

from collections import Counter

from .software_inventory_capture import CipSoftwareInventoryObservation
from .software_inventory_reconciliation import (
    SoftwareInventoryReconciliationResult,
)


def software_inventory_markdown(
    observation: CipSoftwareInventoryObservation,
    reconciliation: SoftwareInventoryReconciliationResult | None = None,
) -> str:
    """Render structural inventory without raw attributes or runtime values."""
    counts = Counter(item.capability.value for item in observation.items)
    lines = [
        "# CIP Software Inventory",
        "",
        f"- Target: `{observation.target.key}`",
        f"- Captured: `{observation.captured_at.isoformat()}`",
        f"- Requests used: {observation.requests_used}",
        "- Runtime values included: no",
        "",
        "## Summary",
        "",
    ]
    for capability in observation.capabilities:
        lines.append(f"- {capability.value}: {counts[capability.value]}")
    lines.extend(["", "## Structural items", ""])
    for item in observation.items:
        parent = f" under `{item.parent}`" if item.parent else ""
        details = []
        if item.data_type is not None:
            details.append(f"data type `{item.data_type}`")
        if item.language is not None:
            details.append(f"language `{item.language}`")
        suffix = f" ({', '.join(details)})" if details else ""
        lines.append(
            f"- {item.capability.value}: `{item.name}`{parent}{suffix}"
        )
    if not observation.items:
        lines.append("- None observed.")

    if reconciliation is not None:
        lines.extend(["", "## L5X reconciliation", ""])
        lines.append(f"- Binding: `{reconciliation.binding_key}`")
        for comparison in reconciliation.comparisons:
            lines.append(f"- {comparison.status.value}: `{comparison.key}`")
        for key in reconciliation.configured_only:
            lines.append(f"- configured only: `{key}`")
        for key in reconciliation.discovered_only:
            lines.append(f"- discovered only: `{key}`")
        if (
            not reconciliation.comparisons
            and not reconciliation.configured_only
            and not reconciliation.discovered_only
        ):
            lines.append("- No structural differences observed.")

    lines.extend(
        [
            "",
            "Raw attributes and CIP object payloads are omitted from this report.",
            "",
        ]
    )
    return "\n".join(lines)
