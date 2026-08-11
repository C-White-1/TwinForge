from __future__ import annotations

from copy import deepcopy

from twinforge.converters.diagnostics import (
    ConversionDiagnostic,
    DiagnosticSeverity,
)
from twinforge.model import Chassis, Controller, Identity, Module, Revision
from twinforge.parsers.l5x.capture import CapturedSection

from .module import convert_module
from .add_on_instruction import convert_add_on_instruction
from .engineering_unit import resolve_engineering_units
from .datatype import convert_datatype, resolve_datatype_references
from .program import convert_program
from .source_extension import captured_to_source_extension
from .tag import convert_tag
from .task import convert_task


def convert_controller(
    section: CapturedSection,
    *,
    diagnostics: list[ConversionDiagnostic] | None = None,
) -> Controller:
    """Convert a captured L5X controller and resolve its module topology."""

    if section.tag != "Controller":
        raise ValueError(f"expected a Controller section, got {section.tag!r}")

    module_sections = [
        module
        for modules in section.elements.get("Modules", [])
        for module in modules.elements.get("Module", [])
    ]
    sections_by_name = _index_module_sections(module_sections, diagnostics)
    modules_by_name = {
        name: convert_module(module_section, diagnostics=diagnostics)
        for name, module_section in sections_by_name.items()
    }
    roots = [
        name
        for name, module_section in sections_by_name.items()
        if module_section.attributes.get("ParentModule") in (None, name)
    ]

    identity = _controller_identity(section, roots, modules_by_name, diagnostics)
    controller = Controller(
        name=section.attributes.get("Name", ""),
        identity=identity,
        source_extensions=[captured_to_source_extension(section)],
    )

    chassis_by_root: dict[str, Chassis] = {}
    for root_name in roots:
        root_module = modules_by_name[root_name]
        chassis = Chassis(
            name=f"{root_name} Chassis",
            source_extensions=[captured_to_source_extension(sections_by_name[root_name])],
        )
        if root_module.slot is None:
            controller.add_unplaced_module(root_module)
            if sections_by_name[root_name].attributes.get("Use") not in {
                "Context",
                "Reference",
            }:
                _topology_diagnostic(
                    diagnostics,
                    "root_without_slot",
                    (
                        f"root module {root_name!r} does not have "
                        "a numeric slot"
                    ),
                    root_name,
                )
            continue
        controller.add_chassis(chassis)
        chassis.add_module(root_module)
        chassis_by_root[root_name] = chassis

    for name, module in modules_by_name.items():
        if name in roots:
            continue
        parent_name = sections_by_name[name].attributes.get("ParentModule")
        if parent_name not in modules_by_name:
            controller.add_unplaced_module(module)
            _topology_diagnostic(
                diagnostics,
                "unknown_module_parent",
                f"module {name!r} references unknown parent {parent_name!r}",
                name,
            )
            continue
        try:
            root_name = _root_name(name, sections_by_name)
        except ValueError as error:
            controller.add_unplaced_module(module)
            _topology_diagnostic(
                diagnostics,
                "module_parent_cycle",
                str(error),
                name,
            )
            continue
        parent = modules_by_name[parent_name]
        if (
            parent_name == root_name
            and module.slot is not None
            and root_name in chassis_by_root
        ):
            try:
                chassis_by_root[root_name].add_module(module)
            except ValueError as error:
                controller.add_unplaced_module(module)
                _topology_diagnostic(
                    diagnostics,
                    "duplicate_chassis_slot",
                    str(error),
                    name,
                )
        else:
            parent.add_child_module(module)

    for datatypes in section.elements.get("DataTypes", []):
        for datatype_section in datatypes.elements.get("DataType", []):
            datatype = convert_datatype(datatype_section, diagnostics=diagnostics)
            if not datatype.name:
                continue
            if datatype.name in controller.datatypes:
                _topology_diagnostic(
                    diagnostics,
                    "duplicate_datatype_name",
                    f"duplicate data type name {datatype.name!r}",
                    datatype.name,
                )
                continue
            controller.add_datatype(datatype)

    for definitions in section.elements.get(
        "AddOnInstructionDefinitions", []
    ):
        for definition_section in definitions.elements.get(
            "AddOnInstructionDefinition", []
        ):
            instruction = convert_add_on_instruction(
                definition_section, diagnostics=diagnostics
            )
            if not instruction.name:
                continue
            if instruction.name in controller.add_on_instructions:
                _topology_diagnostic(
                    diagnostics,
                    "duplicate_aoi_name",
                    (
                        "duplicate Add-On Instruction name "
                        f"{instruction.name!r}"
                    ),
                    instruction.name,
                )
                continue
            controller.add_add_on_instruction(instruction)

    _resolve_aoi_dependencies(controller, diagnostics)

    for programs in section.elements.get("Programs", []):
        for program_section in programs.elements.get("Program", []):
            program = convert_program(program_section, diagnostics=diagnostics)
            if program.name in controller.programs:
                _topology_diagnostic(
                    diagnostics,
                    "duplicate_program_name",
                    f"duplicate program name {program.name!r}",
                    program.name,
                )
                continue
            controller.add_program(program)

    for tags in section.elements.get("Tags", []):
        for tag_section in tags.elements.get("Tag", []):
            tag = convert_tag(tag_section, diagnostics=diagnostics)
            if not tag.name:
                continue
            if tag.name in controller.tags:
                _topology_diagnostic(
                    diagnostics,
                    "duplicate_tag_name",
                    f"duplicate controller tag name {tag.name!r}",
                    tag.name,
                )
                continue
            controller.add_tag(tag)

    for tasks in section.elements.get("Tasks", []):
        for task_section in tasks.elements.get("Task", []):
            task = convert_task(
                task_section,
                controller.programs,
                diagnostics=diagnostics,
            )
            if not task.name:
                continue
            if task.name in controller.tasks:
                _topology_diagnostic(
                    diagnostics,
                    "duplicate_task_name",
                    f"duplicate task name {task.name!r}",
                    task.name,
                )
                continue
            controller.add_task(task)

    resolve_datatype_references(controller, diagnostics)
    resolve_engineering_units(controller, diagnostics=diagnostics)

    return controller


