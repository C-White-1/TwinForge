from twinforge.exporters import LadderSvgExporter
from twinforge.model import (
    LadderInstruction,
    LadderOperation,
    LadderParallel,
    LadderPosition,
    LadderRung,
    LadderSeries,
)


def _instruction(
    operation: LadderOperation,
    operand: str,
    column: int,
    *,
    mnemonic: str = "CONTACT_P",
) -> LadderInstruction:
    return LadderInstruction(
        operation=operation,
        source_mnemonic=mnemonic,
        operand=operand,
        position=LadderPosition(column=column, row=0),
    )


def _series_rung(number: int, elements: tuple) -> LadderRung:
    return LadderRung(number=number, network=LadderSeries(elements=elements))


def test_renders_series_contacts_and_coil():
    rung = _series_rung(
        0,
        (
            _instruction(LadderOperation.NORMALLY_OPEN_CONTACT, "A", 0),
            _instruction(LadderOperation.NORMALLY_CLOSED_CONTACT, "B", 2),
            _instruction(LadderOperation.COIL, "Out", 11, mnemonic="COIL_P"),
        ),
    )

    svg = LadderSvgExporter().export([rung])

    assert svg.startswith("<svg ")
    assert svg.endswith("</svg>")
    assert ">A<" in svg
    assert ">B<" in svg
    assert ">Out<" in svg
    # Normally-closed contact gets a diagonal slash the open contact lacks.
    assert svg.count('stroke-dasharray') == 0
    assert svg.count("<circle") == 1


def test_renders_set_and_reset_coil_markers():
    rung = _series_rung(
        0,
        (
            _instruction(LadderOperation.SET_COIL, "S1", 0, mnemonic="COIL_S"),
        ),
    )
    other = _series_rung(
        1,
        (
            _instruction(LadderOperation.RESET_COIL, "R1", 0, mnemonic="COIL_R"),
        ),
    )

    svg = LadderSvgExporter().export([rung, other])

    assert '>S<' in svg
    assert '>R<' in svg


def test_renders_block_output_reference_as_dashed_labeled_box():
    rung = _series_rung(
        0,
        (
            _instruction(
                LadderOperation.BLOCK_OUTPUT_REFERENCE,
                "Heating_control.A",
                5,
                mnemonic="SR",
            ),
            _instruction(LadderOperation.COIL, "Out", 11, mnemonic="COIL_P"),
        ),
    )

    svg = LadderSvgExporter().export([rung])

    assert "stroke-dasharray" in svg
    assert "Heating_control.A" in svg


def test_renders_unsupported_operation_with_mnemonic():
    rung = _series_rung(
        0,
        (
            _instruction(
                LadderOperation.UNSUPPORTED,
                "Edge",
                3,
                mnemonic="PContact",
            ),
            _instruction(LadderOperation.COIL, "Out", 11, mnemonic="COIL_P"),
        ),
    )

    svg = LadderSvgExporter().export([rung])

    assert "Edge (PContact)" in svg
    assert 'fill="#a00"' in svg


def test_renders_parallel_branch_as_explicit_placeholder_not_silently_dropped():
    rung = _series_rung(
        0,
        (
            LadderParallel(
                branches=(
                    LadderSeries(elements=(_instruction(LadderOperation.NORMALLY_OPEN_CONTACT, "A", 0),)),
                    LadderSeries(elements=(_instruction(LadderOperation.NORMALLY_OPEN_CONTACT, "B", 0),)),
                )
            ),
        ),
    )

    svg = LadderSvgExporter().export([rung])

    assert "not yet rendered" in svg
    # Neither branch's own contacts are guessed at and drawn.
    assert ">A<" not in svg
    assert ">B<" not in svg


def test_rung_with_no_network_renders_empty_row():
    rung = LadderRung(number=0, network=None)

    svg = LadderSvgExporter().export([rung])

    assert svg.startswith("<svg ")
    assert ">0<" in svg


def test_export_is_deterministic():
    rung = _series_rung(
        0,
        (
            _instruction(LadderOperation.NORMALLY_OPEN_CONTACT, "A", 0),
            _instruction(LadderOperation.COIL, "Out", 11, mnemonic="COIL_P"),
        ),
    )

    first = LadderSvgExporter().export([rung], title="determinism check")
    second = LadderSvgExporter().export([rung], title="determinism check")

    assert first == second


def test_multi_rung_layout_sizes_by_max_row_and_column():
    narrow = _series_rung(
        0,
        (_instruction(LadderOperation.NORMALLY_OPEN_CONTACT, "A", 0),),
    )
    wide = _series_rung(
        3,
        (_instruction(LadderOperation.COIL, "Out", 11, mnemonic="COIL_P"),),
    )

    svg = LadderSvgExporter().export([narrow, wide])

    assert ">0<" in svg
    assert ">3<" in svg
    # Four rows (0..3) tall, twelve columns (0..11) wide.
    width_attr = svg.split('width="', 1)[1].split('"', 1)[0]
    height_attr = svg.split('height="', 1)[1].split('"', 1)[0]
    assert int(width_attr) > int(height_attr)
