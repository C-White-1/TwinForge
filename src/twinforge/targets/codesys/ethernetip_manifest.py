"""Reusable CODESYS EtherNet/IP deployment-manifest contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CodesysEtherNetIPConnectionManifest(BaseModel):
    """Validated cyclic connection settings independent of a device profile."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rpi_ms: int = Field(gt=0)
    output_bytes: int = Field(gt=0)
    input_bytes: int = Field(gt=0)
    connection_path: tuple[int, ...]

    @field_validator("connection_path")
    @classmethod
    def _connection_path(
        cls,
        value: tuple[int, ...],
    ) -> tuple[int, ...]:
        if not value:
            raise ValueError("must not be empty")
        if any(item < 0 or item > 0xFF for item in value):
            raise ValueError("bytes must be between 0 and 255")
        return value