def _resolve_aoi_dependencies(
    controller: Controller,
    diagnostics: list[ConversionDiagnostic] | None,
) -> None:
    targets = {
        "DataType": controller.datatypes,
        "AddOnInstructionDefinition": controller.add_on_instructions,
    }
    for instruction in controller.add_on_instructions.values():
        for dependency in instruction.dependencies:
            candidates = targets.get(dependency.dependency_type)
            if candidates is None:
                continue
            dependency.target = candidates.get(dependency.name)
            if dependency.target is None:
                _topology_diagnostic(
                    diagnostics,
                    "unresolved_aoi_dependency",
                    (
                        f"AOI {instruction.name!r} references unknown "
                        f"{dependency.dependency_type} "
                        f"{dependency.name!r}"
                    ),
                    instruction.name,
                )


def _index_module_sections(
    sections: list[CapturedSection],
    diagnostics: list[ConversionDiagnostic] | None,
) -> dict[str, CapturedSection]:
    indexed: dict[str, CapturedSection] = {}
    for section in sections:
        name = section.attributes.get("Name")
        if not name:
            _topology_diagnostic(
                diagnostics,
                "module_missing_name",
                "module is missing its Name attribute",
                None,
            )
            continue
        if name in indexed:
            _topology_diagnostic(
                diagnostics,
                "duplicate_module_name",
                f"duplicate module name {name!r}",
                name,
            )
            continue
        indexed[name] = section
    return indexed


def _root_name(
    name: str,
    sections: dict[str, CapturedSection],
) -> str:
    visited: set[str] = set()
    current = name
    while True:
        if current in visited:
            raise ValueError(f"module parent cycle detected at {current!r}")
        visited.add(current)
        parent = sections[current].attributes.get("ParentModule")
        if parent in (None, current):
            return current
        if parent not in sections:
            raise ValueError(f"module {current!r} references unknown parent {parent!r}")
        current = parent


def _controller_identity(
    section: CapturedSection,
    roots: list[str],
    modules: dict[str, Module],
    diagnostics: list[ConversionDiagnostic] | None,
) -> Identity:
    identity = deepcopy(modules[roots[0]].identity) if roots else Identity()
    identity.product_name = section.attributes.get("ProcessorType")
    major = _optional_int(
        section.attributes.get("MajorRev"), "MajorRev", section, diagnostics
    )
    minor = _optional_int(
        section.attributes.get("MinorRev"), "MinorRev", section, diagnostics
    )
    if major is not None and minor is not None:
        identity.revision = Revision(major, minor)
    identity.source_extensions.append(captured_to_source_extension(section))
    return identity


def _optional_int(
    value: str | None,
    field: str,
    section: CapturedSection,
    diagnostics: list[ConversionDiagnostic] | None,
) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        if diagnostics is not None:
            diagnostics.append(
                ConversionDiagnostic(
                    severity=DiagnosticSeverity.WARNING,
                    code="invalid_integer",
                    message=f"{field} must be an integer, got {value!r}",
                    object_name=section.attributes.get("Name"),
                    field=field,
                    raw_value=value,
                )
            )
        return None


def _topology_diagnostic(
    diagnostics: list[ConversionDiagnostic] | None,
    code: str,
    message: str,
    object_name: str | None,
) -> None:
    if diagnostics is None:
        return
    diagnostics.append(
        ConversionDiagnostic(
            severity=DiagnosticSeverity.ERROR,
            code=code,
            message=message,
            object_name=object_name,
        )
    )
