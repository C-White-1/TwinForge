"""Read-only inspection summaries for Control Expert exchange files."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, TextIO

from twinforge.model.ladder import LadderInstruction, LadderPosition, LadderSeries
from twinforge.model.routine import LadderRung
from twinforge.model.sequential import SequentialElement
from twinforge.parsers.control_expert import capture_file, parse_projects
from twinforge.parsers.control_expert.capture import CapturedArtifact
from twinforge.parsers.control_expert.project import ParsedProject


class ControlExpertCommandError(RuntimeError):
    """Inspection failed or could not fully read its input."""


def _artifacts(root: CapturedArtifact) -> list[CapturedArtifact]:
    result = [root]
    for member in root.members:
        result.extend(_artifacts(member))
    return result


def _sequential_element(element: SequentialElement) -> dict[str, Any]:
    return {"kind": element.kind, "properties": element.properties, "text": element.text,
            "reference_status": element.reference_status,
            "target_definition_index": element.target_definition_index,
            "target_element_path": element.target_element_path,
            "binding_kind": element.binding_kind,
            "target_symbol_name": element.target_symbol_name,
            "target_member_name": element.target_member_name,
            "member_data_type": element.member_data_type,
            "children": [_sequential_element(child) for child in element.children]}


def _ladder_position(position: LadderPosition | None) -> dict[str, Any] | None:
    return {"column": position.column, "row": position.row} if position else None


def _ladder_instruction(instruction: LadderInstruction) -> dict[str, Any]:
    return {"operation": instruction.operation.value, "source_mnemonic": instruction.source_mnemonic,
            "operand": instruction.operand, "alias": instruction.alias,
            "annotations": list(instruction.annotations),
            "position": _ladder_position(instruction.position)}


def _ladder_series(series: LadderSeries) -> dict[str, Any]:
    return {"elements": [_ladder_instruction(element) if isinstance(element, LadderInstruction)
                          else {"branches": [_ladder_series(branch) for branch in element.branches]}
                          for element in series.elements]}


def _ladder_rung(rung: LadderRung) -> dict[str, Any]:
    return {"number": rung.number, "rung_type": rung.rung_type, "comment": rung.comment,
            "position": _ladder_position(rung.position),
            "network": _ladder_series(rung.network) if rung.network else None}


def _expression_operand(operand: Any) -> dict[str, Any]:
    return {
        "text": operand.text, "kind": operand.kind,
        "target_tag": operand.target_tag.name if operand.target_tag else None,
        "target_parameter": operand.target_parameter.name if operand.target_parameter else None,
        "member_path": asdict(operand.member_path) if operand.member_path else None,
        # Set for kind "declared_expression": a logical operand that is
        # itself a Tier 1 comparison/arithmetic expression.
        "sub_expression": _binary_expression(operand.sub_expression) if operand.sub_expression else None,
    }


def _binary_expression(expression: Any) -> dict[str, Any]:
    return {
        "operator": expression.operator,
        "left": _expression_operand(expression.left),
        "right": _expression_operand(expression.right),
    }


def _diagram_summary(diagram: Any) -> dict[str, Any]:
    return {
        "language": diagram.language,
        "connectivity_resolved": diagram.connectivity_resolved,
        "execution_order_resolved": diagram.execution_order_resolved,
        "execution_order": diagram.execution_order,
        "execution_order_basis": diagram.execution_order_basis,
        "shared_variables": [asdict(group) for group in diagram.shared_variables],
        "links": [{
            "source": asdict(link.source), "destination": asdict(link.destination),
        } for link in diagram.links],
        "objects": [{
            "kind": obj.kind, "instance_name": obj.instance_name,
            "type_name": obj.type_name, "operand": obj.operand,
            "interface_status": obj.interface_status, "interface_index": obj.interface_index,
            "position": asdict(obj.position) if obj.position else None,
            "execution_after": obj.execution_after,
            "operand_binding_kind": obj.operand_binding_kind,
            "target_tag": obj.target_tag.name if obj.target_tag else None,
            "target_step_name": obj.target_step_name,
            "operand_member_path": asdict(obj.operand_member_path) if obj.operand_member_path else None,
            "operand_binary_expression": (
                _binary_expression(obj.operand_binary_expression) if obj.operand_binary_expression else None),
            "pins": [{"name": pin.name, "direction": pin.direction,
                      "role": pin.role, "expression": pin.expression,
                      "interface_status": pin.interface_status, "parameter_index": pin.parameter_index,
                      "inverted": pin.inverted, "binding_kind": pin.binding_kind,
                      "target_tag": pin.target_tag.name if pin.target_tag else None,
                      "target_parameter": pin.target_parameter.name if pin.target_parameter else None,
                      "member_path": asdict(pin.member_path) if pin.member_path else None,
                      "binary_expression": (
                          _binary_expression(pin.binary_expression) if pin.binary_expression else None)}
                     for pin in obj.pins],
        } for obj in diagram.objects],
    }


def _project_summary(project: ParsedProject) -> dict[str, Any]:
    controller = project.controller
    programs = []
    for program in controller.programs.values():
        routines = []
        for routine in program.routines.values():
            diagrams = [_diagram_summary(diagram) for diagram in routine.graphical_diagrams]
            routines.append({
                "name": routine.name, "language": routine.language,
                "structured_text_line_count": len(routine.structured_text_lines),
                "task_schedule": routine.metadata.get("task_schedule", []),
                "diagrams": diagrams,
                "ladder_rungs": [_ladder_rung(rung) for rung in routine.ladder_rungs],
                "sequential_charts": [{
                    "name": chart.name,
                    "connectivity_resolved": chart.connectivity_resolved,
                    "connectivity_edges": [{"source_path": edge.source_path,
                                            "destination_path": edge.destination_path,
                                            "basis": edge.basis} for edge in chart.connectivity_edges],
                    "execution_resolved": chart.execution_resolved,
                    "elements": [_sequential_element(e) for e in chart.elements],
                    "transition_definitions": [_sequential_element(e) for e in chart.transition_definitions],
                } for chart in routine.sequential_charts],
            })
        programs.append({"name": program.name, "routines": routines})
    return {
        "name": controller.name,
        "source": asdict(project.artifact.source),
        "sha256": project.artifact.sha256,
        "controller_product": controller.identity.product_name,
        "library_interfaces": [{"name": i.name, "kind": i.kind,
                                "parameters": [asdict(p) for p in i.parameters]}
                               for i in project.library_interfaces],
        "tasks": [{
            "name": task.name, "type": task.task_type,
            "cycle_policy": task.metadata.get("cycle_policy"),
            "scheduled_sections": task.scheduled_program_names,
            "resolved_sections": [p.name for p in task.scheduled_programs],
        } for task in controller.tasks.values()],
        "resources": [{
            "name": resource.name, "identifier": resource.identifier,
            "variable_count": len(resource.tags), "tasks": resource.task_names,
            "ambiguous_names": sorted(resource.ambiguous_names),
        } for resource in controller.resources.values()],
        "programs": programs,
        "datatypes": [{
            "name": dt.name, "description": dt.description,
            "members": [{
                "name": m.name, "type": m.data_type_name, "dimension": m.dimension,
                "resolved_datatype": m.data_type.name if m.data_type else None,
                "description": m.description,
            } for m in dt.members],
        } for dt in controller.datatypes.values()],
        "function_blocks": [{
            "name": aoi.name, "description": aoi.description,
            "parameters": [{
                "name": p.name, "type": p.data_type, "usage": p.usage,
                "resolved_datatype": p.data_type_definition.name if p.data_type_definition else None,
            } for p in aoi.parameters.values()],
            "local_tags": [{
                "name": t.name, "type": t.data_type,
                "resolved_datatype": t.data_type_definition.name if t.data_type_definition else None,
            } for t in aoi.local_tags.values()],
            "body": [{
                "language": r.language, "structured_text_line_count": len(r.structured_text_lines),
                "diagrams": [_diagram_summary(diagram) for diagram in r.graphical_diagrams],
                "ladder_rung_count": len(r.ladder_rungs), "sequential_chart_count": len(r.sequential_charts),
            } for r in aoi.routines.values()],
        } for aoi in controller.add_on_instructions.values()],
        "variables": [{
            "name": tag.name, "type": tag.data_type,
            "resolved_datatype": tag.data_type_definition.name if tag.data_type_definition else None,
            "address": tag.metadata.get("source_memory_address"),
            "array_bounds": tag.metadata.get("source_array_bounds"),
            "initializers": tag.metadata.get("source_initial_values", []),
        } for tag in controller.tags.values()],
        "chassis": [{"name": rack.name, "modules": [
            {"catalog": module.catalog, "slot": module.slot}
            for module in rack.modules.values()
        ], "power_supplies": [
            {"catalog": module.catalog} for module in rack.power_supplies
        ]} for rack in controller.chassis.values()],
        "unplaced_modules": [{"catalog": module.catalog, "slot": module.slot}
                             for module in controller.unplaced_modules],
        "diagnostics": [asdict(diagnostic) for diagnostic in project.diagnostics],
    }


def inspect_control_expert(path: Path, *, output_format: str, stdout: TextIO) -> None:
    """Print deterministic inspection evidence; partial reads have a failure exit."""
    try:
        captured = capture_file(path)
        projects = parse_projects(captured)
    except (OSError, ValueError) as error:
        raise ControlExpertCommandError(f"could not inspect Control Expert input '{path}': {error}") from error
    artifacts = _artifacts(captured)
    diagnostics = [d for artifact in artifacts for d in artifact.diagnostics]
    # Grammar coverage diagnostics are expected for a provisional reader. All
    # other capture diagnostics indicate unreadable or incompletely inspected data.
    failures = [d for d in diagnostics if d.code not in {"unclassified_xml", "unclassified_content"}]
    report: dict[str, Any] = {
        "report_version": "1.0", "report_type": "control_expert_inspection",
        "input": {"name": path.name, "sha256": captured.sha256},
        "status": "incomplete_capture" if failures else "inspected" if projects else "no_supported_projects",
        "native_validation": "not_performed",
        "artifacts": [{"name": a.name, "source": asdict(a.source), "kind": a.kind,
                       "sha256": a.sha256, "bytes_available": a.raw_bytes is not None,
                       "size_bytes": len(a.raw_bytes) if a.raw_bytes is not None else a.declared_size}
                      for a in artifacts],
        "capture_diagnostics": [asdict(d) for d in diagnostics],
        "projects": [_project_summary(p) for p in projects],
    }
    if output_format == "json":
        stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        stdout.write(f"Control Expert inspection: {path.name}\n"
                     f"SHA-256: {captured.sha256}\n"
                     f"Status: {report['status']}\n"
                     f"Projects: {len(projects)} (each exchange document is listed separately)\n"
                     "Native validation: not performed\n")
        for index, project in enumerate(report["projects"]):
            location = " / ".join(f"[{i}] {name}" for i, name in project["source"]["members"]) or path.name
            stdout.write(f"\nProject {index + 1}: {project['name'] or '(unnamed)'}\n"
                         f"  Source: {location}\n"
                         f"  Controller: {project['controller_product'] or '(unknown)'}\n"
                         f"  Variables: {len(project['variables'])}; datatypes: {len(project['datatypes'])}; "
                         f"function blocks: {len(project['function_blocks'])}; "
                         f"sections: {len(project['programs'])}; "
                         f"racks: {len(project['chassis'])}; unplaced modules: {len(project['unplaced_modules'])}\n")
            for resource in project["resources"]:
                if resource["variable_count"]:
                    stdout.write(f"  Resource {resource['name']}: {resource['variable_count']} own variables "
                                 f"(tasks: {', '.join(resource['tasks']) or 'none'})\n")
            for task in project["tasks"]:
                stdout.write(f"  Task {task['name']} ({task['type']}): "
                             + " -> ".join(task["scheduled_sections"]) + "\n")
                stdout.write(f"    Resolved sections: {len(task['resolved_sections'])}/{len(task['scheduled_sections'])}; "
                             f"cycle policy: {task['cycle_policy'] or 'unresolved'}\n")
            for program in project["programs"]:
                for routine in program["routines"]:
                    object_count = sum(len(d["objects"]) for d in routine["diagrams"])
                    stdout.write(f"  Section {program['name']}: {routine['language']}; "
                                 f"ST lines: {routine['structured_text_line_count']}; graphical objects: {object_count}\n")
                    if routine["language"] == "LD":
                        stdout.write(f"    Ladder rungs resolved: {len(routine['ladder_rungs'])} "
                                     "(series only; branches remain unresolved)\n")
                    for chart in routine["sequential_charts"]:
                        counts = Counter(e["kind"] for network in chart["elements"] for e in network["children"])
                        connectivity = "resolved" if chart["connectivity_resolved"] else "unresolved"
                        stdout.write(f"    SFC chart {chart['name']}: steps: {counts['step']}; "
                                     f"transitions: {counts['transition']}; connectivity: {connectivity}; "
                                     "execution unresolved\n")
                    for diagram_index, diagram in enumerate(routine["diagrams"]):
                        bindings = Counter(pin["binding_kind"] for obj in diagram["objects"] for pin in obj["pins"])
                        stdout.write(f"    Diagram {diagram_index}: pin bindings: "
                                     + (", ".join(f"{key}={count}" for key, count in sorted(bindings.items())) or "none")
                                     + "\n")
                        if diagram["shared_variables"]:
                            stdout.write("      Shared variable references (not wires): "
                                         + ", ".join(group["symbol_name"] for group in diagram["shared_variables"]) + "\n")
                        if diagram["links"]:
                            resolved = sum(1 for link in diagram["links"]
                                          if link["source"]["status"] == "resolved"
                                          and link["destination"]["status"] == "resolved")
                            stdout.write(f"      Explicit links: {resolved}/{len(diagram['links'])} resolved "
                                         "(pin-to-pin wiring, not an execution-order claim)\n")
            codes = Counter(d["code"] for d in project["diagnostics"])
            stdout.write("  Diagnostics: " + (", ".join(f"{k}={v}" for k, v in sorted(codes.items())) or "none") + "\n")
        if diagnostics:
            stdout.write("\nCapture diagnostics:\n")
            for diagnostic in diagnostics:
                location = " / ".join(f"[{i}] {name}" for i, name in diagnostic.source.members) or path.name
                stdout.write(f"  {location}: {diagnostic.code}: {diagnostic.message}\n")
    if failures or not projects:
        raise ControlExpertCommandError(
            "inspection report emitted, but capture was incomplete or no supported exchange project was found"
        )
