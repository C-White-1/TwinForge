"""Deterministic JSON serialization of TwinForge model evidence."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from collections import Counter
from enum import Enum
from importlib.resources import files
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote_to_bytes
import xml.etree.ElementTree as ET

from twinforge.model import Asset

if TYPE_CHECKING:
    from twinforge.parsers.l5x.document import L5XDocument


class ModelJSONSerializationError(TypeError):
    """Raised when a model value has no evidence-preserving JSON form."""


class ModelJSONValidationError(ValueError):
    """Raised when a JSON document violates the model-evidence contract."""


class ModelJSONPointerError(ValueError):
    """Raised when a model-evidence JSON Pointer cannot be resolved."""


_RESERVED_KEYS = frozenset({"$bytes_hex", "$map", "$ref", "$type"})


def model_json_schema_text() -> str:
    """Return the packaged TwinForge model JSON 1.0 schema text."""

    schema = files("twinforge.schemas").joinpath("model-json-1.0.schema.json")
    return schema.read_text(encoding="utf-8")


class ModelJSONExporter:
    """Serialize converted L5X evidence without runtime object identities."""

    def export(self, document: L5XDocument) -> str:
        """Return deterministic, cycle-safe JSON for one converted document."""

        encoder = _ModelEvidenceEncoder()
        payload = {
            "schema_version": "1.0",
            "source_format": "l5x",
            "document": encoder.encode(document, "#/document"),
        }
        return json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"


class _ModelEvidenceEncoder:
    """Encode dataclass graphs using stable first-occurrence references."""

    def __init__(self) -> None:
        self._paths: dict[int, str] = {}

    def encode(self, value: Any, path: str) -> Any:
        """Encode one supported value at its stable JSON-pointer path."""

        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, Path):
            return value.as_posix()
        if isinstance(value, bytes):
            return {"$bytes_hex": value.hex()}
        if isinstance(value, ET.Element):
            return {
                "$type": "xml.etree.ElementTree.Element",
                "xml": ET.tostring(value, encoding="unicode"),
            }
        if is_dataclass(value) and not isinstance(value, type):
            return self._dataclass(value, path)
        if isinstance(value, dict):
            return self._mapping(value, path)
        if isinstance(value, (list, tuple)):
            return self._sequence(value, path)
        raise ModelJSONSerializationError(
            f"unsupported model value at {path}: "
            f"{type(value).__module__}.{type(value).__qualname__}"
        )

    def _dataclass(self, value: Any, path: str) -> dict[str, Any]:
        reference = self._reference(value, path)
        if reference is not None:
            return reference
        result: dict[str, Any] = {
            "$type": f"{type(value).__module__}.{type(value).__qualname__}"
        }
        for item in fields(value):
            if item.name == "parent":
                continue
            if item.name == "id" and isinstance(value, Asset):
                continue
            child_path = f"{path}/{_pointer_token(item.name)}"
            result[item.name] = self.encode(getattr(value, item.name), child_path)
        return result

    def _mapping(self, value: dict[Any, Any], path: str) -> dict[str, Any]:
        reference = self._reference(value, path)
        if reference is not None:
            return reference
        if all(isinstance(key, str) for key in value) and not (
            _RESERVED_KEYS & value.keys()
        ):
            return {
                key: self.encode(value[key], f"{path}/{_pointer_token(key)}")
                for key in sorted(value)
            }

        ordered = sorted(value.items(), key=lambda item: _mapping_key(item[0]))
        return {
            "$map": [
                {
                    "key": self.encode(key, f"{path}/$map/{index}/key"),
                    "value": self.encode(
                        item,
                        f"{path}/$map/{index}/value",
                    ),
                }
                for index, (key, item) in enumerate(ordered)
            ]
        }

    def _sequence(self, value: list[Any] | tuple[Any, ...], path: str) -> Any:
        reference = self._reference(value, path)
        if reference is not None:
            return reference
        return [
            self.encode(item, f"{path}/{index}")
            for index, item in enumerate(value)
        ]

    def _reference(self, value: object, path: str) -> dict[str, str] | None:
        identity = id(value)
        existing = self._paths.get(identity)
        if existing is not None:
            return {"$ref": existing}
        self._paths[identity] = path
        return None


def _pointer_token(value: str) -> str:
    """Escape one RFC 6901 JSON Pointer token."""

    return value.replace("~", "~0").replace("/", "~1")


def _mapping_key(value: Any) -> str:
    """Return a deterministic ordering key for a supported mapping key."""

    if value is None or isinstance(value, (bool, int, float, str)):
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    if isinstance(value, Enum):
        return json.dumps(value.value, ensure_ascii=False, allow_nan=False)
    raise ModelJSONSerializationError(
        "unsupported mapping key: "
        f"{type(value).__module__}.{type(value).__qualname__}"
    )


def validate_model_json(value: str | bytes | dict[str, Any]) -> dict[str, Any]:
    """Validate and return one version 1.0 model-evidence document."""

    try:
        document = json.loads(value) if isinstance(value, (str, bytes)) else value
    except json.JSONDecodeError as error:
        raise ModelJSONValidationError(f"invalid JSON: {error}") from error
    if not isinstance(document, dict):
        raise ModelJSONValidationError("document must be a JSON object")
    if set(document) != {"schema_version", "source_format", "document"}:
        raise ModelJSONValidationError(
            "document must contain only schema_version, source_format, "
            "and document"
        )
    if document["schema_version"] != "1.0":
        raise ModelJSONValidationError("schema_version must be '1.0'")
    if document["source_format"] != "l5x":
        raise ModelJSONValidationError("source_format must be 'l5x'")
    _validate_evidence_node(
        document["document"],
        "#/document",
        referenceable_paths=set(),
    )
    root = document["document"]
    if not isinstance(root, dict) or not str(root.get("$type", "")).endswith(
        ".L5XDocument"
    ):
        raise ModelJSONValidationError(
            "#/document must be an L5XDocument record"
        )
    return document


def model_json_inventory(value: str | bytes | dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic inventory of one validated evidence document."""

    document = validate_model_json(value)
    counters: Counter[str] = Counter()
    record_types: Counter[str] = Counter()
    _inventory_evidence_node(document["document"], counters, record_types)
    evidence = document["document"]
    source_extensions = evidence.get("source_extensions", [])
    return {
        "schema_version": document["schema_version"],
        "source_format": document["source_format"],
        "target_type": evidence.get("target_type", "unknown"),
        "target_name": evidence.get("target_name", ""),
        "record_count": counters["record"],
        "record_types": dict(sorted(record_types.items())),
        "reference_count": counters["reference"],
        "byte_sequence_count": counters["bytes"],
        "typed_map_count": counters["map"],
        "source_extension_count": (
            len(source_extensions) if isinstance(source_extensions, list) else 0
        ),
    }


