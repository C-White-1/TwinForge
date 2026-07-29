"""Inventory unresolved native CODESYS visualization properties."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from twinforge.parsers.codesys_native import CodesysNativeExport


@dataclass(frozen=True)
class CodesysOpaqueProperty:
    """Observed uses of one preserved, unmapped numeric property."""

    property_id: str
    occurrences: int
    element_types: tuple[str, ...]
    sample_values: tuple[str, ...]


def inventory_opaque_visualization_properties(
    document: CodesysNativeExport,
) -> tuple[CodesysOpaqueProperty, ...]:
    """Return a deterministic inventory without assigning guessed meanings."""

    occurrences: dict[str, int] = defaultdict(int)
    element_types: dict[str, set[str]] = defaultdict(set)
    values: dict[str, set[str]] = defaultdict(set)
    for visualization in document.visualizations:
        for element in visualization.elements:
            for property_id, value in element.numeric_properties.items():
                if property_id in element.property_names:
                    continue
                occurrences[property_id] += 1
                element_types[property_id].add(
                    element.element_type or "unknown"
                )
                values[property_id].add(value)
    return tuple(
        CodesysOpaqueProperty(
            property_id=property_id,
            occurrences=count,
            element_types=tuple(sorted(element_types[property_id])),
            sample_values=tuple(sorted(values[property_id]))[:5],
        )
        for property_id, count in sorted(
            occurrences.items(),
            key=lambda item: (-item[1], int(item[0])),
        )
    )
