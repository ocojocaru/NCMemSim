# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Independent equations, open-reservoir conservation and M3 numerical limits."""
from copy import deepcopy
from dataclasses import replace
import math
import numpy as np
import pytest
from examples import phase_m3_si_temperature_reference as ref
from ncmemsim.constants import BOLTZMANN_J_K, ELEMENTARY_CHARGE_C
from ncmemsim.hashing import canonical_hash
from ncmemsim.temperature_context import ResolvedThermalContext, SemiconductorThermalMode as Mode


@pytest.fixture(scope='module')
def evidence():
    return ref.run_reference()


def test_complete_scope_and_recorded_assumptions(evidence):
    assert evidence['case_counts']=={'attempted':12,'completed':12,'failed':0}
    assert len(evidence['disabled_controls'])==len(evidence['original_simulator_controls'])==3
    assert 'No experimental calibration' in evidence['scope']
    assert 'Arrhenius' in evidence['scope']
    assert evidence['parameter_status']['geometry_barriers_kinetics']=='assumed'
    assert evidence['parameter_status']['thermal_coefficients']=='literature_fitted'
    assert '0.5' in evidence['charge_convention']
    assert evidence['reference_hash']==canonical_hash({k:v for k,v in evidence.items() if k!='reference_hash'})


def test_repeated_reference_is_deterministic(evidence):
    assert ref.run_reference()==evidence


@pytest.mark.parametrize('temperature',ref.TEMPERATURES_K)
def test_disabled_and_original_identity(evidence,temperature):
    index=ref.TEMPERATURES_K.index(temperature)
    legacy=next(c for c in evidence['cases'] if c['temperature_K']==temperature and c['mode']=='legacy')
    assert legacy['observations']==evidence['disabled_controls'][index]['observations']
    assert legacy['observations']==evidence['original_simulator_controls'][index]['observations']


def test_exact_reference_identity_across_four_modes(evidence):
    rows=[r['observations'] for r in evidence['cases'] if r['temperature_K']==300]
    assert rows[1:]==[rows[0]]*3


@pytest.mark.parametrize('index',range(12))
def test_thermal_values_and_flatband_independent_equations(evidence,index):
    c=evidence['cases'][index];t=c['temperature_K'];o=c['observations'];s=o['semiconductor']
    expected_gap=1.12-7.021e-4*(t*t/(t+1108)-300*300/1408)
    kb=BOLTZMANN_J_K/ELEMENTARY_CHARGE_C
    expected_ni=1e16*(t/300)**1.5*math.exp(-expected_gap/(2*kb*t)+1.12/(2*kb*300))
    assert s['bandgap_eV']==pytest.approx(expected_gap if c['mode'] in ('gap_only','coupled') else 1.12,rel=1e-14)
    assert s['intrinsic_density_m3']==pytest.approx(expected_ni if c['mode'] in ('density_only','coupled') else 1e16,rel=1e-13)
    phi=kb*t*math.log(1e21/s['intrinsic_density_m3'])
    assert o['fermi_potential_V']==pytest.approx(phi,rel=1e-14)
    assert o['flatband_zero_V']==pytest.approx(4.8-(4.05+.5*s['bandgap_eV']+phi),abs=1e-15)
    restored=ResolvedThermalContext.from_dict(c['resolution'])
    assert restored.context_hash==c['resolution_hash']
    assert restored.device.temperature_K==t


@pytest.mark.parametrize('temperature',[250.,350.])
def test_flatband_control_decomposition_and_nontrivial_program_response(evidence,temperature):
    rows={r['mode']:r['observations'] for r in evidence['cases'] if r['temperature_K']==temperature}
    baseline=rows['legacy']['flatband_zero_V']
    gap=rows['gap_only']['flatband_zero_V']-baseline
    density=rows['density_only']['flatband_zero_V']-baseline
    assert rows['coupled']['flatband_zero_V']-baseline==pytest.approx(gap+density,abs=2e-15)
    assert abs(rows['coupled']['program']['delta_vfb_V']-rows['legacy']['program']['delta_vfb_V'])>1e-6
    assert gap>0 and density>0 if temperature>300 else gap<0 and density<0


@pytest.mark.parametrize('index',range(12))
def test_convergence_probability_and_substrate_charge_budget(evidence,index):
    c=evidence['cases'][index]
    for stage in ('program','retention'):
        fine=c['timestep_audit']['finest_pair_max_probability_error'][stage]
        coarse=c['timestep_audit']['coarser_pair_max_probability_error'][stage]
        assert fine<ref.OCCUPATION_ATOL
        assert fine<coarse
    assert c['uniform_retention_vs_solver_max_probability_error']<ref.OCCUPATION_ATOL
    for stage in c['charge_budget']:
        assert stage['charge_budget_relative_residual']<ref.CHARGE_BUDGET_RTOL
        assert stage['max_probability_mass_error']<ref.PROBABILITY_ATOL
        assert stage['minimum_probability']>=0
        assert stage['final_qfg_C_m2']-stage['initial_qfg_C_m2']==pytest.approx(
            stage['integrated_substrate_charge_C_m2'],abs=1e-15)
    assert c['charge_budget'][0]['integrated_substrate_charge_C_m2']>0
    assert c['charge_budget'][1]['integrated_substrate_charge_C_m2']<0
    np.testing.assert_allclose(c['charge_budget'][0]['final']['probabilities'],
        c['observations']['program']['final']['probabilities'],rtol=0,atol=1e-13)


