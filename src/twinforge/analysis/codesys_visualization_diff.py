"""Evidence-led comparison of CODESYS native visualization exports."""

from dataclasses import dataclass

from twinforge.parsers.codesys_native import (
    CodesysNativeExport,
    CodesysVisualizationAction,
    CodesysVisualizationElement,
)


@dataclass(frozen=True)
class CodesysPropertyChange:
    """One observed property value transition."""

    property_id: str
    property_name: str | None
    before: str | None
    after: str | None


@dataclass(frozen=True)
class CodesysActionPropertyChange:
    """One changed property within a named visualization action."""

    action: str
    property_name: str
    before: str | None
    after: str | None


@dataclass(frozen=True)
class CodesysElementChange:
    """Changes associated with one stable visual-element key."""

    visualization: str
    element_key: str
    change_kind: str
    element_type: str | None
    property_changes: tuple[CodesysPropertyChange, ...] = ()
    bindings_before: tuple[str, ...] = ()
    bindings_after: tuple[str, ...] = ()
    actions_before: tuple[str, ...] = ()
    actions_after: tuple[str, ...] = ()
    action_details_before: tuple[str, ...] = ()
    action_details_after: tuple[str, ...] = ()
    action_property_changes: tuple[CodesysActionPropertyChange, ...] = ()


@dataclass(frozen=True)
class CodesysVisualizationDiff:
    """Semantic and opaque-property evidence between two archives."""

    profile_before: str | None
    profile_after: str | None
    element_changes: tuple[CodesysElementChange, ...]
    manager_changes: tuple[CodesysPropertyChange, ...]


def compare_codesys_visualizations(
    before: CodesysNativeExport,
    after: CodesysNativeExport,
) -> CodesysVisualizationDiff:
    """Compare parsed archives without interpreting unknown property IDs."""
    before_elements = _elements(before)
    after_elements = _elements(after)
    changes: list[CodesysElementChange] = []

    for key in sorted(before_elements.keys() | after_elements.keys()):
        old = before_elements.get(key)
        new = after_elements.get(key)
        visualization, element_key = key
        if old is None:
            changes.append(
                _element_change(
                    visualization,
                    element_key,
                    "added",
                    None,
                    new,
                )
            )
        elif new is None:
            changes.append(
                _element_change(
                    visualization,
                    element_key,
                    "removed",
                    old,
                    None,
                )
            )
        else:
            change = _element_change(
                visualization,
                element_key,
                "modified",
                old,
                new,
            )
            if _has_changes(change):
                changes.append(change)

    return CodesysVisualizationDiff(
        profile_before=before.profile,
        profile_after=after.profile,
        element_changes=tuple(changes),
        manager_changes=_manager_changes(before, after),
    )


def _elements(
    document: CodesysNativeExport,
) -> dict[tuple[str, str], CodesysVisualizationElement]:
    result: dict[tuple[str, str], CodesysVisualizationElement] = {}
    for visualization in document.visualizations:
        for index, element in enumerate(visualization.elements):
            identity = (
                element.identifier
                or (
                    str(element.element_id)
                    if element.element_id is not None
                    else f"index:{index}"
                )
            )
            result[(visualization.name, identity)] = element
    return result


def _element_change(
    visualization: str,
    element_key: str,
    change_kind: str,
    before: CodesysVisualizationElement | None,
    after: CodesysVisualizationElement | None,
) -> CodesysElementChange:
    reference = after if after is not None else before
    old_properties = before.numeric_properties if before else {}
    new_properties = after.numeric_properties if after else {}
    friendly = {}
    if before:
        friendly.update(_friendly_ids(before))
    if after:
        friendly.update(_friendly_ids(after))
    property_changes = tuple(
        CodesysPropertyChange(
            property_id=property_id,
            property_name=friendly.get(property_id),
            before=old_properties.get(property_id),
            after=new_properties.get(property_id),
        )
        for property_id in sorted(
            old_properties.keys() | new_properties.keys(),
            key=_property_sort_key,
        )
        if old_properties.get(property_id) != new_properties.get(property_id)
    )
    return CodesysElementChange(
        visualization=visualization,
        element_key=element_key,
        change_kind=change_kind,
        element_type=reference.element_type if reference is not None else None,
        property_changes=property_changes,
        bindings_before=before.bindings if before else (),
        bindings_after=after.bindings if after else (),
        actions_before=_action_names(before),
        actions_after=_action_names(after),
        action_details_before=_action_details(before),
        action_details_after=_action_details(after),
        action_property_changes=_action_property_changes(before, after),
    )


def _friendly_ids(
    element: CodesysVisualizationElement,
) -> dict[str, str]:
    return element.property_names


def _action_names(
    element: CodesysVisualizationElement | None,
) -> tuple[str, ...]:
    if element is None:
        return ()
    return tuple(action.kind for action in element.actions)


def _action_details(
    element: CodesysVisualizationElement | None,
) -> tuple[str, ...]:
    if element is None:
        return ()
    details: list[str] = []
    for action in element.actions:
        properties = tuple(
            f"{key}={value}"
            for key, value in sorted(action.properties.items())
            if key not in {"Name", "Description"}
        )
        suffix = f" ({', '.join(properties)})" if properties else ""
        details.append(action.kind + suffix)
    return tuple(details)


def _action_property_changes(
    before: CodesysVisualizationElement | None,
    after: CodesysVisualizationElement | None,
) -> tuple[CodesysActionPropertyChange, ...]:
    old_actions = _actions_by_key(before)
    new_actions = _actions_by_key(after)
    changes: list[CodesysActionPropertyChange] = []
    for key in sorted(old_actions.keys() & new_actions.keys()):
        old = old_actions[key]
        new = new_actions[key]
        for property_name in sorted(
            old.properties.keys() | new.properties.keys()
        ):
            if property_name in {"Name", "Description"}:
                continue
            old_value = old.properties.get(property_name)
            new_value = new.properties.get(property_name)
            if old_value != new_value:
                changes.append(
                    CodesysActionPropertyChange(
                        action=old.kind,
                        property_name=property_name,
                        before=old_value,
                        after=new_value,
                    )
                )
    return tuple(changes)


def _actions_by_key(
    element: CodesysVisualizationElement | None,
) -> dict[tuple[str, int], CodesysVisualizationAction]:
    if element is None:
        return {}
    counts: dict[str, int] = {}
    result: dict[tuple[str, int], CodesysVisualizationAction] = {}
    for action in element.actions:
        index = counts.get(action.kind, 0)
        counts[action.kind] = index + 1
        result[(action.kind, index)] = action
    return result


def _has_changes(change: CodesysElementChange) -> bool:
    return bool(
        change.property_changes
        or change.bindings_before != change.bindings_after
        or change.actions_before != change.actions_after
        or change.action_details_before != change.action_details_after
        or change.action_property_changes
    )


def _property_sort_key(value: str) -> tuple[int, int | str]:
    return (0, int(value)) if value.isdigit() else (1, value)


def _manager_changes(
    before: CodesysNativeExport,
    after: CodesysNativeExport,
) -> tuple[CodesysPropertyChange, ...]:
    old = before.managers[0] if before.managers else None
    new = after.managers[0] if after.managers else None
    values = (
        ("style", old.style if old else None, new.style if new else None),
        ("numpad", old.numpad if old else None, new.numpad if new else None),
    )
    return tuple(
        CodesysPropertyChange(name, name, old_value, new_value)
        for name, old_value, new_value in values
        if old_value != new_value
    )
