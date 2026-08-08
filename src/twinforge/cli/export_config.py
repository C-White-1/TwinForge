"""Versioned validation models for installed export configuration files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ExportConfigurationError(ValueError):
    """Raised when a target configuration document is unreadable or invalid."""


class OpenPLCExportConfig(BaseModel):
    """Validated options for the runtime-evidenced native OpenPLC target."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    target: Literal["openplc"]
    compile_only: bool = False
    locations: dict[str, str] = Field(default_factory=dict)
    timer_elapsed_locations: dict[str, str] = Field(default_factory=dict)
    counter_accumulator_locations: dict[str, str] = Field(default_factory=dict)
    counter_status_locations: dict[str, dict[str, str]] = Field(
        default_factory=dict
    )


class PLCopenExportConfig(BaseModel):
    """Validated options for target-neutral PLCopen XML 2.01 output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    target: Literal["plcopen"]
    xsd: Path | None = None


class AutomationMLExportConfig(BaseModel):
    """Validated options for AutomationML 2.1 / CAEX 3.0 output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    target: Literal["automationml"]
    base_library: Path | None = None
    xsd: Path | None = None
    plcopen_reference: Path | None = None


ExportConfig = TypeVar("ExportConfig", bound=BaseModel)


def load_openplc_export_config(path: Path) -> OpenPLCExportConfig:
    """Load one strict, versioned OpenPLC JSON configuration document."""
    return _load_export_config(path, OpenPLCExportConfig, "OpenPLC")


def load_plcopen_export_config(path: Path) -> PLCopenExportConfig:
    """Load PLCopen settings and resolve paths relative to their document."""
    config = _load_export_config(path, PLCopenExportConfig, "PLCopen")
    return config.model_copy(update={"xsd": _resolve_path(config.xsd, path)})


def load_automationml_export_config(path: Path) -> AutomationMLExportConfig:
    """Load AutomationML settings with portable document-relative paths."""
    config = _load_export_config(
        path,
        AutomationMLExportConfig,
        "AutomationML",
    )
    return config.model_copy(
        update={
            "base_library": _resolve_path(config.base_library, path),
            "xsd": _resolve_path(config.xsd, path),
            "plcopen_reference": _resolve_path(
                config.plcopen_reference,
                path,
            ),
        }
    )


def _load_export_config(
    path: Path,
    model: type[ExportConfig],
    label: str,
) -> ExportConfig:
    """Load and strictly validate one versioned target configuration."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return model.model_validate(value)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise ExportConfigurationError(
            f"invalid {label} export configuration '{path}': {error}"
        ) from error


def _resolve_path(value: Path | None, config_path: Path) -> Path | None:
    """Resolve a configured path from the directory containing its JSON."""
    if value is None or value.is_absolute():
        return value
    return (config_path.parent / value).resolve()
