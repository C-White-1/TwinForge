"""Observed graphical object selectors; grid connectivity remains unspecified."""
from dataclasses import dataclass


@dataclass(frozen=True)
class GraphicalSpec:
    networks: tuple[tuple[str, str], ...] = (("networkLD", "LD"), ("networkFBD", "FBD"))
    containers: frozenset[str] = frozenset({"typeLine", "shortCircuit"})
    objects: tuple[tuple[str, str], ...] = (
        ("FFBBlock", "block"), ("contact", "contact"), ("textBox", "annotation"),
    )
    # These encode grid layout/connectivity. Retain them rather than interpreting
    # them as discarded whitespace or assuming they are executable graph edges.
    layout_nodes: frozenset[str] = frozenset({"emptyLine", "emptyCell", "HLink", "VLink"})
    position: str = "objPosition"
    description: str = "descriptionFFB"
    pins: tuple[tuple[str, str], ...] = (("inputVariable", "input"), ("outputVariable", "output"))
    execution_roles: tuple[tuple[str, str, str], ...] = (
        ("input", "EN", "execution_enable"),
        ("output", "ENO", "execution_status"),
    )
    execution_after_attribute: str = "execAfter"
    execution_rule_source: str = "https://www.se.com/us/en/faqs/FA340273/"


GRAPHICAL_SPEC = GraphicalSpec()
