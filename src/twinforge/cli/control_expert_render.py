"""Render Control Expert LD networks as SVG diagrams for offline viewing."""
from __future__ import annotations

from pathlib import Path
from typing import TextIO

from twinforge.exporters.ladder_svg import LadderSvgExporter
from twinforge.model import LadderRung
from twinforge.parsers.control_expert import capture_file, parse_projects

from .control_expert import _artifacts, ControlExpertCommandError


def _network_key(rung: LadderRung) -> str | None:
    """Return the enclosing `networkLD`'s xml_path prefix, or None if unknown.

    There is no network-index field on `LadderRung` itself (see
    docs/roadmaps/graphical-diagram-visualization-roadmap.md); rungs from the
    same network are contiguous in `Routine.ladder_rungs` (the parser walks
    each `networkLD` in document order, one full pass), so trimming each
    rung's own xml_path down to its parent is enough to tell "still the same
    network" from "a new one started" without needing that field.
    """
    if not rung.source_extensions:
        return None
    xml_path = rung.source_extensions[0].metadata.get("xml_path")
    if not isinstance(xml_path, str):
        return None
    prefix, _, _ = xml_path.rpartition("/")
    return prefix or None


def _group_rungs_by_network(rungs: list[LadderRung]) -> list[list[LadderRung]]:
    groups: list[list[LadderRung]] = []
    last_key: str | None = None
    for rung in rungs:
        key = _network_key(rung)
        if key is not None and key == last_key and groups:
            groups[-1].append(rung)
        else:
            groups.append([rung])
        last_key = key
    return groups


def render_control_expert_ladder(
    path: Path,
    *,
    destination: Path,
    stdout: TextIO,
    routine: str | None = None,
    network: int | None = None,
) -> None:
    """Write one SVG file per `networkLD`, across every program/routine.

    `routine`/`network` narrow this to a single routine name and/or a single
    (0-indexed, in document order) network within it; omitted, every LD
    network in the file is rendered. This never reads raw captured XML
    itself -- only `Routine.ladder_rungs`, the same vendor-neutral model
    every other exporter in this project renders from.
    """
    try:
        captured = capture_file(path)
        projects = parse_projects(captured)
    except (OSError, ValueError) as error:
        raise ControlExpertCommandError(f"could not inspect Control Expert input '{path}': {error}") from error
    failures = [d for artifact in _artifacts(captured) for d in artifact.diagnostics
                if d.code not in {"unclassified_xml", "unclassified_content"}]
    if failures or not projects:
        raise ControlExpertCommandError(
            f"could not render ladder logic for '{path}': capture was incomplete "
            "or no supported exchange project was found"
        )
    destination.mkdir(parents=True, exist_ok=True)
    exporter = LadderSvgExporter()
    written = 0
    for project_index, project in enumerate(projects):
        project_prefix = f"project{project_index}_" if len(projects) > 1 else ""
        for program_name, program in project.controller.programs.items():
            for routine_name, r in program.routines.items():
                if routine is not None and routine_name != routine:
                    continue
                if not r.ladder_rungs:
                    continue
                for net_index, rungs in enumerate(_group_rungs_by_network(r.ladder_rungs)):
                    if network is not None and net_index != network:
                        continue
                    title = f"{routine_name} network {net_index}"
                    svg = exporter.export(rungs, title=title)
                    filename = f"{project_prefix}{program_name}_{routine_name}_network{net_index}.svg"
                    (destination / filename).write_text(svg, encoding="utf-8")
                    written += 1
                    stdout.write(f"{title}: {len(rungs)} rungs -> {destination / filename}\n")
    if written == 0:
        raise ControlExpertCommandError(
            f"no matching ladder network found to render in '{path}' "
            f"(routine={routine!r}, network={network!r})"
        )
