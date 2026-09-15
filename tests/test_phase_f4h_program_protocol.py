from __future__ import annotations

import numpy as np
import pytest

from ncmemsim.program_protocol import (
    ProgramPulseReadProtocol,
    ProgramPulseReadResult,
    run_program_pulse_read,
)
from ncmemsim.physics import PhysicsModel
from ncmemsim.reference import make_v53_reference_device
from ncmemsim.simulator import (
    SimulationConfig,
    Simulator,
)
from ncmemsim.state import DeviceState


def _simulator():
    device = make_v53_reference_device(
        grid_points=7,
    )
    simulator = Simulator(
        device,
        PhysicsModel.default(),
        SimulationConfig(
            dwell_time_s=5.0e-3,
            internal_dt_s=1.0e-5,
        ),
    )
    return device, simulator


def _protocol(
    *,
    voltage=3.0,
    time_s=1.0e-3,
    read_voltage=0.0,
):
    return ProgramPulseReadProtocol(
        program_voltage_V=voltage,
        programming_time_s=time_s,
        read_voltage_V=read_voltage,
        program_internal_dt_s=1.0e-5,
    )


@pytest.mark.parametrize(
    "time_s",
    [0.0, -1.0e-3],
)
def test_protocol_requires_positive_programming_time(
    time_s,
):
    with pytest.raises(
        ValueError,
        match="strictly positive",
    ):
        _protocol(time_s=time_s)


@pytest.mark.parametrize(
    "field_name",
    [
        "program_voltage_V",
        "programming_time_s",
        "read_voltage_V",
        "program_internal_dt_s",
    ],
)
def test_protocol_rejects_nonfinite_values(
    field_name,
):
    kwargs = {
        "program_voltage_V": 3.0,
        "programming_time_s": 1.0e-3,
        "read_voltage_V": 0.0,
        "program_internal_dt_s": 1.0e-5,
    }
    kwargs[field_name] = float("nan")

    with pytest.raises(ValueError):
        ProgramPulseReadProtocol(**kwargs)


def test_protocol_hash_is_deterministic():
    first = _protocol()
    second = _protocol()

    assert (
        first.protocol_hash()
        == second.protocol_hash()
    )


def test_protocol_hash_changes_with_programming_time():
    first = _protocol(time_s=1.0e-3)
    second = _protocol(time_s=2.0e-3)

    assert (
        first.protocol_hash()
        != second.protocol_hash()
    )


def test_default_initial_state_is_empty():
    device, simulator = _simulator()

    result = run_program_pulse_read(
        simulator,
        _protocol(),
    )

    assert isinstance(
        result,
        ProgramPulseReadResult,
    )
    assert result.initial_state.time_s == 0.0

    for fg_state in result.initial_state.floating_gates:
        assert np.allclose(fg_state.P0, 1.0)
        assert np.allclose(fg_state.P1, 0.0)
        assert np.allclose(fg_state.P2, 0.0)

    result.initial_state.validate(device)


def test_program_pulse_advances_state_time_by_pulse_duration():
    _, simulator = _simulator()
    protocol = _protocol(time_s=2.0e-3)

    result = run_program_pulse_read(
        simulator,
        protocol,
    )

    assert (
        result.programmed_state.time_s
        == pytest.approx(2.0e-3)
    )


def test_zero_dwell_read_does_not_advance_time():
    _, simulator = _simulator()
    protocol = _protocol(time_s=2.0e-3)

    result = run_program_pulse_read(
        simulator,
        protocol,
    )

    assert (
        result.read_state.time_s
        == pytest.approx(
            result.programmed_state.time_s
        )
    )


def test_zero_dwell_read_preserves_occupations():
    _, simulator = _simulator()

    result = run_program_pulse_read(
        simulator,
        _protocol(),
    )

    for programmed, read in zip(
        result.programmed_state.floating_gates,
        result.read_state.floating_gates,
    ):
        assert np.array_equal(
            programmed.P0,
            read.P0,
        )
        assert np.array_equal(
            programmed.P1,
            read.P1,
        )
        assert np.array_equal(
            programmed.P2,
            read.P2,
        )


def test_supplied_initial_state_is_not_mutated():
    device, simulator = _simulator()
    initial = DeviceState.empty_for_device(device)
    before = initial.copy()

    run_program_pulse_read(
        simulator,
        _protocol(),
        initial_state=initial,
    )

    assert initial.time_s == before.time_s
    for lhs, rhs in zip(
        initial.floating_gates,
        before.floating_gates,
    ):
        assert np.array_equal(lhs.P0, rhs.P0)
        assert np.array_equal(lhs.P1, rhs.P1)
        assert np.array_equal(lhs.P2, rhs.P2)


def test_positive_program_pulse_changes_charge():
    _, simulator = _simulator()

    result = run_program_pulse_read(
        simulator,
        _protocol(voltage=3.0),
    )

    assert abs(result.qfg_C_m2) > 0.0
    assert (
        abs(result.delta_vfb_V) > 0.0
    )


def test_longer_programming_time_changes_delta_vfb():
    _, simulator = _simulator()

    short = run_program_pulse_read(
        simulator,
        _protocol(time_s=1.0e-4),
    )
    long = run_program_pulse_read(
        simulator,
        _protocol(time_s=1.0e-3),
    )

    assert (
        long.delta_vfb_V
        != pytest.approx(
            short.delta_vfb_V,
            abs=1.0e-15,
        )
    )


def test_result_arrays_are_read_only():
    _, simulator = _simulator()

    result = run_program_pulse_read(
        simulator,
        _protocol(),
    )

    assert not result.delta_vfb_by_fg_V.flags.writeable
    assert not result.qfg_by_fg_C_m2.flags.writeable
    assert (
        not result.mean_occupation_by_fg.flags.writeable
    )


def test_result_serialization_uses_delta_vfb_not_memory_window():
    _, simulator = _simulator()
    protocol = _protocol()

    result = run_program_pulse_read(
        simulator,
        protocol,
    )
    payload = result.to_dict()

    assert (
        payload["workflow"]
        == "electrical-program-pulse-nondestructive-read"
    )
    assert payload["observable"] == {
        "name": "delta_vfb",
        "unit": "V",
        "value": result.delta_vfb_V,
    }
    assert "memory_window" not in payload
    assert (
        payload["protocol_hash"]
        == protocol.protocol_hash()
    )


def test_result_shapes_follow_number_of_fgs():
    device, simulator = _simulator()

    result = run_program_pulse_read(
        simulator,
        _protocol(),
    )

    n_fgs = device.number_of_fgs()
    assert result.delta_vfb_by_fg_V.shape == (n_fgs,)
    assert result.qfg_by_fg_C_m2.shape == (n_fgs,)
    assert result.mean_occupation_by_fg.shape == (n_fgs,)


def test_read_voltage_is_explicit_but_read_is_nondestructive():
    _, simulator = _simulator()

    zero = run_program_pulse_read(
        simulator,
        _protocol(read_voltage=0.0),
    )
    one = run_program_pulse_read(
        simulator,
        _protocol(read_voltage=1.0),
    )

    # The read bias may change instantaneous electrostatic observables,
    # but it must not alter the programmed occupation state at zero dwell.
    for zero_fg, one_fg in zip(
        zero.read_state.floating_gates,
        one.read_state.floating_gates,
    ):
        assert np.array_equal(
            zero_fg.P0,
            one_fg.P0,
        )
        assert np.array_equal(
            zero_fg.P1,
            one_fg.P1,
        )
        assert np.array_equal(
            zero_fg.P2,
            one_fg.P2,
        )
