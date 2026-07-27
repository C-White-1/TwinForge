"""Markdown export for vendor-neutral cyclic I/O contracts."""

from __future__ import annotations

from twinforge.analysis import CyclicIOContract, CyclicIOImage


class CyclicIOContractMarkdownExporter:
    """Render connection and field evidence without inventing semantics."""

    def export(
        self,
        contract: CyclicIOContract,
        *,
        title: str | None = None,
    ) -> str:
        """Return a deterministic engineering report."""

        period = (
            f"{contract.requested_packet_interval_microseconds / 1000:g} ms"
            if contract.requested_packet_interval_microseconds is not None
            else "not captured"
        )
        lines = [
            f"# {title or f'{contract.implementation_name} cyclic I/O contract'}",
            "",
            (
                "This report separates the drive-produced status image from "
                "the controller-produced command image. Field meanings come "
                "from captured datatype overlays; connection properties come "
                "from the associated module export."
            ),
            "",
            "## Connection",
            "",
            f"- Protocol: {contract.protocol or 'not captured'}",
            f"- Requested packet interval: {period}",
            f"- Unicast: {_yes_no(contract.unicast)}",
            "",
        ]
        lines.extend(_image(contract.input_image))
        lines.extend(_image(contract.output_image))
        lines.extend(
            [
                "## Operational interpretation",
                "",
                (
                    "- The input connection image is consumed by the controller. "
                    "The AOI ignores its leading four-byte `Pad` and interprets "
                    "the following four bytes as drive status and speed feedback."
                ),
                (
                    "- The output assembly is produced by the controller and "
                    "consumed by the drive as a logic command and speed reference."
                ),
                (
                    "- The AOI limits `LogicCommand` to `16#007F`; therefore "
                    "bits 7–15 defined by the datatype are deliberately cleared "
                    "by this implementation."
                ),
                (
                    "- `SpeedCommand` is written as frequency in hertz multiplied "
                    "by 100, after clamping to zero and the captured maximum-speed "
                    "limit. The transmitted integer therefore has 0.01 Hz/count."
                ),
                (
                    "- `OutputSpeed` is captured as a raw signed 16-bit cyclic "
                    "feedback field. This AOI does not expose an observed scaling "
                    "assignment for it, so TwinForge does not invent one."
                ),
                "",
            ]
        )
        if contract.diagnostics:
            lines.extend(["## Diagnostics", ""])
            lines.extend(f"- {item}" for item in contract.diagnostics)
            lines.append("")
        return "\n".join(lines)


def _image(image: CyclicIOImage) -> list[str]:
    heading = "Input/status image" if image.role == "status" else "Output/command image"
    lines = [
        f"## {heading}",
        "",
        f"- AOI parameter: `{image.parameter_name}`",
        f"- Parameter datatype: `{image.parameter_data_type}`",
        f"- Connection point: {_value(image.connection_point)}",
        f"- Configured size: {_bytes(image.configured_size_bytes)}",
        f"- AOI copy size: {_bytes(image.copied_size_bytes)}",
        f"- Internal typed image: `{image.local_path or 'not resolved'}`",
        "",
        "| Byte(s) | Bit | Field | Type | Meaning |",
        "| --- | --- | --- | --- | --- |",
    ]
    for field in image.fields:
        byte_range = (
            str(field.byte_offset)
            if field.byte_size <= 1
            else f"{field.byte_offset}–{field.byte_offset + field.byte_size - 1}"
        )
        lines.append(
            f"| {byte_range} | {_value(field.bit_number)} "
            f"| `{field.name}` | `{field.data_type or 'unknown'}` "
            f"| {_cell(field.description)} |"
        )
    lines.append("")
    return lines


def _yes_no(value: bool | None) -> str:
    if value is None:
        return "not captured"
    return "yes" if value else "no"


def _value(value: object | None) -> str:
    return "—" if value is None else str(value)


def _bytes(value: int | None) -> str:
    return "not captured" if value is None else f"{value} bytes"


def _cell(value: str | None) -> str:
    return (value or "—").replace("|", r"\|").replace("\n", " ")
