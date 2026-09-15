from __future__ import annotations

import numpy as np
import pytest

from ncmemsim.paired_pulse_protocol import (
    PairedPulseMemoryProtocol,
    PairedPulseMemoryResult,
    run_paired_pulse_memory_protocol,
)
from ncmemsim.physics import PhysicsModel
from ncmemsim.reference import make_v53_reference_device
from ncmemsim.simulator import SimulationConfig, Simulator
from ncmemsim.state import DeviceState


def _simulator():
    device = make_v53_reference_device(grid_points=7)
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
    program_voltage=3.0,
    erase_voltage=-3.0,
    program_time=1.0e-3,
    erase_time=1.0e-3,
    read_voltage=0.0,
):
    return PairedPulseMemoryProtocol(
        program_voltage_V=program_voltage,
        program_time_s=program_time,
        erase_voltage_V=erase_voltage,
        erase_time_s=erase_time,
        read_voltage_V=read_voltage,
        pulse_internal_dt_s=1.0e-5,
    )


def _partially_occupied_reference(device):
    state = DeviceState.empty_for_device(device)

    for fg_state in state.floating_gates:
        fg_state.P0[:] = 0.5
        fg_state.P1[:] = 0.5
        fg_state.P2[:] = 0.0

    state.validate(device)
    return state


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("program_time_s", 0.0),
        ("program_time_s", -1.0e-3),
        ("erase_time_s", 0.0),
        ("erase_time_s", -1.0e-3),
    ],
)
def test_protocol_requires_positive_pulse_times(field, value):
    kwargs = dict(
        program_voltage_V=3.0,
        program_time_s=1.0e-3,
        erase_voltage_V=-3.0,
        erase_time_s=1.0e-3,
    )
    kwargs[field] = value

    with pytest.raises(ValueError, match="strictly positive"):
        PairedPulseMemoryProtocol(**kwargs)


def test_protocol_requires_distinct_program_and_erase_voltages():
    with pytest.raises(ValueError, match="must be different"):
        _protocol(
            program_voltage=2.0,
            erase_voltage=2.0,
        )


def test_protocol_hash_is_deterministic():
    assert _protocol().protocol_hash() == _protocol().protocol_hash()


def test_protocol_hash_changes_with_erase_voltage():
    assert (
        _protocol(erase_voltage=-3.0).protocol_hash()
        != _protocol(erase_voltage=-4.0).protocol_hash()
    )


def test_default_reference_state_is_empty():
    device, simulator = _simulator()

    result = run_paired_pulse_memory_protocol(
        simulator,
        _protocol(),
    )

    assert isinstance(result, PairedPulseMemoryResult)
    result.reference_state.validate(device)

    for fg_state in result.reference_state.floating_gates:
        assert np.allclose(fg_state.P0, 1.0)
        assert np.allclose(fg_state.P1, 0.0)
        assert np.allclose(fg_state.P2, 0.0)


def test_program_and_erase_start_from_same_reference():
    device, simulator = _simulator()
    reference = _partially_occupied_reference(device)

    result = run_paired_pulse_memory_protocol(
        simulator,
        _protocol(),
        reference_state=reference,
    )

    for ref_fg, program_fg, erase_fg in zip(
        result.reference_state.floating_gates,
        result.program.initial_state.floating_gates,
        result.erase.initial_state.floating_gates,
    ):
        assert np.array_equal(ref_fg.P0, program_fg.P0)
        assert np.array_equal(ref_fg.P1, program_fg.P1)
        assert np.array_equal(ref_fg.P2, program_fg.P2)
        assert np.array_equal(ref_fg.P0, erase_fg.P0)
        assert np.array_equal(ref_fg.P1, erase_fg.P1)
        assert np.array_equal(ref_fg.P2, erase_fg.P2)


def test_reference_state_is_not_mutated():
    device, simulator = _simulator()
    reference = _partially_occupied_reference(device)
    before = reference.copy()

    run_paired_pulse_memory_protocol(
        simulator,
        _protocol(),
        reference_state=reference,
    )

    assert reference.time_s == before.time_s
    for lhs, rhs in zip(
        reference.floating_gates,
        before.floating_gates,
    ):
        assert np.array_equal(lhs.P0, rhs.P0)
        assert np.array_equal(lhs.P1, rhs.P1)
        assert np.array_equal(lhs.P2, rhs.P2)


def test_branch_times_are_independent_from_reference():
    device, simulator = _simulator()
    reference = _partially_occupied_reference(device)
    protocol = _protocol(
        program_time=2.0e-3,
        erase_time=3.0e-3,
    )

    result = run_paired_pulse_memory_protocol(
        simulator,
        protocol,
        reference_state=reference,
    )

    assert result.program.pulsed_state.time_s == pytest.approx(
        reference.time_s + 2.0e-3
    )
    assert result.erase.pulsed_state.time_s == pytest.approx(
        reference.time_s + 3.0e-3
    )


