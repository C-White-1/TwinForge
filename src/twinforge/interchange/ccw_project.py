"""Validated, lossless boundary for CCW project interchange artifacts."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from importlib.resources import files
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

CCW_PROJECT_SCHEMA_VERSION = "ccw-project-v1"
_SCHEMA_RESOURCE = "ccw-project-v1.schema.json"


class CCWProjectInterchangeError(RuntimeError):
    """Base error for the CCW project interchange boundary."""


class UnsupportedCCWProjectVersionError(CCWProjectInterchangeError):
    """Raised when TwinForge does not support the declared contract version."""


class CCWProjectValidationError(CCWProjectInterchangeError):
    """Raised when a CCW project artifact violates its declared contract."""


@dataclass(frozen=True)
class CCWProjectArtifact:
    """One validated artifact retained without semantic lowering or field loss."""

    _document: dict[str, Any]
    input_path: Path | None = None

    def to_document(self) -> dict[str, Any]:
        """Return an independent copy of the complete validated evidence."""

        return deepcopy(self._document)

    @property
    def schema_version(self) -> str:
        """Return the validated interchange-contract version."""

        return str(self._document["schema_version"])

    @property
    def source_reference(self) -> str:
        """Return the producer-supplied source reference."""

        return str(self._document["source"]["reference"])

    @property
    def source_sha256(self) -> str:
        """Return the producer-supplied hash of the originating CCW archive."""

        return str(self._document["source"]["sha256"])

    @property
    def source_diagnostics(self) -> tuple[str, ...]:
        """Return diagnostics preserved from the producing parser."""

        return tuple(str(item) for item in self._document["diagnostics"])

    @property
    def unknown_evidence_entries(self) -> tuple[str, ...]:
        """Return archive entries whose semantics remain unknown to the producer."""

        return tuple(
            str(item) for item in self._document["evidence"]["unknown_entries"]
        )


def ccw_project_schema_text() -> str:
    """Return the exact packaged Draft 2020-12 interchange schema."""

    resource = files("twinforge.schemas").joinpath(_SCHEMA_RESOURCE)
    return resource.read_text(encoding="utf-8")


def load_ccw_project(value: str | bytes | dict[str, Any]) -> CCWProjectArtifact:
    """Parse and validate one CCW project artifact without lowering it."""

    document = _parse_document(value)
    _validate_version(document)
    schema = json.loads(ccw_project_schema_text())
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(document),
        key=lambda error: tuple(str(item) for item in error.absolute_path),
    )
    if errors:
        error = errors[0]
        pointer = _json_pointer(tuple(error.absolute_path))
        raise CCWProjectValidationError(f"{pointer}: {error.message}")
    return CCWProjectArtifact(deepcopy(document))


def read_ccw_project(path: str | Path) -> CCWProjectArtifact:
    """Read one UTF-8 CCW project artifact through the validated boundary."""

    source = Path(path)
    try:
        if not source.is_file():
            raise FileNotFoundError(f"CCW project file does not exist: {source}")
        artifact = load_ccw_project(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise CCWProjectInterchangeError(
            f"could not read CCW project artifact '{source}': {error}"
        ) from error
    return CCWProjectArtifact(artifact.to_document(), input_path=source)


def ccw_project_inventory(artifact: CCWProjectArtifact) -> dict[str, Any]:
    """Return a deterministic, non-semantic inventory of one artifact."""

    document = artifact.to_document()
    return {
        "schema_version": document["schema_version"],
        "source_reference": document["source"]["reference"],
        "source_sha256": document["source"]["sha256"],
        "project_name": document["project"]["name"],
        "controller_catalog_number": document["controller"]["catalog_number"],
        "program_count": len(document["programs"]),
        "rung_count": sum(len(program["rungs"]) for program in document["programs"]),
        "variable_count": len(document["variables"]),
        "unresolved_operand_count": len(document["unresolved_operands"]),
        "diagnostic_count": len(document["diagnostics"]),
        "unknown_evidence_entry_count": len(document["evidence"]["unknown_entries"]),
    }


def _parse_document(value: str | bytes | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, dict):
        return deepcopy(value)
    try:
        document = json.loads(value, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise CCWProjectValidationError(f"invalid JSON: {error}") from error
    if not isinstance(document, dict):
        raise CCWProjectValidationError("#: document must be a JSON object")
    return document


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CCWProjectValidationError(f"duplicate JSON object member: {key!r}")
        result[key] = value
    return result


def _validate_version(document: dict[str, Any]) -> None:
    if "schema_version" not in document:
        raise CCWProjectValidationError("#/schema_version: required property missing")
    version = document["schema_version"]
    if version != CCW_PROJECT_SCHEMA_VERSION:
        raise UnsupportedCCWProjectVersionError(
            "unsupported CCW project schema_version "
            f"{version!r}; supported version is {CCW_PROJECT_SCHEMA_VERSION!r}"
        )


def _json_pointer(path: tuple[Any, ...]) -> str:
    if not path:
        return "#"
    encoded = [str(item).replace("~", "~0").replace("/", "~1") for item in path]
    return "#/" + "/".join(encoded)
