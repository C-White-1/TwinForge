"""Versioned validation models for installed export configuration files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

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


def load_openplc_export_config(path: Path) -> OpenPLCExportConfig:
    """Load one strict, versioned OpenPLC JSON configuration document."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return OpenPLCExportConfig.model_validate(value)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise ExportConfigurationError(
            f"invalid OpenPLC export configuration '{path}': {error}"
        ) from error