def test_zero_dwell_reads_do_not_advance_branch_times():
    device, simulator = _simulator()
    reference = _partially_occupied_reference(device)

    result = run_paired_pulse_memory_protocol(
        simulator,
        _protocol(),
        reference_state=reference,
    )

    assert result.program.read_state.time_s == pytest.approx(
        result.program.pulsed_state.time_s
    )
    assert result.erase.read_state.time_s == pytest.approx(
        result.erase.pulsed_state.time_s
    )


def test_zero_dwell_reads_preserve_branch_occupations():
    device, simulator = _simulator()
    reference = _partially_occupied_reference(device)

    result = run_paired_pulse_memory_protocol(
        simulator,
        _protocol(),
        reference_state=reference,
    )

    for branch in (result.program, result.erase):
        for pulsed, read in zip(
            branch.pulsed_state.floating_gates,
            branch.read_state.floating_gates,
        ):
            np.testing.assert_allclose(
                pulsed.P0,
                read.P0,
                rtol=0.0,
                atol=1.0e-15,
            )
            np.testing.assert_allclose(
                pulsed.P1,
                read.P1,
                rtol=0.0,
                atol=1.0e-15,
            )
            np.testing.assert_allclose(
                pulsed.P2,
                read.P2,
                rtol=0.0,
                atol=1.0e-15,
            )


def test_memory_window_matches_delta_vfb_separation():
    device, simulator = _simulator()
    reference = _partially_occupied_reference(device)

    result = run_paired_pulse_memory_protocol(
        simulator,
        _protocol(),
        reference_state=reference,
    )

    expected = (
        result.program.delta_vfb_V
        - result.erase.delta_vfb_V
    )

    assert result.memory_window_V == pytest.approx(expected)
    assert result.memory_window_magnitude_V == pytest.approx(
        abs(expected)
    )


def test_program_and_erase_generate_distinct_states():
    device, simulator = _simulator()
    reference = _partially_occupied_reference(device)

    result = run_paired_pulse_memory_protocol(
        simulator,
        _protocol(),
        reference_state=reference,
    )

    assert result.program.delta_vfb_V != pytest.approx(
        result.erase.delta_vfb_V,
        abs=1.0e-15,
    )
    assert result.memory_window_magnitude_V > 0.0


def test_result_arrays_are_read_only():
    device, simulator = _simulator()
    reference = _partially_occupied_reference(device)

    result = run_paired_pulse_memory_protocol(
        simulator,
        _protocol(),
        reference_state=reference,
    )

    for branch in (result.program, result.erase):
        assert not branch.delta_vfb_by_fg_V.flags.writeable
        assert not branch.qfg_by_fg_C_m2.flags.writeable
        assert not branch.mean_occupation_by_fg.flags.writeable


def test_result_shapes_follow_number_of_fgs():
    device, simulator = _simulator()
    reference = _partially_occupied_reference(device)

    result = run_paired_pulse_memory_protocol(
        simulator,
        _protocol(),
        reference_state=reference,
    )

    n_fgs = device.number_of_fgs()

    for branch in (result.program, result.erase):
        assert branch.delta_vfb_by_fg_V.shape == (n_fgs,)
        assert branch.qfg_by_fg_C_m2.shape == (n_fgs,)
        assert branch.mean_occupation_by_fg.shape == (n_fgs,)


def test_serialization_distinguishes_pulse_memory_from_cv_hysteresis():
    device, simulator = _simulator()
    reference = _partially_occupied_reference(device)
    protocol = _protocol()

    result = run_paired_pulse_memory_protocol(
        simulator,
        protocol,
        reference_state=reference,
    )

    payload = result.to_dict()

    assert (
        payload["workflow"]
        == "paired-program-erase-pulse-memory-window"
    )
    assert (
        payload["memory_window_definition"]
        == "delta_vfb_programmed_minus_delta_vfb_erased"
    )
    assert payload["protocol_hash"] == protocol.protocol_hash()
    assert payload["program"]["role"] == "program"
    assert payload["erase"]["role"] == "erase"


def test_read_voltage_does_not_change_branch_occupations():
    device, simulator = _simulator()
    reference = _partially_occupied_reference(device)

    zero_read = run_paired_pulse_memory_protocol(
        simulator,
        _protocol(read_voltage=0.0),
        reference_state=reference,
    )
    one_read = run_paired_pulse_memory_protocol(
        simulator,
        _protocol(read_voltage=1.0),
        reference_state=reference,
    )

    for branch_name in ("program", "erase"):
        zero_branch = getattr(zero_read, branch_name)
        one_branch = getattr(one_read, branch_name)

        for zero_fg, one_fg in zip(
            zero_branch.read_state.floating_gates,
            one_branch.read_state.floating_gates,
        ):
            assert np.array_equal(zero_fg.P0, one_fg.P0)
            assert np.array_equal(zero_fg.P1, one_fg.P1)
            assert np.array_equal(zero_fg.P2, one_fg.P2)
