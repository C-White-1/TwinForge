"""Observed escalator SFC selectors and neutral property names, not execution rules."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SequentialSpec:
    charts: str = "chartSource"
    definitions: str = "transitionSource"
    endpoint_types: tuple[tuple[str, str], ...] = (("step", "step"), ("transition", "transition"))
    # Ordered children and unknown nodes are preserved by the consumer.
    elements: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...] = (
        ("networkSFC", "network", ()),
        ("step", "step", (("stepName", "name"), ("stepType", "source_step_type"))),
        ("action", "action", (("qualifier", "qualifier"),)),
        ("actionName", "action_target", ()),
        ("variableName", "variable_reference", ()),
        ("sectionName", "transition_reference", ()),
        ("transition", "transition", ()),
        ("transitionCondition", "condition", (("invertLogic", "inversion"),)),
        ("altBranch", "alternative_branch", (("width", "width"), ("relativePos", "relative_position"))),
        ("linkSFC", "explicit_link", ()),
        ("directedLinkSource", "link_source", (("objectType", "source_object_type"),)),
        ("directedLinkDestination", "link_destination", (("objectType", "source_object_type"),)),
        ("objPosition", "position", (("posX", "x"), ("posY", "y"))),
        ("gridObjPosition", "route_position", (("posX", "x"), ("posY", "y"))),
        ("literals", "step_timing", (("min", "minimum"), ("max", "maximum"), ("delay", "delay"))),
        ("tValue", "action_timing", ()),
        ("tLiteral", "time_literal", ()),
        ("transitionSource", "transition_definition", (("name", "name"),)),
        ("STSource", "structured_text", ()),
    )


SFC_SPEC = SequentialSpec()
