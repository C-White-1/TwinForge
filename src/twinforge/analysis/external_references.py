"""Inventory explicit external addresses and controller references."""

from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from twinforge.model import Controller, Module, Tag


class ExternalReferenceKind(str, Enum):
    """Conservative syntax class for one captured external reference."""

    IPV4_ADDRESS = "ipv4_address"
    SYMBOLIC_CONTROLLER = "symbolic_controller"
    SYMBOLIC_PATH = "symbolic_path"
    REMOTE_TAG = "remote_tag"
    REMOTE_FILE = "remote_file"


@dataclass(frozen=True)
class ExternalReferenceEvidence:
    """One exact source field that points outside the local controller model."""

    kind: ExternalReferenceKind
    value: str
    source_type: str
    source_name: str
    source_scope: str
    source_field: str


@dataclass(frozen=True)
class ExternalReferenceInventory:
    """Deterministically ordered configured external-reference evidence."""

    controller_name: str
    references: tuple[ExternalReferenceEvidence, ...]


def discover_external_references(
    controller: Controller,
) -> ExternalReferenceInventory:
    """Collect only documented module and tag fields with external meaning."""

    references: list[ExternalReferenceEvidence] = []
    for chassis in controller.iter_chassis():
        for module in chassis.iter_modules():
            _append_module_references(references, module)
    for module in controller.unplaced_modules:
        _append_module_references(references, module)
    for tag in controller.iter_tags():
        _append_tag_references(references, tag, "controller")
    for program in controller.iter_programs():
        for tag in program.iter_tags():
            _append_tag_references(
                references,
                tag,
                f"program:{program.name}",
            )
    return ExternalReferenceInventory(
        controller_name=controller.name,
        references=tuple(
            sorted(
                references,
                key=lambda item: (
                    item.source_scope.casefold(),
                    item.source_type,
                    item.source_name.casefold(),
                    item.source_field,
                    item.value,
                ),
            )
        ),
    )


def external_reference_inventory_data(
    inventory: ExternalReferenceInventory,
) -> dict[str, Any]:
    """Return the stable JSON-compatible external-reference contract."""

    return {
        "schema_version": "1.0",
        "controller_name": inventory.controller_name,
        "references": [
            {
                "kind": item.kind.value,
                "value": item.value,
                "source_type": item.source_type,
                "source_name": item.source_name,
                "source_scope": item.source_scope,
                "source_field": item.source_field,
            }
            for item in inventory.references
        ],
    }


def external_reference_inventory_json(
    inventory: ExternalReferenceInventory,
) -> str:
    """Serialize external reference evidence with a final newline."""

    return json.dumps(
        external_reference_inventory_data(inventory),
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def _append_module_references(
    references: list[ExternalReferenceEvidence],
    module: Module,
) -> None:
    if module.address is None:
        return
    references.append(
        ExternalReferenceEvidence(
            kind=_address_kind(module.address),
            value=module.address,
            source_type="module",
            source_name=module.name,
            source_scope="controller",
            source_field="Address",
        )
    )


def _append_tag_references(
    references: list[ExternalReferenceEvidence],
    tag: Tag,
    scope: str,
) -> None:
    message = tag.message_configuration
    if message is not None and message.connection_path:
        references.append(
            ExternalReferenceEvidence(
                kind=_address_kind(message.connection_path),
                value=message.connection_path,
                source_type="message_tag",
                source_name=tag.name,
                source_scope=scope,
                source_field="ConnectionPath",
            )
        )
    consumed = tag.consumed_configuration
    if consumed is None:
        return
    if consumed.producer:
        references.append(
            ExternalReferenceEvidence(
                kind=ExternalReferenceKind.SYMBOLIC_CONTROLLER,
                value=consumed.producer,
                source_type="consumed_tag",
                source_name=tag.name,
                source_scope=scope,
                source_field="Producer",
            )
        )
    if consumed.remote_tag:
        references.append(
            ExternalReferenceEvidence(
                kind=ExternalReferenceKind.REMOTE_TAG,
                value=consumed.remote_tag,
                source_type="consumed_tag",
                source_name=tag.name,
                source_scope=scope,
                source_field="RemoteTag",
            )
        )
    if consumed.remote_file is not None:
        references.append(
            ExternalReferenceEvidence(
                kind=ExternalReferenceKind.REMOTE_FILE,
                value=str(consumed.remote_file),
                source_type="consumed_tag",
                source_name=tag.name,
                source_scope=scope,
                source_field="RemoteFile",
            )
        )


def _address_kind(value: str) -> ExternalReferenceKind:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return ExternalReferenceKind.SYMBOLIC_PATH
    return (
        ExternalReferenceKind.IPV4_ADDRESS
        if address.version == 4
        else ExternalReferenceKind.SYMBOLIC_PATH
    )
