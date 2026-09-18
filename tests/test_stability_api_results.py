"""Client-observable result shapes, missing-value semantics and ownership."""
from dataclasses import FrozenInstanceError
import importlib
import json
from pathlib import Path

import numpy as np
import pytest

from ncmemsim import DeviceBuilder, DeviceState, RetentionConfig, SimulationConfig, Simulator, make_gesn
from ncmemsim.optics import LightSource
from scripts.validate_api_contract import build_inventory, render_inventory

ROOT = Path(__file__).resolve().parents[1]


def _simulator(n_fgs):
    device = DeviceBuilder.v2(n_fgs, nc_material=make_gesn(0.08))
    for i, fg in enumerate(device.floating_gates()):
        fg.grid_points = 3 + i
    return Simulator(device, config=SimulationConfig(dwell_time_s=0.0))


def test_source_signatures_exports_and_fields_match_review_baseline():
    baseline = json.loads((ROOT / 'docs/api_inventory.json').read_text(encoding='utf-8'))
    actual = build_inventory(ROOT)
    assert actual == baseline, 'API baseline drift requires compatibility review'
    assert (ROOT / 'docs/api_inventory.md').read_text(encoding='utf-8') == render_inventory(baseline)


def test_every_explicit_export_and_documented_import_resolves():
    baseline = json.loads((ROOT / 'docs/api_inventory.json').read_text(encoding='utf-8'))
    for item in baseline['modules']:
        if item['explicit_exports'] is not None:
            module = importlib.import_module(item['module'])
            assert list(module.__all__) == item['explicit_exports']
            for name in item['explicit_exports']:
                assert hasattr(module, name), (item['module'], name)
    for path in baseline['documented_imports']:
        try:
            importlib.import_module(path)
        except ModuleNotFoundError as error:
            # Only fall back for a symbol, not an unrelated missing dependency.
            if error.name != path:
                raise
            module, _, name = path.rpartition('.')
            assert hasattr(importlib.import_module(module), name), path


@pytest.mark.parametrize('n_fgs', [1, 3])
@pytest.mark.parametrize('illuminated', [False, True])
@pytest.mark.parametrize('dwell', [0.0, 1e-5])
def test_relax_result_axes_dark_semantics_and_input_state(n_fgs, illuminated, dwell):
    sim = _simulator(n_fgs)
    state = DeviceState.empty_for_device(sim.device)
    state.time_s = 2.0
    light = LightSource.laser(wavelength_nm=1550.0, power_density_W_m2=1000.0) if illuminated else None
    result = sim.relax_voltage(state=state, gate_voltage_V=2.0, dwell_time_s=dwell, light_source=light)
    expected = json.loads((ROOT / 'docs/api_inventory.json').read_text(encoding='utf-8'))['result_dictionary_keys']['ncmemsim.simulator.Simulator.relax_voltage']
    assert set(result) == set(expected)
    assert result['state'] is not state
    assert result['state'].time_s == pytest.approx(2.0 + dwell)
    assert state.time_s == 2.0
    for i, fg_state in enumerate(state.floating_gates):
        np.testing.assert_array_equal(fg_state.P0, np.ones(3 + i))
        assert not np.shares_memory(fg_state.P0, result['state'].floating_gates[i].P0)
        assert result['rho_by_fg_C_m3'][i].shape == (3 + i,)
    assert isinstance(result['rho_C_m3'], np.ndarray if n_fgs == 1 else list)
    assert result['qfg_by_fg_C_m2'].shape == (n_fgs,)
    assert result['coupling_matrix_m2_F'].shape == (n_fgs, n_fgs)
    assert result['inter_fg_flux_by_link_m2_s'].shape == (n_fgs - 1,)
    assert result['transport_transmission_by_link'].shape == (n_fgs,)
    assert len(result['transport_link_ids']) == n_fgs
    assert result['field_profile'] is result['potential_profile']
    profile = result['field_profile']
    assert profile.potential_V.shape == profile.z_nm.shape
    assert profile.electric_field_V_m.shape == (len(profile.z_nm) - 1,)
    assert len(profile.segment_layer_names) == len(profile.z_nm) - 1
    for name in ('tprog_mean_by_fg', 'terase_mean_by_fg'):
        assert np.all((result[name] >= 0.0) & (result[name] <= 1.0))
    for name in ('optical_absorption_fraction_by_fg', 'optical_alpha_nc_by_fg_m_inv', 'optical_alpha_eff_by_fg_m_inv'):
        assert result[name].shape == (n_fgs,)
        assert np.all(np.isfinite(result[name])) if illuminated else np.all(np.isnan(result[name]))
    for name in ('absorbed_photon_flux_by_fg_m2_s', 'absorbed_photon_rate_per_nc_by_fg_s', 'photo_transition_rate_by_fg_s'):
        assert result[name].shape == (n_fgs,)
        assert np.all(result[name] > 0.0) if illuminated else np.all(result[name] == 0.0)
    assert result['absorbed_photon_flux_m2_s'] == pytest.approx(np.sum(result['absorbed_photon_flux_by_fg_m2_s']))


