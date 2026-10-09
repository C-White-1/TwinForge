"""Conservative basic mapping from a captured `.smbp` tree to neutral objects.

Milestones 1 and 2 of docs/roadmaps/machine-expert-basic-roadmap.md:
controller identity, symbol-table tags, one Program/Routine per POU, and a
`LadderRung.network` built from each rung's grid (see `ladder.py`), or, for a
rung written in Instruction List, from its IL (see `instruction_list.py`).
An IL rung also keeps its IL verbatim in `LadderRung.instruction_list`,
which is its only logic when the IL is not ladder-expressible.

`LadderRung.text` is left empty: across this codebase it means Logix RLL
text (`rll.py`, `software_calls.py` and `tag_dependencies.py` all read it
that way, and the last skips `network` whenever `text` is set). A grid
rung's IL stays verbatim in its source extension.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

from twinforge.model import (
    Controller, Identity, LadderInstruction, LadderOperation, LadderParallel, LadderRung, LadderSeries, Program,
    Routine, Tag,
)
from twinforge.schema.machine_expert_basic import BASIC_MAPPING, MappingSpec

from .capture import CapturedArtifact, CapturedSection, Diagnostic
from .evidence import source_extension as _extension
from .instruction_list import build_network_from_instruction_list
from .ladder import NetworkUnresolved, build_network

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
                tag = Tag(name=name, data_type=table.data_type, description=_text(entry, spec.entry_comment),
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


def _unsupported(series: LadderSeries) -> list[str]:
    found: list[str] = []
    for element in series.elements:
        if isinstance(element, LadderParallel):
            for branch in element.branches:
                found.extend(_unsupported(branch))
        elif isinstance(element, LadderInstruction) and element.operation is LadderOperation.UNSUPPORTED:
            found.append(element.source_mnemonic)
    return found


def _rung(routine: str, index: int, node: CapturedSection, spec: MappingSpec, result: ParsedProject,
          symbols: dict[str, str]) -> LadderRung:
    rung = LadderRung(number=index, comment=_text(node, spec.rung_comment), source_extensions=[_extension(node)])
    if not _select(node, spec.rung_instruction_lines):
        result.report("missing_instruction_list", f"{routine} rung {index} has no Instruction List lines", node)
    disconnected: list[str] = []
    if not _has_grid(node, spec):
        # Written in IL: keep the IL as the rung's logic, and derive a network
        # from it when it is ladder-expressible.
        rung.instruction_list = [line.text or "" for entry in _select(node, spec.rung_instruction_lines)
                                 for line in _select(entry, spec.instruction_text)]
        if not any(line.strip() for line in rung.instruction_list):
            return rung
        try:
            rung.network = build_network_from_instruction_list(rung.instruction_list, symbols)
        except NetworkUnresolved as error:
            result.report(error.code, f"{routine} rung {index}: {error}; Instruction List kept as the rung's logic",
                          node)
            return rung
    else:
        cells = [{child.tag: (child.text or "").strip() for child in cell.ordered_children}
                 for cell in _select(node, spec.rung_cells)]
        try:
            rung.network, disconnected = build_network(cells, symbols)
        except NetworkUnresolved as error:
            result.report(error.code, f"{routine} rung {index}: {error}", node)
            return rung
    if disconnected:
        result.report("ladder_disconnected_element",
                      f"{routine} rung {index}: {sorted(set(disconnected))} reach no output; "
                      "left out of the network, retained in source", node)
    unsupported = _unsupported(rung.network)
    if unsupported:
        result.report("ladder_unsupported_element",
                      f"{routine} rung {index}: {sorted(set(unsupported))} have no portable operation; "
                      "kept in the network as UNSUPPORTED", node)
    return rung


def _has_grid(node: CapturedSection, spec: MappingSpec) -> bool:
    return any(_text(cell, spec.cell_element_type) != spec.placeholder_cell_type
               for cell in _select(node, spec.rung_cells))


def _timers(result: ParsedProject, root: CapturedSection, spec: MappingSpec) -> None:
    """Give every timer the logic uses (or the file configures) a tag, typed as
    its IEC TON/TOF/TP instance with PT, when it behaves as one.

    A timer is a declared object even when it has no symbol or `TimerTM`
    entry (all-default timers have neither), so an unnamed one gets a tag
    named by its address. Settings left at their default are not written to
    the file, so absent values take the documented defaults (`TimerSpec`).
    """
    timers = spec.timers
    address_pattern = re.compile(re.escape(timers.address_prefix) + r"\d+")
    write_pattern = re.compile(timers.preset_write_pattern)
    entries: dict[str, CapturedSection] = {}
    for entry in _select(root, timers.container + (timers.entry,)):
        address = _text(entry, spec.entry_address)
        if address:
            entries[address] = entry
    referenced: set[str] = set()
    written: set[str] = set()
    for pou in _select(root, spec.pous):
        for rung in _select(pou, spec.rungs):
            texts = [line.text or "" for entry in _select(rung, spec.rung_instruction_lines)
                     for line in _select(entry, spec.instruction_text)]
            for cell in _select(rung, spec.rung_cells):
                texts.extend(_text(cell, path) or "" for path in (spec.cell_descriptor, *spec.expression_fields))
            for text in texts:
                referenced.update(address_pattern.findall(text))
                written.update(write_pattern.findall(text))
    tags_by_address = {tag.metadata["source_memory_address"]: tag for tag in result.controller.tags.values()
                       if tag.metadata.get("source_symbol_table") == "Timers"
                       and "source_memory_address" in tag.metadata}
    base_milliseconds = dict(timers.base_milliseconds)
    for address in sorted(set(entries) | referenced, key=lambda a: int(a[len(timers.address_prefix):])):
        entry = entries.get(address)
        node = entry if entry is not None else root
        timer_type = (_text(entry, timers.type_field) if entry is not None else None) or timers.default_type
        preset_text = (_text(entry, timers.preset_field) if entry is not None else None) or str(timers.default_preset)
        base = (_text(entry, timers.base_field) if entry is not None else None) or timers.default_base
        reasons = []
        if timer_type not in timers.iec_types:
            reasons.append(f"type {timer_type!r} is not TON, TOF or TP")
        if base not in base_milliseconds:
            reasons.append(f"time base {base!r} is not a verified spelling")
        if not preset_text.isdigit():
            reasons.append(f"preset {preset_text!r} is not a number")
        if entry is not None and _text(entry, timers.retentive_field) == "true":
            reasons.append("Retentive has no IEC TON/TOF/TP equivalent")
        if entry is not None and _text(entry, timers.dynamic_preset_field) == "true":
            reasons.append("Dynamic Preset has no IEC TON/TOF/TP equivalent")
        if address in written:
            reasons.append("the program writes its preset (%TMi.P), which takes effect differently")
        tag = tags_by_address.get(address)
        if tag is None:
            tag = Tag(name=address, source_extensions=[_extension(entry)] if entry is not None else [])
            tag.metadata["source_symbol_table"] = "Timers"
            tag.metadata["source_memory_address"] = address
            result.controller.add_tag(tag)
        if reasons:
            result.report("timer_not_converted", f"{address}: {'; '.join(reasons)}; kept as an untyped timer", node)
            continue
        tag.data_type = timer_type
        # Constant inputs of the IEC function block instance, as IEC literals.
        tag.metadata["iec_function_block_inputs"] = {
            "PT": f"TIME#{int(preset_text) * base_milliseconds[base]}ms"}


def _programs(result: ParsedProject, root: CapturedSection, spec: MappingSpec) -> None:
    used: set[str] = set()
    # Ladder operands use the declared tag name for an address when one exists.
    # Unnamed objects that still got a tag (timers) are named by their address.
    symbols = {tag.metadata["source_memory_address"]: name for name, tag in result.controller.tags.items()
               if "source_memory_address" in tag.metadata and name != tag.metadata["source_memory_address"]}
    for pou in _select(root, spec.pous):
        name = _unique_name(result, pou, _text(pou, spec.pou_name), used, "POU")
        if name is None:
            continue
        rung_nodes = _select(pou, spec.rungs)
        # IL is stored for every rung; a grid only for rungs edited in Ladder.
        language = "LD" if any(_has_grid(rung, spec) for rung in rung_nodes) else "IL"
        routine = Routine(name=name, language=language, source_extensions=[_extension(pou)])
        routine.ladder_rungs = [_rung(name, index, rung, spec, result, symbols)
                                for index, rung in enumerate(rung_nodes)]
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
    _timers(result, root, spec)
    _programs(result, root, spec)
    return result