def resolve_model_json_pointer(
    value: str | bytes | dict[str, Any],
    pointer: str,
    *,
    resolve_reference: bool = False,
) -> Any:
    """Resolve one RFC 6901 fragment pointer in validated model evidence."""

    document = validate_model_json(value)
    selected = _resolve_json_pointer(document, pointer)
    if (
        resolve_reference
        and isinstance(selected, dict)
        and set(selected) == {"$ref"}
    ):
        selected = _resolve_json_pointer(document, selected["$ref"])
    return selected


def model_json_records(
    value: str | bytes | dict[str, Any],
    *,
    record_type: str | None = None,
) -> tuple[dict[str, str], ...]:
    """Index typed records and their stable pointers in validated evidence."""

    document = validate_model_json(value)
    records: list[dict[str, str]] = []
    _collect_model_json_records(
        document["document"],
        "#/document",
        records,
        record_type=record_type,
    )
    return tuple(records)


def _collect_model_json_records(
    value: Any,
    path: str,
    records: list[dict[str, str]],
    *,
    record_type: str | None,
) -> None:
    """Collect first-occurrence typed nodes without following `$ref` links."""

    if isinstance(value, list):
        for index, item in enumerate(value):
            _collect_model_json_records(
                item,
                f"{path}/{index}",
                records,
                record_type=record_type,
            )
        return
    if not isinstance(value, dict) or set(value) in (
        {"$ref"},
        {"$bytes_hex"},
    ):
        return
    if set(value) == {"$map"}:
        for index, entry in enumerate(value["$map"]):
            entry_path = f"{path}/$map/{index}"
            _collect_model_json_records(
                entry["key"],
                f"{entry_path}/key",
                records,
                record_type=record_type,
            )
            _collect_model_json_records(
                entry["value"],
                f"{entry_path}/value",
                records,
                record_type=record_type,
            )
        return

    encoded_type = value.get("$type")
    if isinstance(encoded_type, str) and _record_type_matches(
        encoded_type,
        record_type,
    ):
        record = {"pointer": path, "type": encoded_type}
        name = value.get("name", value.get("target_name"))
        if isinstance(name, str) and name:
            record["name"] = name
        records.append(record)
    for key, item in value.items():
        if key != "$type":
            _collect_model_json_records(
                item,
                f"{path}/{_pointer_token(key)}",
                records,
                record_type=record_type,
            )


