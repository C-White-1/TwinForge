"""Render Control Expert LD networks as SVG diagrams for offline viewing."""
from __future__ import annotations

from pathlib import Path
from typing import TextIO

from twinforge.exporters.ladder_svg import LadderSvgExporter
from twinforge.parsers.control_expert import capture_file, parse_projects

from .control_expert import _artifacts, ControlExpertCommandError


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
    network in the file is rendered. This renders `Routine.graphical_diagrams`
    (`GraphicalDiagram.grid_rows`, Milestone 2 of the visualization roadmap),
    not raw captured XML -- every contact/coil/block/shortCircuit a Control
    Expert LD network can carry, not only the pure-series rows `LadderRung`
    alone would have covered. Each `GraphicalDiagram` already knows which
    network it is, so -- unlike the Milestone 1 CLI this superseded -- no
    workaround is needed to tell one network's rows from the next.
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
                ld_diagrams = [d for d in r.graphical_diagrams if d.language == "LD"]
                for net_index, diagram in enumerate(ld_diagrams):
                    if network is not None and net_index != network:
                        continue
                    title = f"{routine_name} network {net_index}"
                    svg = exporter.export_diagram(diagram, title=title)
                    filename = f"{project_prefix}{program_name}_{routine_name}_network{net_index}.svg"
                    (destination / filename).write_text(svg, encoding="utf-8")
                    written += 1
                    stdout.write(f"{title}: {len(diagram.objects)} objects -> {destination / filename}\n")
    if written == 0:
        raise ControlExpertCommandError(
            f"no matching ladder network found to render in '{path}' "
            f"(routine={routine!r}, network={network!r})"
        )
