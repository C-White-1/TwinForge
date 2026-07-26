"""Human-readable reports generated from the vendor-neutral TwinForge model."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from twinforge.model import Controller, Module, Program, Routine, Tag


@dataclass(frozen=True)
class TextReportBundle:
    """A deterministic collection of report filenames and UTF-8 text."""

    files: dict[str, str]

    def write_to(self, directory: str | Path) -> tuple[Path, ...]:
        """Create *directory* and write every report, replacing old reports."""

        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for filename, content in self.files.items():
            path = destination / filename
            path.write_text(content, encoding="utf-8")
            written.append(path)
        return tuple(written)


class TextReportExporter:
    """Render engineering reports without returning to the source XML."""

    def export(self, controller: Controller) -> TextReportBundle:
        """Generate the currently supported report set for one controller."""

        return TextReportBundle(
            {
                "controller.txt": self._controller(controller),
                "tags.txt": self._tags(controller),
                "datatypes.txt": self._datatypes(controller),
                "add_on_instructions.txt": self._add_on_instructions(
                    controller
                ),
                "modules.txt": self._modules(controller),
                "tasks.txt": self._tasks(controller),
                "programs.txt": self._programs(controller),
            }
        )

    def _controller(self, controller: Controller) -> str:
        identity = controller.identity
        rows = [
            ("Name", controller.name),
            ("Product", identity.product_name),
            ("Vendor", str(identity.vendor) if identity.vendor else None),
            ("Product type", identity.product_type_name or identity.product_type),
            ("Product code", identity.product_code),
            ("Revision", identity.revision),
            ("Serial", identity.serial),
            ("Chassis", len(controller.chassis)),
            ("Modules", sum(1 for _ in _modules(controller))),
            ("Controller tags", len(controller.tags)),
            ("Datatypes", len(controller.datatypes)),
            ("Add-On Instructions", len(controller.add_on_instructions)),
            ("Programs", len(controller.programs)),
            ("Tasks", len(controller.tasks)),
        ]
        return _report("CONTROLLER SUMMARY", _key_values(rows))

    def _tags(self, controller: Controller) -> str:
        sections = [
            _tag_section("CONTROLLER TAGS", controller.tags.values())
        ]
        for program in sorted(controller.programs.values(), key=lambda item: item.name):
            sections.append(
                _tag_section(
                    f"PROGRAM TAGS: {program.name}",
                    program.tags.values(),
                )
            )
        return "\n\n".join(sections).rstrip() + "\n"

    def _datatypes(self, controller: Controller) -> str:
        lines = [
            "DATATYPES",
            "=" * 80,
            f"Count: {len(controller.datatypes)}",
        ]
        for datatype in sorted(
            controller.datatypes.values(), key=lambda item: item.name
        ):
            lines.extend(
                [
                    "",
                    f"{datatype.name} "
                    f"[family={_display(datatype.family)}, "
                    f"class={_display(datatype.classification)}]",
                ]
            )
            if datatype.description:
                lines.append(f"  Description: {datatype.description}")
            member_rows = [
                [
                    member.name,
                    _display(member.data_type_name),
                    _display(member.dimension),
                    _display(member.radix),
                    _display(member.description),
                ]
                for member in datatype.members
            ]
            lines.extend(
                _table(
                    ("Member", "Data type", "Dimension", "Radix", "Description"),
                    member_rows,
                    indent="  ",
                )
            )
        return "\n".join(lines).rstrip() + "\n"

    def _add_on_instructions(self, controller: Controller) -> str:
        lines = [
            "ADD-ON INSTRUCTIONS",
            "=" * 80,
            f"Count: {len(controller.add_on_instructions)}",
        ]
        for instruction in sorted(
            controller.add_on_instructions.values(),
            key=lambda item: item.name,
        ):
            lines.extend(
                [
                    "",
                    f"Instruction: {instruction.name}",
                    *_key_values(
                        [
                            ("Revision", instruction.revision),
                            ("Vendor", instruction.vendor),
                            ("Description", instruction.description),
                            ("Execute prescan", instruction.execute_prescan),
                            ("Execute postscan", instruction.execute_postscan),
                            (
                                "Execute EnableInFalse",
                                instruction.execute_enable_in_false,
                            ),
                        ],
                        indent="  ",
                    ),
                    "",
                    "  Parameters:",
                    *_table(
                        (
                            "Name",
                            "Usage",
                            "Data type",
                            "Dimensions",
                            "Alias for",
                            "Required",
                            "Visible",
                            "Constant",
                            "Default",
                            "Description",
                        ),
                        [
                            [
                                parameter.name,
                                _display(parameter.usage),
                                _display(parameter.data_type),
                                _display(parameter.dimensions),
                                _display(parameter.alias_for),
                                _display(parameter.required),
                                _display(parameter.visible),
                                _display(parameter.constant),
                                _display(
                                    parameter.default_value.lexical_value
                                    if parameter.default_value
                                    else None
                                ),
                                _display(parameter.description),
                            ]
                            for parameter in instruction.parameters.values()
                        ],
                        indent="    ",
                    ),
                ]
            )
            if instruction.local_tags:
                lines.extend(
                    [
                        "",
                        "  Local tags:",
                        *_table(
                            (
                                "Name",
                                "Data type",
                                "Dimensions",
                                "Default",
                                "External access",
                                "Description",
                            ),
                            [
                                [
                                    tag.name,
                                    _display(tag.data_type),
                                    _display(tag.dimensions),
                                    _display(
                                        tag.initial_value.lexical_value
                                        if tag.initial_value
                                        else None
                                    ),
                                    _display(tag.external_access),
                                    _display(tag.description),
                                ]
                                for tag in instruction.local_tags.values()
                            ],
                            indent="    ",
                        ),
                    ]
                )
            if instruction.dependencies:
                lines.extend(
                    [
                        "",
                        "  Dependencies:",
                        *[
                            (
                                f"    {dependency.dependency_type}: "
                                f"{dependency.name}"
                                + (
                                    " [resolved]"
                                    if dependency.target is not None
                                    else " [unresolved]"
                                )
                            )
                            for dependency in instruction.dependencies
                        ],
                    ]
                )
            for routine in instruction.routines.values():
                lines.extend(_routine_lines(routine, indent="  "))
        return "\n".join(lines).rstrip() + "\n"

    def _modules(self, controller: Controller) -> str:
        rows: list[list[str]] = []
        for module in _modules(controller):
            capability = module.capability
            rows.append(
                [
                    _display(module.slot if module.slot is not None else module.address),
                    module.name,
                    module.catalog,
                    str(module.identity.vendor) if module.identity.vendor else "",
                    _display(capability.signal_type.value if capability else None),
                    _display(capability.direction.value if capability else None),
                    _display(capability.nominal_channel_count if capability else None),
                    _display(
                        capability.configured_channel_count if capability else None
                    ),
                    _display(
                        module.electronic_key.mode.value
                        if module.electronic_key and module.electronic_key.mode
                        else None
                    ),
                ]
            )
        lines = [
            "MODULE AND I/O INVENTORY",
            "=" * 80,
            f"Count: {len(rows)}",
            "",
            *_table(
                (
                    "Slot/address",
                    "Name",
                    "Catalog",
                    "Vendor",
                    "Signal",
                    "Direction",
                    "Nominal",
                    "Configured",
                    "Keying",
                ),
                rows,
            ),
        ]
        return "\n".join(lines).rstrip() + "\n"

    def _tasks(self, controller: Controller) -> str:
        lines = [
            "TASK SCHEDULE",
            "=" * 80,
            f"Count: {len(controller.tasks)}",
        ]
        for task in sorted(controller.tasks.values(), key=lambda item: item.name):
            resolved = ", ".join(program.name for program in task.scheduled_programs)
            unresolved = [
                name
                for name in task.scheduled_program_names
                if name not in {program.name for program in task.scheduled_programs}
            ]
            lines.extend(
                [
                    "",
                    f"Task: {task.name}",
                    *_key_values(
                        [
                            ("Type", task.task_type),
                            ("Rate (ms)", task.rate),
                            ("Priority", task.priority),
                            ("Watchdog (ms)", task.watchdog),
                            ("Inhibited", task.inhibited),
                            ("Description", task.description),
                            ("Scheduled programs", resolved),
                            ("Unresolved programs", ", ".join(unresolved)),
                        ],
                        indent="  ",
                    ),
                ]
            )
        return "\n".join(lines).rstrip() + "\n"

    def _programs(self, controller: Controller) -> str:
        lines = [
            "PROGRAMS AND ROUTINES",
            "=" * 80,
            f"Programs: {len(controller.programs)}",
        ]
        for program in sorted(controller.programs.values(), key=lambda item: item.name):
            lines.extend(_program_lines(program))
        return "\n".join(lines).rstrip() + "\n"


def _tag_section(title: str, tags: Iterable[Tag]) -> str:
    tag_list = sorted(tags, key=lambda item: item.name)
    rows = [
        [
            tag.name,
            "Alias" if tag.alias_for else _display(tag.tag_type),
            _display(tag.data_type),
            _display(tag.alias_for),
            _display(tag.initial_value.lexical_value if tag.initial_value else None),
            _display(tag.engineering_unit.symbol if tag.engineering_unit else None),
            (
                f"{tag.engineering_range.lower:g}..{tag.engineering_range.upper:g}"
                if tag.engineering_range
                else ""
            ),
            _display(tag.description),
        ]
        for tag in tag_list
    ]
    return "\n".join(
        [
            title,
            "=" * 80,
            f"Count: {len(tag_list)}",
            "",
            *_table(
                (
                    "Name",
                    "Kind",
                    "Data type",
                    "Alias for",
                    "Initial value",
                    "Unit",
                    "Range",
                    "Description",
                ),
                rows,
            ),
        ]
    )


def _program_lines(program: Program) -> list[str]:
    lines = [
        "",
        f"Program: {program.name}",
        f"  Main routine: "
        f"{program.main_routine.name if program.main_routine else ''}",
        f"  Disabled: {_display(program.disabled)}",
        f"  Local tags: {len(program.tags)}",
        f"  Routines: {len(program.routines)}",
    ]
    for routine in sorted(program.routines.values(), key=lambda item: item.name):
        lines.extend(_routine_lines(routine, indent="  "))
    return lines


def _routine_lines(routine: Routine, *, indent: str) -> list[str]:
    lines = [
        "",
        f"{indent}Routine: {routine.name} "
        f"[{_display(routine.language)}]",
    ]
    if routine.language == "RLL":
        for rung in routine.ladder_rungs:
            lines.append(
                f"{indent}  Rung {_display(rung.number)} "
                f"[{_display(rung.rung_type)}]"
            )
            if rung.comment:
                lines.append(f"{indent}    Comment: {rung.comment}")
            lines.append(f"{indent}    Logic: {_display(rung.text)}")
    elif routine.language == "ST":
        for source_line in routine.structured_text_lines:
            lines.append(
                f"{indent}  {source_line.number}: {source_line.text}"
            )
    else:
        lines.append(
            f"{indent}  Body conversion/reporting is not implemented."
        )
    return lines


def _modules(controller: Controller) -> Iterator[Module]:
    for chassis in sorted(controller.chassis.values(), key=lambda item: item.name):
        for module in sorted(
            chassis.modules.values(),
            key=lambda item: (
                item.slot is None,
                item.slot if item.slot is not None else 0,
                item.name,
            ),
        ):
            yield from _module_tree(module)
    for module in sorted(controller.unplaced_modules, key=lambda item: item.name):
        yield from _module_tree(module)


def _module_tree(module: Module) -> Iterator[Module]:
    yield module
    for child in sorted(module.child_modules, key=lambda item: item.name):
        yield from _module_tree(child)


def _report(title: str, lines: list[str]) -> str:
    return "\n".join([title, "=" * 80, *lines]).rstrip() + "\n"


def _key_values(
    rows: list[tuple[str, object | None]],
    *,
    indent: str = "",
) -> list[str]:
    width = max(len(label) for label, _ in rows)
    return [
        f"{indent}{label:<{width}} : {_display(value)}"
        for label, value in rows
    ]


def _table(
    headers: tuple[str, ...],
    rows: list[list[str]],
    *,
    indent: str = "",
) -> list[str]:
    widths = [
        max(
            [len(headers[index]), *(len(row[index]) for row in rows)]
        )
        for index in range(len(headers))
    ]

    def render(values: tuple[str, ...] | list[str]) -> str:
        return indent + " | ".join(
            value.ljust(widths[index]) for index, value in enumerate(values)
        ).rstrip()

    return [
        render(headers),
        indent + "-+-".join("-" * width for width in widths),
        *(render(row) for row in rows),
    ]


def _display(value: object | None) -> str:
    return "" if value is None else str(value)
