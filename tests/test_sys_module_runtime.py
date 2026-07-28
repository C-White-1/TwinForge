from dataclasses import dataclass, field

from twinforge.runtime import (
    SysModuleAdapterError,
    SysModuleRuntime,
    SysModuleSnapshot,
)


@dataclass
class FakeSysModuleAdapter:
    snapshot: SysModuleSnapshot
    read_failures: list[SysModuleAdapterError] = field(default_factory=list)
    write_failures: list[SysModuleAdapterError] = field(default_factory=list)
    written_modes: list[int] = field(default_factory=list)
    read_count: int = 0

    def read_snapshot(self) -> SysModuleSnapshot:
        self.read_count += 1
        if self.read_failures:
            raise self.read_failures.pop(0)
        return self.snapshot

    def write_mode(self, mode: int) -> None:
        if self.write_failures:
            raise self.write_failures.pop(0)
        self.written_modes.append(mode)


def snapshot(*, mode: int = 0, entry_status: int = 0x4000) -> SysModuleSnapshot:
    return SysModuleSnapshot(
        instance=7,
        entry_status=entry_status,
        fault_code=0,
        fault_info=0,
        mode=mode,
    )


def test_successful_read_returns_decoded_outputs():
    adapter = FakeSysModuleAdapter(snapshot())

    result = SysModuleRuntime(adapter).cycle()

    assert result.outputs.snapshot.instance == 7
    assert result.outputs.status.connected
    assert result.read_failure is None
    assert result.write_failure is None
    assert adapter.read_count == 1


def test_inhibit_edge_writes_mode_with_inhibit_bit_set():
    adapter = FakeSysModuleAdapter(snapshot(mode=0x0010))

    result = SysModuleRuntime(adapter).cycle(input_inhibit=True)

    assert result.mode_write is not None
    assert result.mode_write.mode == 0x0014
    assert adapter.written_modes == [0x0014]


def test_uninhibit_edge_writes_mode_with_inhibit_bit_cleared():
    adapter = FakeSysModuleAdapter(snapshot(mode=0x0014))

    result = SysModuleRuntime(adapter).cycle(input_uninhibit=True)

    assert result.mode_write is not None
    assert result.mode_write.mode == 0x0010
    assert adapter.written_modes == [0x0010]


def test_read_failure_preserves_outputs_and_does_not_consume_edge():
    adapter = FakeSysModuleAdapter(snapshot())
    runtime = SysModuleRuntime(adapter)
    baseline = runtime.cycle()
    adapter.read_failures.append(
        SysModuleAdapterError("read-timeout", "module read timed out")
    )

    failed = runtime.cycle(input_inhibit=True)
    recovered = runtime.cycle(input_inhibit=True)

    assert failed.outputs == baseline.outputs
    assert failed.read_failure is not None
    assert failed.read_failure.code == "read-timeout"
    assert failed.read_failure.message == "module read timed out"
    assert failed.mode_write is None
    assert recovered.mode_write is not None
    assert adapter.written_modes == [0x0004]


def test_write_failure_is_reported_without_automatic_retry():
    adapter = FakeSysModuleAdapter(
        snapshot(),
        write_failures=[
            SysModuleAdapterError("write-rejected", "Mode write rejected")
        ],
    )
    runtime = SysModuleRuntime(adapter)

    failed = runtime.cycle(input_inhibit=True)
    held = runtime.cycle(input_inhibit=True)
    runtime.cycle(input_inhibit=False)
    retried = runtime.cycle(input_inhibit=True)

    assert failed.mode_write is not None
    assert failed.write_failure is not None
    assert failed.write_failure.code == "write-rejected"
    assert held.mode_write is None
    assert retried.mode_write is not None
    assert adapter.written_modes == [0x0004]


def test_prescan_does_not_access_adapter():
    adapter = FakeSysModuleAdapter(snapshot())
    runtime = SysModuleRuntime(adapter)

    result = runtime.prescan()

    assert result.input_inhibit is False
    assert result.input_uninhibit is False
    assert adapter.read_count == 0
    assert adapter.written_modes == []