@pytest.mark.parametrize('n_fgs', [1, 3])
@pytest.mark.parametrize('illuminated', [False, True])
def test_sweep_history_axes_order_and_missing_profile_history(n_fgs, illuminated):
    sim = _simulator(n_fgs)
    voltage = np.array([2.0, -1.0, 0.0])
    light = LightSource.laser(wavelength_nm=1550.0, power_density_W_m2=1000.0) if illuminated else None
    result = sim.run_sweep(voltages_V=voltage, light_source=light)
    np.testing.assert_array_equal(result.voltages_V, voltage)
    for name in ('capacitance_F_m2','qfg_C_m2','vfb_V','veff_V','mean_occupation','field_mean_V_m','tprog_mean','terase_mean','delta_vfb_V','optical_absorption_fraction','absorbed_photon_flux_m2_s','photo_transition_rate_s'):
        assert getattr(result, name).shape == (3,), name
    for name in ('qfg_by_fg_C_m2','mean_occupation_by_fg','field_mean_by_fg_V_m','tprog_mean_by_fg','terase_mean_by_fg','delta_vfb_by_fg_V','electrostatic_local_field_by_fg_V_m','electrostatic_local_potential_by_fg_V','optical_absorption_fraction_by_fg','absorbed_photon_flux_by_fg_m2_s','absorbed_photon_rate_per_nc_by_fg_s','photo_transition_rate_by_fg_s','optical_alpha_nc_by_fg_m_inv','optical_alpha_eff_by_fg_m_inv'):
        assert getattr(result, name).shape == (3, n_fgs), name
    assert result.coupling_sensitivity_factors.shape == (n_fgs,)
    assert result.coupling_coefficients_m2_F.shape == (n_fgs,)
    assert result.inter_fg_flux_by_link_m2_s.shape == (3, n_fgs - 1)
    assert result.transport_transmission_by_link.shape == (3, n_fgs)
    assert result.field_profiles is None


def test_legacy_empty_sweep_and_input_voltage_aliasing_are_explicit():
    sim = _simulator(3)
    state = DeviceState.empty_for_device(sim.device)
    result = sim.run_sweep(voltages_V=[], state=state)
    assert result.qfg_by_fg_C_m2.shape == (0,)
    assert result.transport_transmission_by_link.shape == (0,)
    assert result.transport_link_ids is None
    assert result.final_state is not state
    voltage = np.array([0.0, 1.0])
    populated = sim.run_sweep(voltages_V=voltage)
    assert np.shares_memory(populated.voltages_V, voltage)
    populated.voltages_V[0] = 7.0
    assert voltage[0] == 7.0


def test_state_copy_is_independent_for_probabilities_but_shallow_for_metadata():
    state = DeviceState.empty_for_device(_simulator(1).device)
    state.metadata['nested'] = {'value': 0}
    state.floating_gates[0].metadata['nested'] = {'value': 0}
    copied = state.copy()
    copied.floating_gates[0].P0[:] = 0.0
    np.testing.assert_array_equal(state.floating_gates[0].P0, np.ones(3))
    assert copied.metadata is not state.metadata
    assert copied.floating_gates[0].metadata is not state.floating_gates[0].metadata
    copied.metadata['nested']['value'] = 1
    copied.floating_gates[0].metadata['nested']['value'] = 1
    assert state.metadata['nested']['value'] == 1
    assert state.floating_gates[0].metadata['nested']['value'] == 1


def test_frozen_profile_container_does_not_freeze_numpy_payload():
    sim = _simulator(1)
    profile = sim.relax_voltage(DeviceState.empty_for_device(sim.device), 0.0, dwell_time_s=0.0)['field_profile']
    with pytest.raises(FrozenInstanceError):
        profile.potential_V = np.zeros_like(profile.potential_V)
    profile.potential_V[0] = 7.0
    assert profile.potential_V[0] == 7.0


@pytest.mark.parametrize('n_fgs', [1, 3])
@pytest.mark.parametrize('duration', [0.0, 1e-8])
def test_retention_axes_actual_count_and_zero_charge_convention(n_fgs, duration):
    sim = _simulator(n_fgs)
    state = DeviceState.empty_for_device(sim.device)
    state.time_s = 10.0
    cfg = RetentionConfig(total_time_s=duration, initial_dt_s=1e-8, maximum_dt_s=1e-8, output_points=4)
    result = sim.simulate_retention(state=state, config=cfg)
    count = 1 if duration == 0.0 else 2
    assert result.time_s.shape == (count,)
    assert result.time_s[0] == 0.0
    assert result.qfg_by_fg_C_m2.shape == (count, n_fgs)
    assert result.inter_fg_flux_by_link_m2_s.shape == (count, n_fgs - 1)
    assert result.transport_transmission_by_link.shape == (count, n_fgs)
    assert result.charge_rate_C_m2_s.shape == (count,)
    assert result.quasi_equilibrium_time_s is None
    assert result.quasi_equilibrium_reached is False
    assert result.final_state.time_s == pytest.approx(10.0 + duration)
    assert state.time_s == 10.0
    np.testing.assert_array_equal(result.total_charge_retention_fraction, np.ones(count))
    np.testing.assert_array_equal(result.charge_loss_fraction, np.zeros(count))


def test_cv_branch_order_and_window_definition():
    result = _simulator(1).simulate_cv(vmin_V=-1.0, vmax_V=1.0, points=3)
    np.testing.assert_array_equal(result.forward.voltages_V, [-1.0, 0.0, 1.0])
    np.testing.assert_array_equal(result.backward.voltages_V, [1.0, 0.0, -1.0])
    assert result.memory_window_V == pytest.approx(result.vmid_backward_V - result.vmid_forward_V)