def _record_type_matches(encoded_type: str, requested: str | None) -> bool:
    """Match either a fully qualified `$type` or its exact short name."""

    if requested is None:
        return True
    if "." in requested:
        return encoded_type == requested
    return encoded_type.rsplit(".", maxsplit=1)[-1] == requested


def _resolve_json_pointer(document: Any, pointer: str) -> Any:
    """Traverse a validated JSON value with strict fragment-pointer syntax."""

    if pointer == "#":
        return document
    if not pointer.startswith("#/"):
        raise ModelJSONPointerError(
            "pointer must be '#' or start with '#/'"
        )

    current = document
    for encoded_token in pointer[2:].split("/"):
        token = _decode_pointer_token(encoded_token, pointer)
        if isinstance(current, dict):
            if token not in current:
                raise ModelJSONPointerError(
                    f"pointer does not exist: {pointer}"
                )
            current = current[token]
            continue
        if isinstance(current, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                raise ModelJSONPointerError(
                    f"invalid array index in pointer: {pointer}"
                )
            index = int(token)
            if index >= len(current):
                raise ModelJSONPointerError(
                    f"array index out of range in pointer: {pointer}"
                )
            current = current[index]
            continue
        raise ModelJSONPointerError(
            f"pointer traverses a scalar value: {pointer}"
        )
    return current


def _decode_pointer_token(token: str, pointer: str) -> str:
    """Decode one RFC 6901 token while rejecting malformed escapes."""

    percent_index = 0
    while percent_index < len(token):
        if token[percent_index] != "%":
            percent_index += 1
            continue
        if (
            percent_index + 2 >= len(token)
            or any(
                character not in "0123456789abcdefABCDEF"
                for character in token[percent_index + 1 : percent_index + 3]
            )
        ):
            raise ModelJSONPointerError(
                f"invalid percent escape in pointer: {pointer}"
            )
        percent_index += 3
    try:
        token = unquote_to_bytes(token).decode("utf-8")
    except UnicodeDecodeError as error:
        raise ModelJSONPointerError(
            f"invalid UTF-8 escape in pointer: {pointer}"
        ) from error

    result: list[str] = []
    index = 0
    while index < len(token):
        character = token[index]
        if character != "~":
            result.append(character)
            index += 1
            continue
        if index + 1 >= len(token) or token[index + 1] not in "01":
            raise ModelJSONPointerError(
                f"invalid RFC 6901 escape in pointer: {pointer}"
            )
        result.append("~" if token[index + 1] == "0" else "/")
        index += 2
    return "".join(result)


def _inventory_evidence_node(
    value: Any,
    counters: Counter[str],
    record_types: Counter[str],
) -> None:
    """Accumulate control-node and typed-record counts without rehydration."""

    if isinstance(value, list):
        for item in value:
            _inventory_evidence_node(item, counters, record_types)
        return
    if not isinstance(value, dict):
        return
    if set(value) == {"$ref"}:
        counters["reference"] += 1
        return
    if set(value) == {"$bytes_hex"}:
        counters["bytes"] += 1
        return
    if set(value) == {"$map"}:
        counters["map"] += 1
        for entry in value["$map"]:
            _inventory_evidence_node(entry["key"], counters, record_types)
            _inventory_evidence_node(entry["value"], counters, record_types)
        return
    record_type = value.get("$type")
    if isinstance(record_type, str):
        counters["record"] += 1
        record_types[record_type] += 1
    for key, item in value.items():
        if key != "$type":
            _inventory_evidence_node(item, counters, record_types)


def _validate_evidence_node(
    value: Any,
    path: str,
    *,
    referenceable_paths: set[str],
) -> None:
    """Validate one recursive model-evidence node."""

    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ModelJSONValidationError(f"non-finite number at {path}")
        return
    if isinstance(value, list):
        referenceable_paths.add(path)
        for index, item in enumerate(value):
            _validate_evidence_node(
                item,
                f"{path}/{index}",
                referenceable_paths=referenceable_paths,
            )
        return
    if not isinstance(value, dict):
        raise ModelJSONValidationError(f"unsupported JSON value at {path}")

    reserved = _RESERVED_KEYS & value.keys()
    if not reserved:
        referenceable_paths.add(path)
        for key, item in value.items():
            _validate_evidence_node(
                item,
                f"{path}/{_pointer_token(key)}",
                referenceable_paths=referenceable_paths,
            )
        return
    if reserved == {"$ref"} and set(value) == {"$ref"}:
        reference = value["$ref"]
        if not isinstance(reference, str) or not reference.startswith("#/"):
            raise ModelJSONValidationError(f"invalid $ref at {path}")
        if reference not in referenceable_paths:
            raise ModelJSONValidationError(
                f"unresolved or forward $ref at {path}: {reference}"
            )
        return
    if reserved == {"$bytes_hex"} and set(value) == {"$bytes_hex"}:
        encoded = value["$bytes_hex"]
        if not isinstance(encoded, str):
            raise ModelJSONValidationError(f"invalid $bytes_hex at {path}")
        try:
            bytes.fromhex(encoded)
        except ValueError as error:
            raise ModelJSONValidationError(
                f"invalid $bytes_hex at {path}"
            ) from error
        return
    if reserved == {"$map"} and set(value) == {"$map"}:
        referenceable_paths.add(path)
        entries = value["$map"]
        if not isinstance(entries, list):
            raise ModelJSONValidationError(f"invalid $map at {path}")
        for index, entry in enumerate(entries):
            entry_path = f"{path}/$map/{index}"
            if not isinstance(entry, dict) or set(entry) != {"key", "value"}:
                raise ModelJSONValidationError(
                    f"invalid map entry at {entry_path}"
                )
            _validate_evidence_node(
                entry["key"],
                f"{entry_path}/key",
                referenceable_paths=referenceable_paths,
            )
            _validate_evidence_node(
                entry["value"],
                f"{entry_path}/value",
                referenceable_paths=referenceable_paths,
            )
        return
    if reserved == {"$type"} and isinstance(value.get("$type"), str):
        if not value["$type"]:
            raise ModelJSONValidationError(f"blank $type at {path}")
        referenceable_paths.add(path)
        for key, item in value.items():
            if key != "$type":
                _validate_evidence_node(
                    item,
                    f"{path}/{_pointer_token(key)}",
                    referenceable_paths=referenceable_paths,
                )
        return
    raise ModelJSONValidationError(f"invalid reserved-key object at {path}")
