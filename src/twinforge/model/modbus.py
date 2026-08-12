"""Vendor-neutral Modbus address and register-map model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .asset import Asset
from .source_extension import SourceExtension


class ModbusArea(str, Enum):
    """The four data areas defined by the Modbus data model."""

    COILS = "coils"
    DISCRETE_INPUTS = "discrete_inputs"
    INPUT_REGISTERS = "input_registers"
    HOLDING_REGISTERS = "holding_registers"


class ModbusAddressingConvention(str, Enum):
    """How a source expressed a Modbus point address."""

    ZERO_BASED = "zero_based"
    ONE_BASED = "one_based"
    UNKNOWN = "unknown"


class ModbusAccess(str, Enum):
    """Observed or declared access permitted for one point."""

    READ_ONLY = "read_only"
    WRITE_ONLY = "write_only"
    READ_WRITE = "read_write"
    UNKNOWN = "unknown"


@dataclass(frozen=True, kw_only=True)
class ModbusEndpointConfiguration:
    """Transport and addressing settings for one Modbus endpoint."""

    unit_id: int | None = None
    tcp_port: int | None = None
    addressing_convention: ModbusAddressingConvention = (
        ModbusAddressingConvention.UNKNOWN
    )

    def __post_init__(self) -> None:
        if self.unit_id is not None and not 0 <= self.unit_id <= 255:
            raise ValueError("Modbus unit ID must be between 0 and 255")
        if self.tcp_port is not None and not 0 <= self.tcp_port <= 65535:
            raise ValueError("Modbus TCP port must be between 0 and 65535")


@dataclass(frozen=True, kw_only=True)
class ModbusAddress:
    """One Modbus address without guessing its source convention.

    `offset` is the protocol data-model offset only when the convention is
    known. `source_reference` always retains the source notation, such as
    `40001`, `HR0`, or a configuration-tool expression.
    """

    area: ModbusArea
    source_reference: str
    offset: int | None = None
    convention: ModbusAddressingConvention = ModbusAddressingConvention.UNKNOWN
    unit_id: int | None = None
    quantity: int | None = 1

    def __post_init__(self) -> None:
        if not self.source_reference.strip():
            raise ValueError("Modbus source reference must not be empty")
        if self.offset is not None and self.offset < 0:
            raise ValueError("Modbus offset must not be negative")
        if self.quantity is not None and self.quantity < 1:
            raise ValueError("Modbus quantity must be positive")
        if self.unit_id is not None and not 0 <= self.unit_id <= 255:
            raise ValueError("Modbus unit ID must be between 0 and 255")
        if (
            self.convention is ModbusAddressingConvention.UNKNOWN
            and self.offset is not None
        ):
            raise ValueError(
                "Modbus offset requires an explicit addressing convention"
            )


@dataclass(kw_only=True)
class ModbusPoint(Asset):
    """One named value occupying a Modbus data-model address range."""

    address: ModbusAddress
    access: ModbusAccess = ModbusAccess.UNKNOWN
    data_type: str | None = None
    engineering_unit: str | None = None
    description: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(kw_only=True)
class ModbusRegisterMap(Asset):
    """A collection of evidenced points for one Modbus protocol endpoint."""

    interface_name: str
    points: list[ModbusPoint] = field(default_factory=list)
    source_extensions: list[SourceExtension] = field(default_factory=list, repr=False)

    def add_point(self, point: ModbusPoint) -> None:
        """Attach a point without treating overlaps as automatically invalid."""

        point.parent = self
        self.points.append(point)

    def overlaps(self) -> tuple[tuple[ModbusPoint, ModbusPoint], ...]:
        """Return comparable overlapping ranges for later QA resolution."""

        result: list[tuple[ModbusPoint, ModbusPoint]] = []
        for index, left in enumerate(self.points):
            for right in self.points[index + 1 :]:
                if _overlaps(left.address, right.address):
                    result.append((left, right))
        return tuple(result)


def _overlaps(left: ModbusAddress, right: ModbusAddress) -> bool:
    if left.area is not right.area or left.unit_id != right.unit_id:
        return False
    if left.offset is None or right.offset is None:
        return False
    if left.quantity is None or right.quantity is None:
        return False
    left_end = left.offset + left.quantity
    right_end = right.offset + right.quantity
    return left.offset < right_end and right.offset < left_end
