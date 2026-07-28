import pytest

from twinforge.runtime import (
    SysModuleCore,
    SysModuleSnapshot,
    decode_entry_status,
)


@pytest.mark.parametrize(
    ("entry_status", "active"),
    [
        (0x0000, "standby"),
        (0x1000, "faulted"),
        (0x2000, "validating"),
        (0x3000, "connecting"),
        (0x4000, "connected"),
        (0x5000, "shutting_down"),
        (0x6000, "inhibited"),
        (0x7000, "waiting"),
        (0x9000, "firmware_updating"),
        (0xA000, "configuring"),
    ],
)
def test_decodes_every_documented_entry_status(
    entry_status: int,
    active: str,
) -> None:
    status = decode_entry_status(entry_status | 0x0123)
    named_states = {
        "standby": status.standby,
        "faulted": status.faulted,
        "validating": status.validating,
        "connecting": status.connecting,
        "connected": status.connected,
        "shutting_down": status.shutting_down,
        "inhibited": status.inhibited,
        "waiting": status.waiting,
        "firmware_updating": status.firmware_updating,
        "configuring": status.configuring,
    }

    assert [name for name, enabled in named_states.items() if enabled] == [
        active
    ]
    assert status.disconnected is (
        active not in {"connected", "inhibited"}
    )


@pytest.mark.parametrize("entry_status", [0x8000, 0xB000, 0xC000, 0xF000])
def test_unknown_entry_states_are_only_disconnected(
    entry_status: int,
) -> None:
    status = decode_entry_status(entry_status)

    assert status.word == 1 << 11


def test_inhibit_and_uninhibit_use_one_shared_rising_edge_latch() -> None:
    core = SysModuleCore()
    snapshot = SysModuleSnapshot(mode=0x0010)

    first = core.scan(snapshot, input_inhibit=True)
    held = core.scan(snapshot, input_inhibit=True)
    switched_without_release = core.scan(snapshot, input_uninhibit=True)
    released = core.scan(snapshot)
    uninhibited = core.scan(
        SysModuleSnapshot(mode=0x0014),
        input_uninhibit=True,
    )

    assert first.mode_write is not None
    assert first.mode_write.mode == 0x0014
    assert held.mode_write is None
    assert switched_without_release.mode_write is None
    assert released.mode_write is None
    assert uninhibited.mode_write is not None
    assert uninhibited.mode_write.mode == 0x0010


def test_simultaneous_commands_prioritize_inhibit() -> None:
    result = SysModuleCore().scan(
        SysModuleSnapshot(mode=0),
        input_inhibit=True,
        input_uninhibit=True,
    )

    assert result.mode_write is not None
    assert result.mode_write.mode == 0x0004


def test_scan_preserves_raw_diagnostic_outputs() -> None:
    snapshot = SysModuleSnapshot(
        instance=7,
        entry_status=0x4123,
        fault_code=11,
        fault_info=22,
        mode=4,
    )

    result = SysModuleCore().scan(snapshot)

    assert result.outputs.snapshot == snapshot
    assert result.outputs.status.connected
    assert result.outputs.status.word == 1 << 4


def test_prescan_clears_source_outputs_but_does_not_invent_osr_reset() -> None:
    core = SysModuleCore()
    core.scan(
        SysModuleSnapshot(
            instance=7,
            entry_status=0x4000,
            fault_code=11,
            fault_info=22,
            mode=4,
        ),
        input_inhibit=True,
    )

    prescan = core.prescan()
    still_held = core.scan(
        SysModuleSnapshot(mode=0),
        input_inhibit=True,
    )

    assert prescan.input_inhibit is False
    assert prescan.input_uninhibit is False
    assert prescan.outputs.snapshot == SysModuleSnapshot()
    assert prescan.outputs.status.word == 0
    assert still_held.mode_write is None
