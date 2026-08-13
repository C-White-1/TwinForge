"""Order-independent ingestion of multi-file, multi-controller L5X corpora."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from twinforge.analysis.software_calls import extract_program_calls
from twinforge.model import (
    AddOnInstruction,
    Controller,
    Module,
    ModuleDataDirection,
    Program,
    ResolvedSoftwareCall,
    SoftwareBinding,
    SoftwareBindingRole,
    SoftwareCallSite,
    SoftwareCallArgumentBinding,
    SoftwareCallBindingRole,
    SoftwareComponent,
    SoftwareModuleAssembly,
    SoftwareParameterFlow,
    SoftwareTagScope,
    Tag,
)

from .document import L5XDocument, L5XTargetType
from .parser import L5XParser


class WorkspaceEvidence(str, Enum):
    """Strength of the evidence defining a controller workspace."""

    FULL_CONTROLLER = "full_controller"
    CONTEXT_NAME_ONLY = "context_name_only"


@dataclass
class ControllerWorkspace:
    """Documents assigned to one confirmed or provisional PLC context."""

    key: str
    controller_name: str
    evidence: WorkspaceEvidence
    documents: list[L5XDocument] = field(default_factory=list)
    controller_document: L5XDocument | None = None

    @property
    def confirmed(self) -> bool:
        """Return whether a full controller export anchors this workspace."""

        return self.evidence is WorkspaceEvidence.FULL_CONTROLLER


@dataclass(frozen=True)
class L5XCorpusDiagnostic:
    """A corpus-level ownership or ingestion finding."""

    code: str
    message: str
    source_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class L5XCorpus:
    """Parsed documents plus conservative controller ownership resolution."""

    documents: tuple[L5XDocument, ...]
    workspaces: tuple[ControllerWorkspace, ...]
    shared_software: tuple[SoftwareComponent, ...]
    software_index: dict[str, tuple[SoftwareComponent, ...]]
    software_bindings: tuple[SoftwareBinding, ...]
    call_sites: tuple[SoftwareCallSite, ...]
    resolved_calls: tuple[ResolvedSoftwareCall, ...]
    software_module_assemblies: tuple[SoftwareModuleAssembly, ...]
    unassigned_documents: tuple[L5XDocument, ...]
    diagnostics: tuple[L5XCorpusDiagnostic, ...]


class L5XCorpusParser:
    """Parse explicit L5X import boundaries without assuming one PLC."""

    def parse_directory(
        self,
        directory: str | Path,
        *,
        recursive: bool = True,
    ) -> L5XCorpus:
        """Parse every L5X file below an explicitly supplied directory."""

        root = Path(directory)
        iterator = root.rglob("*") if recursive else root.glob("*")
        paths = [
            path
            for path in iterator
            if path.is_file() and path.suffix.casefold() == ".l5x"
        ]
        return self.parse_files(paths)

    def parse_files(
        self,
        paths: Iterable[str | Path],
    ) -> L5XCorpus:
        """Parse and resolve an explicit set of L5X files."""

        resolved = sorted(
            {Path(path).resolve() for path in paths},
            key=lambda path: str(path).casefold(),
        )
        documents = tuple(
            L5XParser().parse_document(path) for path in resolved
        )
        return _resolve_corpus(documents)


def _resolve_corpus(documents: tuple[L5XDocument, ...]) -> L5XCorpus:
    diagnostics: list[L5XCorpusDiagnostic] = []
    workspaces: list[ControllerWorkspace] = []
    by_controller_name: dict[str, list[ControllerWorkspace]] = defaultdict(
        list
    )

    for document in documents:
        if document.target_type is not L5XTargetType.CONTROLLER:
            continue
        name = document.target.name
        workspace = ControllerWorkspace(
            key=f"controller:{document.source_path}",
            controller_name=name,
            evidence=WorkspaceEvidence.FULL_CONTROLLER,
            documents=[document],
            controller_document=document,
        )
        workspaces.append(workspace)
        by_controller_name[name.casefold()].append(workspace)

    provisional: dict[str, ControllerWorkspace] = {}
    shared_software: list[SoftwareComponent] = []
    unassigned: list[L5XDocument] = []
    for document in documents:
        if document.target_type is L5XTargetType.CONTROLLER:
            continue
        if document.target_type is L5XTargetType.ADD_ON_INSTRUCTION:
            if document.software_component is not None:
                shared_software.append(document.software_component)
            continue
        names = document.context_controller_names
        if len(names) != 1:
            unassigned.append(document)
            diagnostics.append(
                L5XCorpusDiagnostic(
                    "controller_context_not_unique",
                    f"{document.source_path.name} has {len(names)} "
                    "controller context names",
                    (document.source_path,),
                )
            )
            continue
        name = names[0]
        matches = by_controller_name.get(name.casefold(), [])
        if len(matches) == 1:
            matches[0].documents.append(document)
            continue
        if len(matches) > 1:
            unassigned.append(document)
            diagnostics.append(
                L5XCorpusDiagnostic(
                    "ambiguous_controller_context",
                    f"{document.source_path.name} context {name!r} matches "
                    f"{len(matches)} controller exports",
                    (document.source_path,),
                )
            )
            continue
        key = name.casefold()
        workspace = provisional.get(key)
        if workspace is None:
            workspace = ControllerWorkspace(
                key=f"context:{name}",
                controller_name=name,
                evidence=WorkspaceEvidence.CONTEXT_NAME_ONLY,
            )
            provisional[key] = workspace
            workspaces.append(workspace)
        workspace.documents.append(document)

    for name, matches in by_controller_name.items():
        if len(matches) > 1:
            diagnostics.append(
                L5XCorpusDiagnostic(
                    "duplicate_controller_name",
                    f"controller name {name!r} occurs in "
                    f"{len(matches)} full controller exports",
                    tuple(
                        workspace.controller_document.source_path
                        for workspace in matches
                        if workspace.controller_document is not None
                    ),
                )
            )

    software_index = _software_index(shared_software)
    software_bindings = _resolve_software_instances(
        workspaces,
        software_index,
        diagnostics,
    )
    call_sites = _extract_call_sites(workspaces)
    resolved_calls = _resolve_calls(
        call_sites,
        workspaces,
        software_index,
        diagnostics,
    )
    software_module_assemblies = _assemble_software_modules(
        resolved_calls,
        workspaces,
    )
    return L5XCorpus(
        documents=documents,
        workspaces=tuple(workspaces),
        shared_software=tuple(shared_software),
        software_index=software_index,
        software_bindings=tuple(software_bindings),
        call_sites=tuple(call_sites),
        resolved_calls=tuple(resolved_calls),
        software_module_assemblies=tuple(software_module_assemblies),
        unassigned_documents=tuple(unassigned),
        diagnostics=tuple(diagnostics),
    )


def _assemble_software_modules(
    resolved_calls: list[ResolvedSoftwareCall],
    workspaces: list[ControllerWorkspace],
) -> list[SoftwareModuleAssembly]:
    """Group call evidence by PLC, software definition, and instance tag."""

    workspace_by_source = {
        str(document.source_path): workspace
        for workspace in workspaces
        for document in workspace.documents
    }
    grouped: dict[
        tuple[str, str, int],
        list[ResolvedSoftwareCall],
    ] = defaultdict(list)
    for resolved in resolved_calls:
        call = resolved.call_site
        if resolved.instance_tag is None or call.source_path is None:
            continue
        workspace = workspace_by_source.get(str(call.source_path))
        if workspace is None:
            continue
        module_ids = {
            id(binding.target_module)
            for binding in resolved.argument_bindings
            if binding.target_module is not None
        }
        if not module_ids:
            continue
        grouped[
            (
                workspace.key,
                resolved.definition.id,
                id(resolved.instance_tag),
            )
        ].append(resolved)

    assemblies: list[SoftwareModuleAssembly] = []
    for (workspace_key, _, _), calls in grouped.items():
        definition = calls[0].definition
        instance_tag = calls[0].instance_tag
        if instance_tag is None:
            continue
        modules: list[Module] = []
        evidence: list[str] = []
        seen_modules: set[int] = set()
        for resolved in calls:
            for binding in resolved.argument_bindings:
                module = binding.target_module
                if module is None:
                    continue
                if id(module) not in seen_modules:
                    modules.append(module)
                    seen_modules.add(id(module))
                parameter_name = (
                    binding.parameter.name
                    if binding.parameter is not None
                    else "<unmatched>"
                )
                evidence.append(
                    f"{resolved.call_site.program_name}."
                    f"{resolved.call_site.routine_name}: "
                    f"{definition.name} instance {instance_tag.name} "
                    f"parameter {parameter_name} references "
                    f"{binding.argument.source}"
                )
        assemblies.append(
            SoftwareModuleAssembly(
                workspace_key=workspace_key,
                definition=definition,
                instance_tag=instance_tag,
                modules=tuple(modules),
                calls=tuple(calls),
                evidence=tuple(evidence),
            )
        )
    return assemblies


def _extract_call_sites(
    workspaces: list[ControllerWorkspace],
) -> list[SoftwareCallSite]:
    """Collect candidate calls while retaining their document boundaries."""

    return [
        call
        for workspace in workspaces
        for program, source_path in _workspace_programs(workspace)
        for call in extract_program_calls(program, source_path=source_path)
    ]


def _resolve_calls(
    call_sites: list[SoftwareCallSite],
    workspaces: list[ControllerWorkspace],
    software_index: dict[str, tuple[SoftwareComponent, ...]],
    diagnostics: list[L5XCorpusDiagnostic],
) -> list[ResolvedSoftwareCall]:
    """Resolve only calls whose reusable definition is unambiguous."""

    program_index = {
        (str(source_path), program.name.casefold()): program
        for workspace in workspaces
        for program, source_path in _workspace_programs(workspace)
    }
    workspace_by_source = {
        str(document.source_path): workspace
        for workspace in workspaces
        for document in workspace.documents
    }
    document_by_source = {
        str(document.source_path): document
        for workspace in workspaces
        for document in workspace.documents
    }
    resolved: list[ResolvedSoftwareCall] = []
    for call in call_sites:
        definitions = software_index.get(call.callee.casefold(), ())
        if not definitions:
            continue
        if len(definitions) > 1:
            diagnostics.append(
                L5XCorpusDiagnostic(
                    "ambiguous_software_call",
                    f"call {call.program_name}.{call.routine_name} to "
                    f"{call.callee!r} matches {len(definitions)} definitions",
                    (call.source_path,) if call.source_path is not None else (),
                )
            )
            continue
        definition = next(iter(definitions))
        instance_tag = None
        program = None
        first_argument = next(iter(call.arguments), None)
        if call.source_path is not None and first_argument is not None:
            program = program_index.get(
                (str(call.source_path), call.program_name.casefold())
            )
            operand = first_argument.source
            if program is not None:
                instance_tag = program.get_tag(operand)
        argument_bindings = _bind_call_arguments(
            call,
            definition,
            program,
            _controller_tags_for_call(
                document_by_source.get(str(call.source_path)),
                workspace_by_source.get(str(call.source_path)),
            ),
            instance_tag,
            _workspace_modules(
                workspace_by_source.get(str(call.source_path))
            ),
            diagnostics,
        )
        resolved.append(
            ResolvedSoftwareCall(
                call_site=call,
                definition=definition,
                instance_tag=instance_tag,
                argument_bindings=argument_bindings,
            )
        )
    return resolved


def _bind_call_arguments(
    call: SoftwareCallSite,
    definition: SoftwareComponent | None,
    program: Program | None,
    controller_tags: tuple[tuple[Tag, SoftwareTagScope], ...],
    instance_tag: Tag | None,
    modules: tuple[Module, ...],
    diagnostics: list[L5XCorpusDiagnostic],
) -> tuple[SoftwareCallArgumentBinding, ...]:
    """Bind instance and required AOI operands without guessing omissions."""

    if definition is None or not isinstance(
        definition.implementation, AddOnInstruction
    ):
        return ()
    instruction = definition.implementation
    parameters_by_name = {
        parameter.name.casefold(): parameter
        for parameter in instruction.parameters.values()
    }
    required = [
        parameter
        for parameter in instruction.parameters.values()
        if parameter.required is True
    ]
    bindings: list[SoftwareCallArgumentBinding] = []
    positional_index = 0
    instance_consumed = False
    for argument in call.arguments:
        target_tag = program.get_tag(argument.source) if program else None
        target_tag_scope = (
            SoftwareTagScope.PROGRAM if target_tag is not None else None
        )
        if target_tag is None:
            controller_matches = [
                (tag, scope)
                for tag, scope in controller_tags
                if tag.name.casefold() == argument.source.casefold()
            ]
            if len(controller_matches) == 1:
                target_tag, target_tag_scope = controller_matches[0]
        target_module, module_path, module_direction = _resolve_module_operand(
            argument.source,
            modules,
        )
        target_connection = (
            target_module.connections[0]
            if target_module is not None
            and len(target_module.connections) == 1
            else None
        )
        if (
            not instance_consumed
            and argument.name is None
            and target_tag is instance_tag
            and instance_tag is not None
        ):
            bindings.append(
                SoftwareCallArgumentBinding(
                    argument=argument,
                    role=SoftwareCallBindingRole.INSTANCE,
                    target_tag=target_tag,
                    target_tag_scope=target_tag_scope,
                )
            )
            instance_consumed = True
            continue
        parameter = (
            parameters_by_name.get(argument.name.casefold())
            if argument.name is not None
            else (
                required[positional_index]
                if positional_index < len(required)
                else None
            )
        )
        if argument.name is None:
            positional_index += 1
        bindings.append(
            SoftwareCallArgumentBinding(
                argument=argument,
                role=(
                    SoftwareCallBindingRole.PARAMETER
                    if parameter is not None
                    else SoftwareCallBindingRole.UNMATCHED
                ),
                parameter=parameter,
                target_tag=target_tag,
                target_tag_scope=target_tag_scope,
                target_module=target_module,
                target_connection=target_connection,
                module_data_path=module_path,
                module_data_direction=module_direction,
                flow=_parameter_flow(parameter.usage)
                if parameter is not None
                else SoftwareParameterFlow.UNKNOWN,
            )
        )
        if parameter is None:
            diagnostics.append(
                L5XCorpusDiagnostic(
                    "unmatched_software_call_argument",
                    f"call to {call.callee!r} has unmatched operand "
                    f"{argument.source!r}",
                    (call.source_path,) if call.source_path is not None else (),
                )
            )
    bound_parameters = {
        binding.parameter.name.casefold()
        for binding in bindings
        if binding.parameter is not None
    }
    for parameter in required:
        if parameter.name.casefold() not in bound_parameters:
            diagnostics.append(
                L5XCorpusDiagnostic(
                    "required_software_parameter_unbound",
                    f"call to {call.callee!r} does not bind required "
                    f"parameter {parameter.name!r}",
                    (call.source_path,) if call.source_path is not None else (),
                )
            )
    return tuple(bindings)


def _controller_tags_for_call(
    document: L5XDocument | None,
    workspace: ControllerWorkspace | None,
) -> tuple[tuple[Tag, SoftwareTagScope], ...]:
    """Return the strongest controller-tag evidence available to one call."""

    if document is not None and document.context_controller_tags:
        return tuple(
            (tag, SoftwareTagScope.CONTROLLER_CONTEXT)
            for tag in document.context_controller_tags
        )
    if workspace is None or workspace.controller_document is None:
        return ()
    controller = workspace.controller_document.target
    if not isinstance(controller, Controller):
        return ()
    return tuple(
        (tag, SoftwareTagScope.CONTROLLER)
        for tag in controller.iter_tags()
    )


def _workspace_modules(
    workspace: ControllerWorkspace | None,
) -> tuple[Module, ...]:
    """Return all modules explicitly owned by one resolved PLC workspace."""

    if workspace is None:
        return ()
    roots: list[Module] = []
    if workspace.controller_document is not None:
        controller = workspace.controller_document.target
        if isinstance(controller, Controller):
            roots.extend(controller.unplaced_modules)
            roots.extend(
                module
                for chassis in controller.iter_chassis()
                for module in chassis.iter_modules()
            )
    roots.extend(
        document.target
        for document in workspace.documents
        if document.target_type is L5XTargetType.MODULE
        and isinstance(document.target, Module)
    )
    modules: list[Module] = []
    pending = list(roots)
    while pending:
        module = pending.pop(0)
        modules.append(module)
        pending.extend(module.child_modules)
    return tuple(modules)


def _resolve_module_operand(
    operand: str,
    modules: tuple[Module, ...],
) -> tuple[Module | None, str | None, ModuleDataDirection | None]:
    """Resolve a module data operand by the longest exact module-name prefix."""

    exact = [
        module
        for module in modules
        if operand.casefold() == module.name.casefold()
    ]
    if len(exact) == 1:
        return exact[0], None, ModuleDataDirection.UNKNOWN
    if len(exact) > 1:
        return None, None, None
    matches = sorted(
        (
            module
            for module in modules
            if operand.casefold().startswith(f"{module.name}:".casefold())
        ),
        key=lambda module: len(module.name),
        reverse=True,
    )
    if not matches:
        return None, None, None
    longest_length = len(matches[0].name)
    longest = [
        module for module in matches if len(module.name) == longest_length
    ]
    if len(longest) != 1:
        return None, None, None
    module = longest[0]
    path = operand[len(module.name) + 1 :]
    area = path.partition(".")[0].casefold()
    direction = {
        "i": ModuleDataDirection.INPUT,
        "o": ModuleDataDirection.OUTPUT,
        "c": ModuleDataDirection.CONFIGURATION,
        "s": ModuleDataDirection.STATUS,
    }.get(area, ModuleDataDirection.UNKNOWN)
    return module, path, direction


def _parameter_flow(usage: str | None) -> SoftwareParameterFlow:
    """Normalize documented AOI Usage without interpreting parameter names."""

    normalized = (usage or "").casefold()
    return {
        "input": SoftwareParameterFlow.INPUT,
        "output": SoftwareParameterFlow.OUTPUT,
        "inout": SoftwareParameterFlow.IN_OUT,
    }.get(normalized, SoftwareParameterFlow.UNKNOWN)


def _software_index(
    components: list[SoftwareComponent],
) -> dict[str, tuple[SoftwareComponent, ...]]:
    indexed: dict[str, list[SoftwareComponent]] = defaultdict(list)
    for component in components:
        indexed[component.name.casefold()].append(component)
    return {
        name: tuple(matches)
        for name, matches in sorted(indexed.items())
    }


def _resolve_software_instances(
    workspaces: list[ControllerWorkspace],
    software_index: dict[str, tuple[SoftwareComponent, ...]],
    diagnostics: list[L5XCorpusDiagnostic],
) -> list[SoftwareBinding]:
    """Bind tags only when their AOI definition name is unique."""

    bindings: list[SoftwareBinding] = []
    for name, definitions in software_index.items():
        if len(definitions) > 1:
            diagnostics.append(
                L5XCorpusDiagnostic(
                    "duplicate_software_definition",
                    f"software definition {name!r} occurs "
                    f"{len(definitions)} times",
                )
            )
    for workspace in workspaces:
        for program, source_path in _workspace_programs(workspace):
            for tag in program.iter_tags():
                if tag.data_type is None:
                    continue
                definitions = software_index.get(tag.data_type.casefold(), ())
                if not definitions:
                    continue
                if len(definitions) > 1:
                    diagnostics.append(
                        L5XCorpusDiagnostic(
                            "ambiguous_software_instance",
                            f"tag {program.name}.{tag.name} datatype "
                            f"{tag.data_type!r} matches "
                            f"{len(definitions)} definitions",
                            (source_path,),
                        )
                    )
                    continue
                definition = next(iter(definitions))
                binding = definition.bind_tag(
                    tag,
                    role=SoftwareBindingRole.INSTANCE_TAG,
                    evidence=(
                        f"{source_path.name}: tag {program.name}.{tag.name} "
                        f"declares DataType={tag.data_type}"
                    ),
                    metadata={
                        "workspace_key": workspace.key,
                        "controller_name": workspace.controller_name,
                        "program_name": program.name,
                        "source_path": str(source_path),
                    },
                )
                bindings.append(binding)
    return bindings


def _workspace_programs(
    workspace: ControllerWorkspace,
) -> list[tuple[Program, Path]]:
    programs: list[tuple[Program, Path]] = []
    if workspace.controller_document is not None:
        target = workspace.controller_document.target
        if isinstance(target, Controller):
            programs.extend(
                (program, workspace.controller_document.source_path)
                for program in target.iter_programs()
            )
    programs.extend(
        (document.target, document.source_path)
        for document in workspace.documents
        if document.target_type is L5XTargetType.PROGRAM
        and isinstance(document.target, Program)
    )
    return programs