@pytest.mark.parametrize('index',range(12))
def test_nondestructive_read_and_charge_flatband_relation(evidence,index):
    o=evidence['cases'][index]['observations']
    np.testing.assert_allclose(o['program']['read']['probabilities'],o['program']['final']['probabilities'],rtol=0,atol=1e-15)
    assert o['program']['read']['time_s']==o['program']['final']['time_s']
    assert o['program']['read_max_probability_change']<ref.PROBABILITY_ATOL
    assert o['program']['delta_vfb_V']==pytest.approx(-o['program']['qfg_C_m2']/o['cox_F_m2'],abs=1e-15)
    np.testing.assert_allclose(o['retention']['delta_vfb_V'],-np.array(o['retention']['qfg_C_m2'])/o['cox_F_m2'],rtol=1e-13,atol=1e-15)
    assert o['retention']['time_s'][0]==0 and o['retention']['time_s'][-1]==ref.RETENTION_TIME_S
    assert o['retention']['qfg_C_m2'][0]==pytest.approx(o['program']['qfg_C_m2'],rel=5e-15,abs=1e-18)
    assert 0<o['retention']['charge_retention_fraction'][-1]<1
    assert o['retention_config']['gate_voltage_V']==0


def test_numerical_scope_does_not_rewrite_material_barriers(evidence):
    states=[ResolvedThermalContext.from_dict(r['resolution']) for r in evidence['cases']]
    nominal=ref.build_nominal()[0].floating_gates()[0].nc_material
    assert all(r.device.floating_gates()[0].nc_material==nominal for r in states)
    assert len({r.context.nominal_hash for r in states})==1
    assert len({r.context_hash for r in states})==12
    for t in ref.TEMPERATURES_K:
        assert len({r['observations']['gamma_c'] for r in evidence['cases'] if r['temperature_K']==t})==1


@pytest.mark.parametrize('target',['missing_case','duplicate_case','timestep','budget','probability','clipping','nonfinite'])
def test_failed_evidence_is_rejected(evidence,target):
    altered=deepcopy(evidence)
    if target=='missing_case': altered['cases'].pop()
    if target=='duplicate_case': altered['cases'][1]=deepcopy(altered['cases'][0])
    if target=='timestep': altered['cases'][0]['timestep_audit']['finest_pair_max_probability_error']['program']=.1
    if target=='budget': altered['cases'][0]['charge_budget'][0]['charge_budget_relative_residual']=.1
    if target=='probability': altered['cases'][0]['charge_budget'][0]['max_probability_mass_error']=.1
    if target=='clipping': altered['cases'][0]['charge_budget'][0]['minimum_unclipped_euler_probability']=-.1
    if target=='nonfinite': altered['cases'][0]['observations']['fermi_potential_V']=float('nan')
    with pytest.raises(ValueError): ref.validate_reference(altered)


def test_unsafe_euler_step_cannot_hide_behind_normalization():
    audit=ref.charge_budget_audit(ref.build_context().resolve(),steps=1)[0]
    assert audit['max_probability_mass_error']<ref.PROBABILITY_ATOL
    assert audit['minimum_unclipped_euler_probability']<0
    assert audit['charge_budget_relative_residual']>ref.CHARGE_BUDGET_RTOL


@pytest.mark.parametrize('bad',[0,-1,True,1.5,'128'])
def test_bad_timestep_count(bad):
    with pytest.raises(ValueError): ref.evaluate_case(ref.build_context(),300,bad)


@pytest.mark.parametrize('temperature',[249,351,float('nan'),True])
def test_invalid_temperature_fails_before_running(temperature):
    with pytest.raises(ValueError): ref.evaluate_case(ref.build_context(),temperature)


@pytest.mark.parametrize('index',range(12))
def test_thermal_program_contrast_converges_separately(evidence,index):
    c=evidence['cases'][index]; audit=c['program_thermal_contrast_audit']
    assert audit['finest_pair_contrast_error_V']<ref.PROGRAM_CONTRAST_ATOL_V
    if c['temperature_K']!=300 and c['mode']!='legacy':
        assert abs(audit['contrast_at_each_step_count_V'][-1])>10*audit['finest_pair_contrast_error_V']
