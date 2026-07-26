"""Materialize devices from corroborated software and module evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from twinforge.analysis.literal_assignments import extract_literal_assignments
from twinforge.converters.device import assemble_device_from_module
from twinforge.knowledge.powerflex525_parameters import (
    POWERFLEX_525_PARAMETER_REFERENCE,
    PowerFlex525ParameterCatalogue,
)
from twinforge.model import (
    AddOnInstruction,
    CommunicationService,
    Device,
    DeviceType,
    ObservedParameterAccess,
    SoftwareModuleAssembly,
)
from twinforge.parsers.l5x.corpus import L5XCorpus


@dataclass(frozen=True)
class AssembledSoftwareDevice:
    """A materialized device and the neutral evidence supporting it."""

    device: Device
    source: SoftwareModuleAssembly
    provider: str


class DeviceAssemblyProvider(Protocol):
    """Optional domain knowledge used after neutral L5X resolution."""

    name: str

    def assemble(
        self,
        source: SoftwareModuleAssembly,
    ) -> Device | None:
        """Return a device only when this provider recognizes the evidence."""


class PowerFlex525AssemblyProvider:
    """Recognize the documented Dvc_PF525/PowerFlex 525 library contract."""

    name = "powerflex_525"

    def assemble(
        self,
        source: SoftwareModuleAssembly,
    ) -> Device | None:
        implementation = source.definition.implementation
        description = getattr(implementation, "description", None)
        if source.definition.name.casefold() != "dvc_pf525":
            return None
        if not isinstance(description, str) or (
            description.strip().casefold() != "powerflex 525"
        ):
            return None
        if len(source.modules) != 1:
            return None
        evidence = "; ".join(source.evidence)
        device = assemble_device_from_module(
            source.modules[0],
            name=source.instance_tag.name,
            device_type=DeviceType.DRIVE,
            manufacturer="Rockwell Automation",
            model="PowerFlex 525",
            evidence=evidence,
        )
        device.metadata.update(
            {
                "workspace_key": source.workspace_key,
                "software_definition": source.definition.name,
                "instance_tag": source.instance_tag.name,
                "assembly_provider": self.name,
            }
        )
        _add_explicit_message_services(device, source)
        _add_powerflex_parameter_inventory(device, source)
        source.definition.bind_device(device, evidence=evidence)
        source.definition.bind_module(source.modules[0], evidence=evidence)
        return device


def assemble_corpus_devices(
    corpus: L5XCorpus,
    *,
    providers: tuple[DeviceAssemblyProvider, ...] = (
        PowerFlex525AssemblyProvider(),
    ),
) -> tuple[AssembledSoftwareDevice, ...]:
    """Apply ordered opt-in knowledge providers to neutral assemblies."""

    results: list[AssembledSoftwareDevice] = []
    for source in corpus.software_module_assemblies:
        for provider in providers:
            device = provider.assemble(source)
            if device is None:
                continue
            results.append(
                AssembledSoftwareDevice(
                    device=device,
                    source=source,
                    provider=provider.name,
                )
            )
            break
    return tuple(results)


def _add_explicit_message_services(
    device: Device,
    source: SoftwareModuleAssembly,
) -> None:
    """Add services only for operands typed as Logix MESSAGE parameters."""

    interface = next(
        (
            item
            for item in device.communication_interfaces
            if item.protocol.casefold() == "ethernet/ip"
        ),
        None,
    )
    if interface is None:
        return
    existing = {service.name.casefold() for service in interface.services}
    payload_tags: list[str] = []
    for resolved in source.calls:
        for binding in resolved.argument_bindings:
            parameter = binding.parameter
            tag = binding.target_tag
            if parameter is None or tag is None:
                continue
            data_type = (parameter.effective_data_type or "").casefold()
            if data_type == "message" and tag.name.casefold() not in existing:
                configuration = tag.message_configuration
                interface.add_service(
                    CommunicationService(
                        name=tag.name,
                        service_type=_message_service_type(
                            configuration.service_code
                            if configuration is not None
                            else None
                        ),
                        object_class=_hex_value(
                            configuration.object_type
                            if configuration is not None
                            else None
                        ),
                        instance=str(configuration.target_object)
                        if configuration is not None
                        and configuration.target_object is not None
                        else None,
                        attribute=_hex_value(
                            configuration.attribute_number
                            if configuration is not None
                            else None
                        ),
                        service_code=configuration.service_code
                        if configuration is not None
                        else None,
                        requested_length=configuration.requested_length
                        if configuration is not None
                        else None,
                        connection_path=configuration.connection_path
                        if configuration is not None
                        else None,
                        local_element=configuration.local_element
                        if configuration is not None
                        else None,
                        destination_tag=configuration.destination_tag
                        if configuration is not None
                        else None,
                        configuration_source="l5x_message_tag"
                        if configuration is not None
                        else None,
                        runtime_mutable=True
                        if configuration is not None
                        else None,
                        source_extensions=tuple(tag.source_extensions),
                    )
                )
                existing.add(tag.name.casefold())
            elif parameter.name.casefold() == "ref_msgdata":
                payload_tags.append(tag.name)
    if payload_tags:
        device.metadata["explicit_message_payload_tags"] = tuple(
            dict.fromkeys(payload_tags)
        )


def _message_service_type(service_code: int | None) -> str:
    if service_code is None:
        return "explicit_message"
    return {
        0x10: "explicit_message_write",
        0x32: "explicit_message_read",
    }.get(service_code, "explicit_message")


def _hex_value(value: int | None) -> str | None:
    return f"0x{value:04X}" if value is not None else None


def _add_powerflex_parameter_inventory(
    device: Device,
    source: SoftwareModuleAssembly,
) -> None:
    """Retain observed AOI parameter-number candidates without overclaiming."""

    implementation = source.definition.implementation
    if not isinstance(implementation, AddOnInstruction):
        return
    evidence = [
        item
        for routine in implementation.iter_routines()
        for item in extract_literal_assignments(routine)
    ]
    read_evidence = [
        item
        for item in evidence
        if item.target.casefold().startswith("ref_msgdata[")
        and item.indices
        and item.indices[0] < 64
        and item.value > 0
    ]
    write_evidence = [
        item
        for item in evidence
        if item.target.casefold() == "writeinstance" and item.value > 0
    ]
    read_candidates = sorted({item.value for item in read_evidence})
    write_candidates = sorted({item.value for item in write_evidence})
    if read_candidates:
        device.metadata[
            "observed_bulk_read_parameter_candidates"
        ] = tuple(read_candidates)
    if write_candidates:
        device.metadata[
            "observed_write_parameter_candidates"
        ] = tuple(write_candidates)
    labels = {
        item.value: _parameter_label(item.comment)
        for item in read_evidence
        if item.comment is not None
    }
    catalogue = PowerFlex525ParameterCatalogue()
    for number in sorted(set(read_candidates) | set(write_candidates)):
        matching_reads = [
            item for item in read_evidence if item.value == number
        ]
        matching_writes = [
            item for item in write_evidence if item.value == number
        ]
        label = labels.get(number)
        code, group_prefix, display_name = _parse_parameter_label(label)
        definition = catalogue.definition(number)
        if definition is not None:
            code = definition.code
            group_prefix = definition.group_prefix
            display_name = definition.name
        device.observed_parameters.append(
            ObservedParameterAccess(
                number=number,
                label=label,
                code=code,
                group_prefix=group_prefix,
                group_name=(
                    definition.group_name
                    if definition is not None
                    else catalogue.group_name(group_prefix)
                ),
                display_name=display_name,
                reference=(
                    definition.reference
                    if definition is not None
                    else POWERFLEX_525_PARAMETER_REFERENCE
                ),
                definition=definition,
                observed_read=bool(matching_reads),
                observed_write=bool(matching_writes),
                read_buffer_indices=tuple(
                    sorted(
                        {
                            item.indices[0]
                            for item in matching_reads
                            if item.indices
                        }
                    )
                ),
                evidence=tuple(
                    item.source_text.strip()
                    for item in (*matching_reads, *matching_writes)
                ),
            )
        )


def _parameter_label(comment: str | None) -> str | None:
    if comment is None:
        return None
    label = comment.replace("***", "").strip()
    return label or None


def _parse_parameter_label(
    label: str | None,
) -> tuple[str | None, str | None, str | None]:
    """Parse AOI labels such as ``P038 [VoltageClass]`` conservatively."""

    if label is None:
        return None, None, None
    match = re.fullmatch(
        r"(?P<prefix>[A-Za-z])(?P<number>\d{3})\s+\[(?P<name>[^\]]+)\]",
        label,
    )
    if match is None:
        return None, None, None
    prefix = match.group("prefix")
    return (
        f"{prefix}{match.group('number')}",
        prefix,
        match.group("name").strip(),
    )

