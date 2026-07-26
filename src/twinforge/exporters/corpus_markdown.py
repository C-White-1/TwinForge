"""Deterministic evidence reports for multi-document L5X corpora."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from twinforge.assembly import AssembledSoftwareDevice
from twinforge.model import DeviceParameterDefinition, ObservedParameterAccess
from twinforge.parsers.l5x import L5XCorpus


class CorpusMarkdownExporter:
    """Render ownership and resolution evidence without reparsing source XML."""

    def export(
        self,
        corpus: L5XCorpus,
        *,
        devices: Iterable[AssembledSoftwareDevice] = (),
        title: str = "L5X corpus evidence report",
    ) -> str:
        """Return a stable Markdown report for review or version control."""

        assembled_devices = tuple(devices)
        lines = [
            f"# {title}",
            "",
            "## Summary",
            "",
            f"- Documents: {len(corpus.documents)}",
            f"- Controller workspaces: {len(corpus.workspaces)}",
            f"- Candidate calls: {len(corpus.call_sites)}",
            f"- Resolved software calls: {len(corpus.resolved_calls)}",
            (
                "- Software/module assemblies: "
                f"{len(corpus.software_module_assemblies)}"
            ),
            f"- Assembled devices: {len(assembled_devices)}",
            f"- Unassigned documents: {len(corpus.unassigned_documents)}",
            f"- Diagnostics: {len(corpus.diagnostics)}",
            "",
            "## Documents",
            "",
            "| Target type | Target name | Source file |",
            "| --- | --- | --- |",
        ]
        lines.extend(
            f"| {_cell(document.target_type.value)} "
            f"| {_cell(document.target_name)} "
            f"| {_cell(document.source_path.name)} |"
            for document in corpus.documents
        )
        lines.extend(["", "## Controller workspaces", ""])
        for workspace in corpus.workspaces:
            lines.extend(
                [
                    f"### {_text(workspace.controller_name)}",
                    "",
                    f"- Key: `{_code(workspace.key)}`",
                    f"- Evidence: `{workspace.evidence.value}`",
                    f"- Confirmed by controller export: "
                    f"{_yes_no(workspace.confirmed)}",
                    "- Documents: "
                    + ", ".join(
                        f"`{_code(document.source_path.name)}`"
                        for document in workspace.documents
                    ),
                    "",
                ]
            )
        lines.extend(["## Resolved software calls", ""])
        if not corpus.resolved_calls:
            lines.extend(["None.", ""])
        for resolved in corpus.resolved_calls:
            call = resolved.call_site
            location = (
                f"rung {call.rung_number}"
                if call.rung_number is not None
                else f"line {call.line_number}"
            )
            lines.extend(
                [
                    f"### `{_code(resolved.definition.name)}` in "
                    f"`{_code(call.program_name)}.{_code(call.routine_name)}`",
                    "",
                    f"- Source: `{_code(call.source_path.name)}`"
                    if call.source_path is not None
                    else "- Source: unknown",
                    f"- Location: {location}",
                    "- Instance tag: "
                    + (
                        f"`{_code(resolved.instance_tag.name)}`"
                        if resolved.instance_tag is not None
                        else "unresolved"
                    ),
                    f"- Source text: `{_code(call.source_text)}`",
                    "",
                    "| Operand | Role | Parameter | Flow | Tag | Scope | "
                    "Module | "
                    "Module area |",
                    "| --- | --- | --- | --- | --- | --- | --- | --- |",
                ]
            )
            for binding in resolved.argument_bindings:
                lines.append(
                    f"| {_cell(binding.argument.source)} "
                    f"| {binding.role.value} "
                    f"| {_cell(binding.parameter.name if binding.parameter else None)} "
                    f"| {binding.flow.value} "
                    f"| {_cell(binding.target_tag.name if binding.target_tag else None)} "
                    f"| {_cell(binding.target_tag_scope.value if binding.target_tag_scope else None)} "
                    f"| {_cell(binding.target_module.name if binding.target_module else None)} "
                    f"| {_cell(binding.module_data_direction.value if binding.module_data_direction else None)} |"
                )
            lines.append("")
        lines.extend(["## Assembled devices", ""])
        if not assembled_devices:
            lines.extend(["None.", ""])
        for result in assembled_devices:
            device = result.device
            lines.extend(
                [
                    f"### {_text(device.name)}",
                    "",
                    f"- Provider: `{_code(result.provider)}`",
                    f"- Type: `{device.device_type.value}`",
                    f"- Manufacturer: {_text(device.manufacturer)}",
                    f"- Model: {_text(device.model)}",
                    "- Modules: "
                    + ", ".join(
                        f"`{_code(binding.module.name)}`"
                        for binding in device.module_bindings
                    ),
                    "- Identity scopes: represented device identity is "
                    "separate from controller module identity",
                ]
            )
            for binding in device.module_bindings:
                module_vendor = binding.module.identity.vendor
                lines.append(
                    f"  - Module `{_code(binding.module.name)}` identity: "
                    f"{_text(module_vendor)} "
                    "(controller representation)"
                )
            for interface in device.communication_interfaces:
                lines.append(
                    f"- Interface: {interface.protocol or 'unknown'} at "
                    f"`{_code(interface.address)}`"
                )
                for connection in interface.connections:
                    lines.append(
                        "  - Connection "
                        f"`{_code(connection.name)}`: "
                        f"RPI {connection.requested_packet_interval_microseconds} µs, "
                        f"input {connection.input_size_bytes} bytes, "
                        f"output {connection.output_size_bytes} bytes, "
                        f"unicast {_yes_no(connection.unicast is True)}"
                    )
                for service in interface.services:
                    lines.append(
                        f"  - Service `{_code(service.name)}`: "
                        f"`{_code(service.service_type)}`, "
                        f"code `{_code(_hex(service.service_code))}`, "
                        f"class `{_code(service.object_class)}`, "
                        f"configured instance `{_code(service.instance)}`, "
                        f"configured attribute `{_code(service.attribute)}`"
                    )
                    lines.append(
                        "    - Configured transfer: "
                        f"{service.requested_length} bytes via "
                        f"`{_code(service.connection_path)}`; "
                        f"local `{_code(service.local_element)}`; "
                        f"destination `{_code(service.destination_tag)}`"
                    )
                    lines.append(
                        "    - Runtime mutable: "
                        f"{_yes_no(service.runtime_mutable is True)}; "
                        f"source `{_code(service.configuration_source)}`"
                    )
            read_candidates = device.metadata.get(
                "observed_bulk_read_parameter_candidates"
            )
            write_candidates = device.metadata.get(
                "observed_write_parameter_candidates"
            )
            if isinstance(read_candidates, tuple):
                lines.append(
                    "- Observed bulk-read parameter candidates "
                    f"({len(read_candidates)}): "
                    + _number_ranges(read_candidates)
                )
            if isinstance(write_candidates, tuple):
                lines.append(
                    "- Observed write parameter candidates "
                    f"({len(write_candidates)}): "
                    + _number_ranges(write_candidates)
                )
            _append_parameter_inventory(lines, device.observed_parameters)
            _append_evidence(lines, result.source.evidence)
            lines.append("")
        lines.extend(["## Diagnostics and unresolved evidence", ""])
        if not corpus.diagnostics and not corpus.unassigned_documents:
            lines.extend(["No corpus diagnostics or unassigned documents.", ""])
        else:
            lines.extend(
                f"- `{diagnostic.code}`: {_text(diagnostic.message)}"
                for diagnostic in corpus.diagnostics
            )
            lines.extend(
                f"- Unassigned: `{_code(document.source_path.name)}`"
                for document in corpus.unassigned_documents
            )
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def _cell(value: object | None) -> str:
    return _text(value).replace("|", "\\|").replace("\n", "<br>")


def _text(value: object | None) -> str:
    return "—" if value is None or value == "" else str(value)


def _code(value: object | None) -> str:
    return _text(value).replace("`", "\\`").replace("\n", " ")


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _hex(value: int | None) -> str | None:
    return f"0x{value:02X}" if value is not None else None


def _number_ranges(values: tuple[object, ...]) -> str:
    numbers = [value for value in values if isinstance(value, int)]
    if not numbers:
        return "—"
    ranges: list[str] = []
    start = previous = numbers[0]
    for number in numbers[1:]:
        if number == previous + 1:
            previous = number
            continue
        ranges.append(
            str(start) if start == previous else f"{start}–{previous}"
        )
        start = previous = number
    ranges.append(str(start) if start == previous else f"{start}–{previous}")
    return ", ".join(ranges)


def _append_parameter_inventory(
    lines: list[str],
    parameters: list[ObservedParameterAccess],
) -> None:
    """Append normalized parameter evidence without vendor-specific inference."""

    if not parameters:
        return
    ordered = sorted(parameters, key=lambda item: item.number)
    group_counts = Counter(
        parameter.group_name or parameter.group_prefix or "Unclassified"
        for parameter in ordered
    )
    lines.extend(
        [
            "- Parameter groups: "
            + ", ".join(
                f"{group} ({count})"
                for group, count in sorted(group_counts.items())
            ),
        ]
    )
    references = sorted(
        {
            parameter.reference
            for parameter in ordered
            if parameter.reference is not None
        }
    )
    if references:
        lines.append(
            "- Parameter references: "
            + "; ".join(_text(reference) for reference in references)
        )
    lines.extend(
        [
            "",
            "Observed parameter inventory:",
            "",
            "| Number | Code | Name | Group | Read | Write | "
            "Read buffer slots |",
            "| ---: | --- | --- | --- | :---: | :---: | --- |",
        ]
    )
    for parameter in ordered:
        slots = ", ".join(
            str(index) for index in parameter.read_buffer_indices
        )
        lines.append(
            f"| {parameter.number} "
            f"| {_cell(parameter.code)} "
            f"| {_cell(parameter.display_name)} "
            f"| {_cell(parameter.group_name or parameter.group_prefix)} "
            f"| {_yes_no(parameter.observed_read)} "
            f"| {_yes_no(parameter.observed_write)} "
            f"| {_cell(slots)} |"
        )
    _append_parameter_semantics(lines, ordered)


def _append_parameter_semantics(
    lines: list[str],
    parameters: list[ObservedParameterAccess],
) -> None:
    """Append curated manual facts separately from observed access evidence."""

    definitions = [
        parameter.definition
        for parameter in parameters
        if parameter.definition is not None
    ]
    if not definitions:
        return
    lines.extend(
        [
            "",
            "Curated parameter semantics:",
            "",
            "| Code | Purpose | Range, options, or flags | Units | Default | "
            "Resolution | Access | Stop required |",
            "| --- | --- | --- | --- | --- | --- | --- | :---: |",
        ]
    )
    for definition in definitions:
        constraint = _parameter_constraint(definition)
        lines.append(
            f"| {_cell(definition.code)} "
            f"| {_cell(definition.description)} "
            f"| {_cell(constraint)} "
            f"| {_cell(definition.engineering_unit)} "
            f"| {_cell(definition.default)} "
            f"| {_cell(definition.resolution)} "
            f"| {'Read only' if definition.read_only else 'Read/write'} "
            f"| {_yes_no(definition.change_requires_stop)} |"
        )
    _append_parameter_option_sets(lines, definitions)


def _append_parameter_option_sets(
    lines: list[str],
    definitions: list[DeviceParameterDefinition],
) -> None:
    """Render each named shared option set once."""

    option_sets = {
        definition.option_set_name: definition.options
        for definition in definitions
        if definition.option_set_name is not None
    }
    if not option_sets:
        return
    lines.extend(["", "Parameter option sets:", ""])
    for name, options in sorted(option_sets.items()):
        lines.extend(
            [
                f"#### {_text(name)}",
                "",
                "| Value | Meaning |",
                "| ---: | --- |",
            ]
        )
        lines.extend(
            f"| {_cell(option.value)} | {_cell(option.label)} |"
            for option in options
        )
        lines.append("")


def _parameter_constraint(
    definition: DeviceParameterDefinition,
) -> str | None:
    """Render ranges and enumerations without interpreting expressions."""

    if definition.options:
        if definition.option_set_name is not None:
            return f"See option set: {definition.option_set_name}"
        return "; ".join(
            f"{option.value} = {option.label}" for option in definition.options
        )
    if definition.flags:
        return "; ".join(
            f"{flag.position} = {flag.label}" for flag in definition.flags
        )
    if definition.fields:
        return "; ".join(
            f"{field.position} {field.label}: "
            + ", ".join(
                f"{option.value}={option.label}" for option in field.options
            )
            for field in definition.fields
        )
    if definition.minimum is None and definition.maximum is None:
        return None
    return f"{_text(definition.minimum)} to {_text(definition.maximum)}"


def _append_evidence(lines: list[str], evidence: tuple[str, ...]) -> None:
    """Append a Markdown list with MD032-compliant surrounding blanks."""

    if lines and lines[-1] != "":
        lines.append("")
    lines.extend(["Evidence:", ""])
    lines.extend(f"- {_text(item)}" for item in evidence)
