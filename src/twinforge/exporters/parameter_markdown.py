"""Markdown inventory of observed device-parameter access."""

from __future__ import annotations

from twinforge.model import Device


class ParameterMarkdownExporter:
    """Render software-observed parameter access for one assembled device."""

    def export(
        self,
        device: Device,
        *,
        title: str | None = None,
    ) -> str:
        """Return a deterministic parameter inventory."""

        lines = [
            f"# {title or f'{device.name} observed parameter inventory'}",
            "",
            (
                "These entries are candidates observed in controller-software "
                "branches. They are not proof that every parameter is accessed "
                "on every scan or device configuration."
            ),
            "",
            "| Number | Code | Name | Group | Read | Write | "
            "Read buffer slots |",
            "| ---: | --- | --- | :---: | :---: | :---: | --- |",
        ]
        for parameter in sorted(
            device.observed_parameters,
            key=lambda item: item.number,
        ):
            slots = ", ".join(
                str(index) for index in parameter.read_buffer_indices
            )
            lines.append(
                f"| {parameter.number} "
                f"| {_cell(parameter.code)} "
                f"| {_cell(parameter.display_name)} "
                f"| {_cell(parameter.group_name or parameter.group_prefix)} "
                f"| {_yes_no(parameter.observed_read)} "
                f"| {_yes_no(parameter.observed_write)} "
                f"| {_cell(slots)} |"
            )
        return "\n".join(lines).rstrip() + "\n"


def _cell(value: str | None) -> str:
    if not value:
        return "—"
    return value.replace("|", "\\|").replace("\n", "<br>")


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
