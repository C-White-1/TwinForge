from dataclasses import dataclass


@dataclass
class _RtcPulseSemanticOracle:
    """Executable oracle for the captured RTC_PulseGen equations."""

    interval_ms: int = 1000
    previous_enable: bool = False
    start_microseconds: int = 0
    enabled: bool = False
    pulse: bool = False

    def scan(
        self,
        now_milliseconds: int,
        *,
        input_enable: bool,
        clock_ok: bool = True,
    ) -> bool:
        """Execute one scan using the mapped CODESYS clock boundary."""

        if not clock_ok:
            self.enabled = False
            self.pulse = False
            return self.pulse

        now_microseconds = now_milliseconds * 1000
        if (
            input_enable
            and not self.previous_enable
            or self.pulse
        ):
            self.start_microseconds = now_microseconds
        self.previous_enable = input_enable
        self.enabled = input_enable
        self.pulse = input_enable and (
            now_microseconds - self.start_microseconds
            >= self.interval_ms * 1000
        )
        return self.pulse


def test_rising_enable_continuous_enable_disable_and_reenable():
    pulse = _RtcPulseSemanticOracle()

    assert not pulse.scan(0, input_enable=False)
    assert not pulse.scan(20, input_enable=True)
    assert pulse.enabled
    assert pulse.previous_enable
    assert not pulse.scan(500, input_enable=True)
    assert not pulse.scan(600, input_enable=False)
    assert not pulse.enabled
    assert not pulse.previous_enable
    assert not pulse.scan(700, input_enable=True)
    assert pulse.start_microseconds == 700_000


def test_interval_boundary_produces_exactly_one_high_scan():
    pulse = _RtcPulseSemanticOracle()

    assert not pulse.scan(0, input_enable=True)
    assert not pulse.scan(999, input_enable=True)
    assert pulse.scan(1000, input_enable=True)
    assert not pulse.scan(1020, input_enable=True)
    assert pulse.start_microseconds == 1_020_000


def test_one_scan_pulse_width_is_independent_of_task_period():
    for task_period_ms in (10, 20, 50):
        pulse = _RtcPulseSemanticOracle()
        samples = [
            pulse.scan(now, input_enable=True)
            for now in range(0, 1100, task_period_ms)
        ]

        assert sum(samples) == 1


def test_clock_failure_suppresses_outputs_and_backward_time_does_not_pulse():
    pulse = _RtcPulseSemanticOracle()

    assert not pulse.scan(1000, input_enable=True)
    assert not pulse.scan(2000, input_enable=True, clock_ok=False)
    assert not pulse.enabled
    assert not pulse.pulse
    assert not pulse.scan(900, input_enable=True)
    assert pulse.scan(2000, input_enable=True)
