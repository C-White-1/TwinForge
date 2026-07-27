"""Analyze evidence-backed cyclic I/O contracts used by reusable logic."""

from __future__ import annotations

from dataclasses import dataclass

from twinforge.model import AddOnInstruction, Connection, Controller, DatatypeMember


@dataclass(frozen=True)
class CyclicIOField:
    """One typed field carried by a cyclic connection."""

    name: str
    data_type: str | None
    byte_offset: int
    byte_size: int
    overlay_target: str | None = None
    bit_number: int | None = None
    description: str | None = None


@dataclass(frozen=True)
class CyclicIOImage:
    """One producer-to-consumer data image."""

    role: str
    parameter_name: str
    parameter_data_type: str
    connection_point: int | None
    configured_size_bytes: int | None
    copied_size_bytes: int | None
    local_path: str | None
    fields: tuple[CyclicIOField, ...]


@dataclass(frozen=True)
class CyclicIOContract:
    """Cyclic input/status and output/command evidence for one AOI."""

    implementation_name: str
    protocol: str | None
    requested_packet_interval_microseconds: int | None
    unicast: bool | None
    input_image: CyclicIOImage
    output_image: CyclicIOImage
    diagnostics: tuple[str, ...] = ()


def analyze_cyclic_io_contract(
    controller: Controller,
    implementation: AddOnInstruction,
    connection: Connection | None = None,
    *,
    input_parameter: str = "Ref_DataIn",
    output_parameter: str = "Ref_DataOut",
) -> CyclicIOContract:
    """Build a contract from AOI datatypes, copy operations, and connection data."""

    input_image = _image(
        controller,
        implementation,
        parameter_name=input_parameter,
        role="status",
        connection_point=(
            connection.input_connection_point if connection else None
        ),
        configured_size=connection.input_size_bytes if connection else None,
    )
    output_image = _image(
        controller,
        implementation,
        parameter_name=output_parameter,
        role="command",
        connection_point=(
            connection.output_connection_point if connection else None
        ),
        configured_size=connection.output_size_bytes if connection else None,
    )
    diagnostics: list[str] = []
    for image in (input_image, output_image):
        if (
            image.configured_size_bytes is not None
            and image.copied_size_bytes is not None
            and image.configured_size_bytes != image.copied_size_bytes
        ):
            diagnostics.append(
                f"{image.role} image configures "
                f"{image.configured_size_bytes} bytes but the AOI copy "
                f"evidence specifies {image.copied_size_bytes} bytes"
            )
    return CyclicIOContract(
        implementation_name=implementation.name,
        protocol=connection.protocol if connection else None,
        requested_packet_interval_microseconds=(
            connection.requested_packet_interval_microseconds
            if connection
            else None
        ),
        unicast=connection.unicast if connection else None,
        input_image=input_image,
        output_image=output_image,
        diagnostics=tuple(diagnostics),
    )


def _image(
    controller: Controller,
    implementation: AddOnInstruction,
    *,
    parameter_name: str,
    role: str,
    connection_point: int | None,
    configured_size: int | None,
) -> CyclicIOImage:
    parameter = implementation.parameters.get(parameter_name)
    if parameter is None or parameter.effective_data_type is None:
        raise ValueError(
            f"{implementation.name} has no typed {parameter_name} parameter"
        )
    local_path, copy_count = _copy_evidence(
        implementation, parameter_name, role
    )
    datatype = _local_datatype(controller, implementation, local_path)
    fields = _layout(datatype.members) if datatype is not None else ()
    if role == "status":
        copied_size = (
            _datatype_size(datatype) * copy_count
            if datatype is not None and copy_count is not None
            else None
        )
    else:
        element_size = _parameter_element_size(parameter.effective_data_type)
        copied_size = (
            element_size * copy_count
            if element_size and copy_count is not None
            else None
        )
    return CyclicIOImage(
        role=role,
        parameter_name=parameter_name,
        parameter_data_type=parameter.effective_data_type,
        connection_point=connection_point,
        configured_size_bytes=configured_size,
        copied_size_bytes=copied_size,
        local_path=local_path,
        fields=fields,
    )


def _copy_evidence(
    implementation: AddOnInstruction,
    parameter_name: str,
    role: str,
) -> tuple[str | None, int | None]:
    """Recover the direct COP boundary without interpreting arbitrary ST."""

    import re

    if role == "status":
        pattern = re.compile(
            rf"\bCOP\s*\(\s*{re.escape(parameter_name)}\s*,\s*"
            r"([A-Za-z_][\w.]*)\s*,\s*(\d+)\s*\)",
            re.IGNORECASE,
        )
    else:
        pattern = re.compile(
            rf"\bCOP\s*\(\s*([A-Za-z_][\w.]*)\s*,\s*"
            rf"{re.escape(parameter_name)}\s*,\s*(\d+)\s*\)",
            re.IGNORECASE,
        )
    for routine in implementation.iter_routines():
        if routine.structured_text:
            match = pattern.search(routine.structured_text)
            if match:
                return match.group(1), int(match.group(2))
    return None, None


def _local_datatype(
    controller: Controller,
    implementation: AddOnInstruction,
    local_path: str | None,
):
    if local_path is None:
        return None
    parts = local_path.split(".")
    if len(parts) < 2:
        return None
    tag = implementation.local_tags.get(parts[0])
    datatype = controller.get_datatype(tag.data_type) if tag and tag.data_type else None
    for member_name in parts[1:]:
        if datatype is None:
            return None
        member = next(
            (item for item in datatype.members if item.name == member_name),
            None,
        )
        datatype = member.data_type if member else None
    return datatype


def _layout(members: list[DatatypeMember]) -> tuple[CyclicIOField, ...]:
    offsets: dict[str, tuple[int, int]] = {}
    result: list[CyclicIOField] = []
    offset = 0
    for member in members:
        if member.target is not None:
            target_offset, target_size = offsets.get(member.target, (0, 0))
            result.append(
                CyclicIOField(
                    name=member.name,
                    data_type=member.data_type_name,
                    byte_offset=target_offset,
                    byte_size=target_size,
                    overlay_target=member.target,
                    bit_number=member.bit_number,
                    description=member.description,
                )
            )
            continue
        size = _atomic_size(member.data_type_name)
        result.append(
            CyclicIOField(
                name=member.name,
                data_type=member.data_type_name,
                byte_offset=offset,
                byte_size=size,
                description=member.description,
            )
        )
        offsets[member.name] = (offset, size)
        offset += size
    return tuple(result)


def _atomic_size(data_type: str | None) -> int:
    return {
        "BOOL": 1,
        "SINT": 1,
        "INT": 2,
        "DINT": 4,
        "REAL": 4,
    }.get((data_type or "").upper(), 0)


def _datatype_size(datatype: object | None) -> int:
    members = getattr(datatype, "members", None)
    if not isinstance(members, list):
        return 0
    return sum(
        _atomic_size(member.data_type_name)
        for member in members
        if member.target is None
    )


def _parameter_element_size(data_type: str) -> int:
    """Recover the atomic transport element from a generated Logix type."""

    import re

    match = re.search(
        r"(?:^|:|_)(BOOL|SINT|INT|DINT|REAL)(?:_|:|$)",
        data_type,
        re.IGNORECASE,
    )
    return _atomic_size(match.group(1)) if match else 0
