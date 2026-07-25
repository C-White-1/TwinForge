from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IOSignalType(str, Enum):
    DIGITAL = "Digital"
    ANALOG = "Analog"


class IODirection(str, Enum):
    INPUT = "Input"
    OUTPUT = "Output"


@dataclass(frozen=True)
class ModuleCapability:
    signal_type: IOSignalType
    direction: IODirection
    nominal_channel_count: int
    configured_channel_count: int | None
    source: str

    @property
    def unavailable_by_configuration_count(self) -> int | None:
        if self.configured_channel_count is None:
            return None
        return max(
            0,
            self.nominal_channel_count - self.configured_channel_count,
        )
