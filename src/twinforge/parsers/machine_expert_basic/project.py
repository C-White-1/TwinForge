"""Conservative basic mapping from a captured `.smbp` tree to neutral objects.

Milestone 1 of docs/roadmaps/machine-expert-basic-roadmap.md: controller
identity, symbol-table tags, and one Program/Routine per POU whose rungs
carry their Instruction List text. Grid cells are retained as rung source
evidence but not yet turned into `LadderRung.network`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from twinforge.model import Controller, Identity, LadderRung, Program, Routine, Tag
from twinforge.schema.machine_expert_basic import BASIC_MAPPING, MappingSpec

from .capture import CapturedArtifact, CapturedSection, Diagnostic
from .evidence import source_extension as _extension

PathSpec = tuple[str, ...]


@dataclass
class ParsedProject:
    controller: Controller
    artifact: CapturedArtifact
    project_version: str | None = None
    encrypted: bool = False
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def report(self, code: str, message: str, node: CapturedSection) -> None:
        self.diagnostics.append(Diagnostic(code, message, node.source))


def _select(node: CapturedSection, path: PathSpec) -> list[CapturedSection]:
    nodes = [node]
    for name in path:
        nodes = [child for parent in nodes for child in parent.ordered_children if child.tag == name]
    return nodes


def _text(node: CapturedSection, path: PathSpec) -> str | None:
    """Stripped text of the single node at `path`; None when absent, repeated or empty."""
    nodes = _select(node, path)
    if len(nodes) != 1:
        return None
    return (nodes[0].text or "").strip() or None


def _unique_name(result: ParsedProject, node: CapturedSection, name: str | None,
                 used: set[str], kind: str) -> str | None:
    if not name or name.casefold() in used:
        result.report("ambiguous_identity", f"Missing or duplicate {kind} name {name!r}; source retained", node)
        return None
    used.add(name.casefold())
    return name


def _tags(result: ParsedProject, root: CapturedSection, spec: MappingSpec) -> None:
    used: set[str] = set()
    mapped: set[int] = set()
    for table in spec.symbol_tables:
        for container in _select(root, table.container):
            for entry in _select(container, (table.entry,)):
                mapped.add(id(entry))
                symbol = _text(entry, spec.entry_symbol)
                if symbol is None:
                    continue
                name = _unique_name(result, entry, symbol, used, "symbol")
                if name is None:
                    continue
                tag = Tag(name=name, description=_text(entry, spec.entry_comment),
                          source_extensions=[_extension(entry)])
                tag.metadata["source_symbol_table"] = table.name
                address = _text(entry, spec.entry_address)
                if address is not None:
                    tag.metadata["source_memory_address"] = address
                result.controller.add_tag(tag)
    # A named entry outside every declared table is real data the profile
    # does not yet cover; say so instead of dropping it silently.
    pending, unmapped = [root], []
    while pending:
        node = pending.pop()
        if (id(node) not in mapped and _select(node, spec.entry_address)
                and _text(node, spec.entry_symbol) is not None):
            unmapped.append(node)
        pending.extend(node.ordered_children)
    for node in unmapped:
        result.report("unmapped_symbol",
                      f"Symbol {_text(node, spec.entry_symbol)!r} in <{node.tag}> is outside the "
                      "declared symbol tables; source retained", node)


def _rung(index: int, node: CapturedSection, spec: MappingSpec, result: ParsedProject) -> LadderRung:
    lines = [line.text or "" for entry in _select(node, spec.rung_instruction_lines)
             for line in _select(entry, spec.instruction_text)]
    if not lines:
        result.report("missing_instruction_list", f"Rung {index} has no Instruction List lines", node)
    return LadderRung(number=index, comment=_text(node, spec.rung_comment),
                      text="\n".join(lines) if lines else None,
                      source_extensions=[_extension(node)])


def _has_grid(node: CapturedSection, spec: MappingSpec) -> bool:
    return any(_text(cell, spec.cell_element_type) != spec.placeholder_cell_type
               for cell in _select(node, spec.rung_cells))


def _programs(result: ParsedProject, root: CapturedSection, spec: MappingSpec) -> None:
    used: set[str] = set()
    for pou in _select(root, spec.pous):
        name = _unique_name(result, pou, _text(pou, spec.pou_name), used, "POU")
        if name is None:
            continue
        rung_nodes = _select(pou, spec.rungs)
        # IL is stored for every rung; a grid only for rungs edited in Ladder.
        language = "LD" if any(_has_grid(rung, spec) for rung in rung_nodes) else "IL"
        routine = Routine(name=name, language=language, source_extensions=[_extension(pou)])
        routine.ladder_rungs = [_rung(index, rung, spec, result) for index, rung in enumerate(rung_nodes)]
        program = Program(name=name, source_extensions=[_extension(pou)])
        program.add_routine(routine)
        result.controller.add_program(program)


def parse_project(artifact: CapturedArtifact, *, spec: MappingSpec = BASIC_MAPPING) -> ParsedProject:
    """Map one captured `.smbp`. An encrypted project yields only its public name."""
    root = artifact.section
    if root is None or root.tag not in (spec.project_root, spec.encrypted_root):
        raise ValueError("Expected a captured .smbp project artifact")
    encrypted = root.tag == spec.encrypted_root
    name = _text(root, spec.encrypted_project_name if encrypted else spec.project_name) or ""
    controller = Controller(name=name, identity=Identity(), source_extensions=[_extension(root)])
    result = ParsedProject(controller, artifact, _text(root, spec.project_version), encrypted,
                           list(artifact.diagnostics))
    if not name:
        result.report("missing_project_name", "Project name missing or ambiguous", root)
    if encrypted:
        result.report("encrypted_project",
                      "Project content is encrypted; only public properties are readable. "
                      "Encrypted payload retained verbatim, not decrypted", root)
        return result
    cpu = _text(root, spec.cpu_reference)
    controller.identity = Identity(product_name=cpu)
    if cpu is None:
        result.report("missing_cpu_reference", "CPU catalogue reference missing or ambiguous", root)
    _tags(result, root, spec)
    _programs(result, root, spec)
    return result
