"""Packed cyclic-I/O layouts derived from captured neutral contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from twinforge.analysis import CyclicIOContract, CyclicIOImage


class ByteOrder(str, Enum):
    """Byte ordering used by a packed transport image."""

    LITTLE = "little"
    BIG = "big"


@dataclass(frozen=True)
class PackedField:
    """One scalar or bit-overlay field in a packed image."""

    name: str
    data_type: str
    byte_offset: int
    byte_size: int
    overlay_target: str | None = None
    bit_number: int | None = None
    description: str | None = None

    @property
    def is_overlay(self) -> bool:
        """Return whether this field addresses a bit in another field."""

        return self.overlay_target is not None


@dataclass(frozen=True)
class PackedImage:
    """Decoded values together with the exact source bytes."""

    raw: bytes
    values: Mapping[str, int | bool]


@dataclass(frozen=True)
class PackedImageLayout:
    """Validated, target-neutral description of one cyclic image."""

    name: str
    byte_size: int
    byte_order: ByteOrder
    fields: tuple[PackedField, ...]

    def __post_init__(self) -> None:
        if self.byte_size <= 0:
            raise ValueError("byte_size must be positive")
        names: set[str] = set()
        base_names = {
            field.name for field in self.fields if not field.is_overlay
        }
        for field in self.fields:
            if field.name in names:
                raise ValueError(f"duplicate packed field {field.name!r}")
            names.add(field.name)
            if field.byte_offset < 0 or field.byte_size <= 0:
                raise ValueError(f"invalid bounds for field {field.name!r}")
            if field.byte_offset + field.byte_size > self.byte_size:
                raise ValueError(f"field {field.name!r} exceeds image size")
            if field.is_overlay:
                if field.overlay_target not in base_names:
                    raise ValueError(
                        f"overlay target {field.overlay_target!r} is absent"
                    )
                if field.bit_number is None:
                    raise ValueError(
                        f"overlay field {field.name!r} has no bit number"
                    )
                if not 0 <= field.bit_number < field.byte_size * 8:
                    raise ValueError(
                        f"bit number for {field.name!r} exceeds its target"
                    )

    def decode(self, image: bytes) -> PackedImage:
        """Decode a complete image while retaining its exact byte sequence."""

        if len(image) != self.byte_size:
            raise ValueError(
                f"{self.name} requires {self.byte_size} bytes, "
                f"received {len(image)}"
            )
        values: dict[str, int | bool] = {}
        for field in self.fields:
            raw_value = int.from_bytes(
                image[field.byte_offset : field.byte_offset + field.byte_size],
                byteorder=self.byte_order.value,
                signed=_is_signed(field.data_type),
            )
            if field.is_overlay:
                assert field.bit_number is not None
                values[field.name] = bool(
                    (raw_value & 0xFFFF_FFFF) & (1 << field.bit_number)
                )
            else:
                values[field.name] = raw_value
        return PackedImage(raw=bytes(image), values=values)

    def encode(
        self,
        values: Mapping[str, int | bool],
        *,
        base: bytes | None = None,
    ) -> bytes:
        """Encode supplied fields, preserving unspecified bytes and bits."""

        image = bytearray(base if base is not None else bytes(self.byte_size))
        if len(image) != self.byte_size:
            raise ValueError(
                f"{self.name} base requires {self.byte_size} bytes, "
                f"received {len(image)}"
            )
        fields = {field.name: field for field in self.fields}
        unknown = set(values) - set(fields)
        if unknown:
            raise ValueError(f"unknown packed fields: {sorted(unknown)!r}")
        for name, value in values.items():
            field = fields[name]
            if field.is_overlay:
                continue
            image[field.byte_offset : field.byte_offset + field.byte_size] = (
                int(value).to_bytes(
                    field.byte_size,
                    byteorder=self.byte_order.value,
                    signed=_is_signed(field.data_type),
                )
            )
        for name, value in values.items():
            field = fields[name]
            if not field.is_overlay:
                continue
            assert field.bit_number is not None
            current = int.from_bytes(
                image[field.byte_offset : field.byte_offset + field.byte_size],
                byteorder=self.byte_order.value,
                signed=False,
            )
            mask = 1 << field.bit_number
            current = current | mask if bool(value) else current & ~mask
            image[field.byte_offset : field.byte_offset + field.byte_size] = (
                current.to_bytes(
                    field.byte_size,
                    byteorder=self.byte_order.value,
                    signed=False,
                )
            )
        return bytes(image)


@dataclass(frozen=True)
class PackedCyclicIOContract:
    """Runtime-ready layouts for both directions of a cyclic connection."""

    implementation_name: str
    protocol: str | None
    requested_packet_interval_microseconds: int | None
    input_layout: PackedImageLayout
    output_layout: PackedImageLayout


def build_packed_cyclic_io_contract(
    contract: CyclicIOContract,
    *,
    byte_order: ByteOrder = ByteOrder.LITTLE,
) -> PackedCyclicIOContract:
    """Build validated runtime layouts from captured cyclic-I/O evidence."""

    return PackedCyclicIOContract(
        implementation_name=contract.implementation_name,
        protocol=contract.protocol,
        requested_packet_interval_microseconds=(
            contract.requested_packet_interval_microseconds
        ),
        input_layout=_build_layout(contract.input_image, byte_order),
        output_layout=_build_layout(contract.output_image, byte_order),
    )


def _build_layout(
    image: CyclicIOImage,
    byte_order: ByteOrder,
) -> PackedImageLayout:
    size = image.configured_size_bytes or image.copied_size_bytes
    if size is None:
        raise ValueError(f"{image.role} image has no captured byte size")
    fields = tuple(
        PackedField(
            name=field.name,
            data_type=field.data_type or "",
            byte_offset=field.byte_offset,
            byte_size=field.byte_size,
            overlay_target=field.overlay_target,
            bit_number=field.bit_number,
            description=field.description,
        )
        for field in image.fields
    )
    return PackedImageLayout(
        name=f"{image.role}_image",
        byte_size=size,
        byte_order=byte_order,
        fields=fields,
    )


def _is_signed(data_type: str) -> bool:
    return data_type.upper() in {"SINT", "INT", "DINT", "LINT"}
