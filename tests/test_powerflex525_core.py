from twinforge.runtime import (
    PowerFlex525Core,
    PowerFlexCommandSource,
    PowerFlexCommands,
    PowerFlexCoreInput,
)


def _input(**changes):
    values = {
        "source": PowerFlexCommandSource.PROGRAM,
        "program": PowerFlexCommands(run_forward=True, speed_hz=45.25),
        "drive_ready": True,
        "ethernet_logic_control": True,
        "maximum_speed_hz": 60.0,
    }
    values.update(changes)
    return PowerFlexCoreInput(**values)


def test_program_run_is_level_triggered_and_speed_is_scaled():
    core = PowerFlex525Core()

    running = core.scan(_input())
    released = core.scan(
        _input(program=PowerFlexCommands(speed_hz=45.25))
    )

    assert running.run_forward is True
    assert running.logic_command == 0b0001_0010
    assert running.speed_command == 4525
    assert released.run_forward is False


def test_operator_run_latches_until_stop_or_interlock_failure():
    core = PowerFlex525Core()
    start = _input(
        source=PowerFlexCommandSource.OPERATOR,
        operator=PowerFlexCommands(run_forward=True, speed_hz=20.0),
    )

    assert core.scan(start).run_forward is True
    assert core.scan(
        _input(
            source=PowerFlexCommandSource.OPERATOR,
            operator=PowerFlexCommands(speed_hz=20.0),
        )
    ).run_forward is True
    assert core.scan(
        _input(
            source=PowerFlexCommandSource.OPERATOR,
            operator=PowerFlexCommands(stop=True, speed_hz=20.0),
        )
    ).run_forward is False


def test_running_program_command_survives_bypassable_permissive_loss():
    core = PowerFlex525Core()

    core.scan(_input())
    result = core.scan(_input(permissive_ok=False))

    assert result.permissives_ok is False
    assert result.run_forward is True


def test_non_bypassable_interlock_stops_even_with_bypass():
    core = PowerFlex525Core()

    core.scan(_input())
    result = core.scan(
        _input(
            bypass_active=True,
            non_bypassable_interlock_ok=False,
        )
    )

    assert result.interlocks_ok is False
    assert result.run_forward is False


def test_start_delay_uses_elapsed_scan_time():
    core = PowerFlex525Core()

    first = core.scan(_input(start_delay_ms=100, elapsed_ms=40))
    second = core.scan(_input(start_delay_ms=100, elapsed_ms=60))

    assert first.starting is True
    assert first.logic_command & 0b10 == 0
    assert second.starting is False
    assert second.logic_command & 0b10


def test_speed_reference_is_clamped_and_jog_uses_jog_speed():
    core = PowerFlex525Core()

    high = core.scan(
        _input(program=PowerFlexCommands(run_forward=True, speed_hz=99.0))
    )
    jog = core.scan(
        _input(
            program=PowerFlexCommands(jog_forward=True),
            jog_speed_hz=12.34,
        )
    )

    assert high.speed_command == 6000
    assert jog.jog_forward is True
    assert jog.speed_command == 1234
    assert jog.logic_command & 0b0001_0100 == 0b0001_0100


def test_program_jog_retains_source_precedence_behavior():
    core = PowerFlex525Core()

    result = core.scan(
        _input(
            program=PowerFlexCommands(jog_forward=True),
            permissive_ok=False,
            jog_forward_available=False,
            jog_speed_hz=5.0,
        )
    )

    assert result.permissives_ok is False
    assert result.jog_forward is True


def test_prescan_does_not_invent_a_retained_state_reset():
    core = PowerFlex525Core()
    core.scan(_input(start_delay_ms=100, elapsed_ms=50))

    core.prescan()

    assert core.state.run_forward is True
    assert core.state.start_elapsed_ms == 50


def test_explicit_target_policy_can_clear_retained_state():
    core = PowerFlex525Core()
    core.scan(_input(start_delay_ms=100, elapsed_ms=50))

    core.state.reset()

    assert core.state.run_forward is False
    assert core.state.start_elapsed_ms == 0
