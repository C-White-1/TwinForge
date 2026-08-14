"""Deterministic JSON serialization of TwinForge model evidence."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
import xml.etree.ElementTree as ET

from twinforge.model import Asset

if TYPE_CHECKING:
    from twinforge.parsers.l5x.document import L5XDocument


class ModelJSONSerializationError(TypeError):
    """Raised when a model value has no evidence-preserving JSON form."""


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
        if all(isinstance(key, str) for key in value):
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
