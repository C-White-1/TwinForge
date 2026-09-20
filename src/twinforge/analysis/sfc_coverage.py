"""Build a test-coverage/traceability skeleton from parsed SFC evidence.

Lists every step, every transition and every SFC-relevant diagnostic as a row
a reviewer can map to a requirement and a test case. This asserts nothing about
the correctness or completeness of the underlying PLC logic -- only what
TwinForge could and could not establish structurally. Regenerating overwrites
the sheet; it does not merge back a reviewer's prior requirement/test-ID
annotations (see the roadmap's coverage checkpoint for that known limitation).
"""
from dataclasses import dataclass

from twinforge.model import Controller
from twinforge.model.sequential import SequentialElement
from twinforge.parsers.control_expert.capture import Diagnostic

# Diagnostic codes describing SFC structure specifically -- not every code this
# parser can emit (hardware, variables, FBD, ... are out of scope here).
SFC_DIAGNOSTIC_CODES = frozenset({
    "uninterpreted_sfc_execution",
    "missing_sfc_definition_name",
    "duplicate_sfc_definition",
    "unresolved_sfc_transition_reference",
    "invalid_sfc_link_endpoint_count",
    "unresolved_sfc_link_endpoint",
    "unresolved_sfc_successor",
    "ambiguous_sfc_successor",
    "unsupported_sfc_branch_position",
    "sfc_unresolved_member",
    "sfc_ambiguous_symbol",
    "sfc_missing_symbol",
    "sfc_unresolved_expression",
})


@dataclass(frozen=True)
class SFCCoverageItem:
    """One traceable row: a step, a transition, or an SFC-relevant diagnostic."""
    key: str
    program_name: str
    routine_name: str
    chart_name: str | None
    chart_index: int
    item_type: str  # "step" | "transition" | "diagnostic"
    element_name: str | None
    element_path: tuple[int, int] | None
    description: str
    connectivity_status: str  # "resolved" | "unresolved" | "not_applicable"
    diagnostic_code: str | None


@dataclass(frozen=True)
class SFCCoverageReport:
    controller_name: str
    items: tuple[SFCCoverageItem, ...]

    @property
    def step_count(self) -> int:
        return sum(item.item_type == "step" for item in self.items)

    @property
    def transition_count(self) -> int:
        return sum(item.item_type == "transition" for item in self.items)

    @property
    def diagnostic_count(self) -> int:
        return sum(item.item_type == "diagnostic" for item in self.items)

    @property
    def unresolved_connectivity_count(self) -> int:
        return sum(item.connectivity_status == "unresolved" for item in self.items)


def _condition_text(transition: SequentialElement) -> str | None:
    for child in transition.children:
        if child.kind != "condition":
            continue
        for reference in child.children:
            if reference.kind in {"transition_reference", "variable_reference"} and reference.text:
                inverted = child.properties.get("inversion") == "true"
                return f"NOT {reference.text.strip()}" if inverted else reference.text.strip()
    return None


def build_sfc_coverage_report(
    controller: Controller, diagnostics: list[Diagnostic],
) -> SFCCoverageReport:
    items: list[SFCCoverageItem] = []
    location_owners: dict[tuple[str, tuple[tuple[int, str], ...], str], tuple[str, str, int, str | None]] = {}

    for program in controller.programs.values():
        for routine in program.routines.values():
            if routine.source_extensions:
                # Routine-level diagnostics (e.g. uninterpreted_sfc_execution) are
                # reported against the routine's own source, not any chart element.
                metadata = routine.source_extensions[0].metadata
                location_owners[(metadata["input_sha256"], tuple(metadata["members"]),
                                  metadata["xml_path"])] = (program.name, routine.name, -1, None)
            for chart_index, chart in enumerate(routine.sequential_charts):
                edge_sources = {tuple(edge.source_path) for edge in chart.connectivity_edges}
                for network_index, network in enumerate(chart.elements):
                    if network.kind != "network":
                        continue
                    for child_index, element in enumerate(network.children):
                        if element.kind not in {"step", "transition"}:
                            continue
                        if element.source_extensions:
                            metadata = element.source_extensions[0].metadata
                            location_owners[(metadata["input_sha256"], tuple(metadata["members"]),
                                              metadata["xml_path"])] = (
                                program.name, routine.name, chart_index, chart.name)
                        path = (network_index, child_index)
                        status = "resolved" if path in edge_sources else "unresolved"
                        if element.kind == "step":
                            name = element.properties.get("name")
                            description = f"Step {name or '(unnamed)'}" + (
                                " (initial)" if element.properties.get("source_step_type") == "initialStep" else "")
                        else:
                            name = None
                            condition = _condition_text(element)
                            description = f"Transition{f': {condition}' if condition else ' (condition not resolved to a simple reference)'}"
                        items.append(SFCCoverageItem(
                            key=f"{program.name}/{routine.name}/chart{chart_index}/{element.kind}@{network_index}.{child_index}",
                            program_name=program.name, routine_name=routine.name,
                            chart_name=chart.name, chart_index=chart_index,
                            item_type=element.kind, element_name=name, element_path=path,
                            description=description, connectivity_status=status, diagnostic_code=None,
                        ))

    for index, diagnostic in enumerate(diagnostics):
        if diagnostic.code not in SFC_DIAGNOSTIC_CODES:
            continue
        owner = location_owners.get(
            (diagnostic.source.input_sha256, diagnostic.source.members, diagnostic.source.xml_path))
        program_name, routine_name, chart_index, chart_name = owner or ("", "", -1, None)
        items.append(SFCCoverageItem(
            key=f"diagnostic:{diagnostic.code}#{index}",
            program_name=program_name, routine_name=routine_name,
            chart_name=chart_name, chart_index=chart_index,
            item_type="diagnostic", element_name=None, element_path=None,
            description=diagnostic.message, connectivity_status="not_applicable",
            diagnostic_code=diagnostic.code,
        ))

    return SFCCoverageReport(controller_name=controller.name, items=tuple(items))
