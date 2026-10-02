# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Independent optical equations, photon accounting and controlled illumination."""
from copy import deepcopy
import math
import numpy as np
import pytest
from examples import phase_m4_ge_temperature_reference as ref
from ncmemsim.constants import BOLTZMANN_J_K, ELEMENTARY_CHARGE_C
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.optics.models import CompositeGeSnAbsorptionModel
from ncmemsim.photo import nanocrystal_number_density_m3
from ncmemsim.temperature_context import OpticalThermalMode as Mode, ResolvedThermalContext


@pytest.fixture(scope='module')
def evidence():
    return ref.run_reference()


def test_complete_conditional_evidence(evidence):
    assert evidence['case_counts']=={'attempted':12,'completed':12,'failed':0}
    assert evidence['statuses']['capture_efficiency']=='ASSUMED'
    assert 'No experimental thermal absorption calibration' in evidence['scope']
    raw=deepcopy(evidence); digest=raw.pop('reference_hash')
    assert digest==canonical_hash(raw)
    assert len(evidence['controls'])==3


@pytest.mark.parametrize('index',range(12))
def test_independent_optical_equations_and_photon_budget(evidence,index):
    case=evidence['cases'][index]
    mode=Mode(case['mode']); t=case['temperature_K']
    resolution=ResolvedThermalContext.from_dict(case['resolved_context'])
    assert resolution.context_hash==case['resolution_hash']
    binding=resolution.context.optical_bindings[0]
    g=binding.gamma_profile.evaluate(t) if mode in (Mode.GAPS_ONLY,Mode.COUPLED) else .7985
    l=binding.l_profile.evaluate(t) if mode in (Mode.GAPS_ONLY,Mode.COUPLED) else .664
    phonon_t=t if mode in (Mode.PHONONS_ONLY,Mode.COUPLED) else 300
    n=1/math.expm1(.027*ELEMENTARY_CHARGE_C/(BOLTZMANN_J_K*phonon_t))
    for row in case['optical']:
        e=row['photon_energy_eV']
        direct=1e7*math.sqrt(max(e-g,0))/e
        indirect=1e6*(n*max(e-l+.027,0)**2+(n+1)*max(e-l-.027,0)**2)
        tail=1e5*math.exp((e-g)/.012) if e<g else 0
        assert row['direct_gap_eV']==g
        assert row['indirect_gap_eV']==l
        assert row['alpha_direct_m_inv']==pytest.approx(direct,rel=2e-14)
        assert row['alpha_indirect_m_inv']==pytest.approx(indirect,rel=2e-14)
        assert row['alpha_urbach_m_inv']==pytest.approx(tail,rel=2e-14)
        assert row['nc_absorption_coefficient_m_inv']==pytest.approx(direct+indirect+tail)
        fraction=-math.expm1(-.2*(direct+indirect+tail)*6e-9)
        assert row['absorption_fraction']==pytest.approx(fraction,rel=1e-12)
        incident=row['incident_photon_flux_m2_s']
        assert row['absorbed_photon_flux_m2_s']==pytest.approx(incident*fraction)
        assert row['absorbed_photon_flux_m2_s']+row['transmitted_photon_flux_m2_s']==pytest.approx(incident,rel=1e-14)
        assert row['average_generation_rate_m3_s']==pytest.approx(incident*fraction/6e-9)
    for program in case['programs']:
        optical=next(r for r in case['optical'] if r['wavelength_nm']==program['wavelength_nm'])
        density=nanocrystal_number_density_m3(resolution.device.get_layer('FG1').nc_diameter_nm,.2)
        expected=ref.CAPTURE_EFFICIENCY*optical['average_generation_rate_m3_s']/density
        for run in program['runs']:
            assert run['photo_transition_rate_s']==pytest.approx(expected,rel=1e-14)
            assert run['absorbed_photon_flux_m2_s']==optical['absorbed_photon_flux_m2_s']
            assert run['photo_contrast_V']<0
            assert run['read_max_probability_change']<1e-12
            assert run['minimum_probability']>=0
        assert program['finest_probability_error']<ref.PROBABILITY_ATOL
        assert program['finest_photo_contrast_error_V']<ref.CONTRAST_ATOL_V


def test_reference_temperature_recovers_legacy_optical_points(evidence):
    cases=[c for c in evidence['cases'] if c['temperature_K']==300]
    for case in cases:
        assert case['optical']==cases[0]['optical']
        assert case['programs']==cases[0]['programs']
    resolution=ref.build_context().resolve(temperature_K=300)
    for w in ref.WAVELENGTHS_NM:
        assert resolution.optical_model('FG1').evaluate(resolution.device.get_layer('FG1').nc_material,w)==CompositeGeSnAbsorptionModel().evaluate(resolution.device.get_layer('FG1').nc_material,w)


@pytest.mark.parametrize('t',[250.,350.])
def test_controls_isolate_phonons_and_gaps_and_detect_response(evidence,t):
    cases={c['mode']:c for c in evidence['cases'] if c['temperature_K']==t}
    for i in range(len(ref.WAVELENGTHS_NM)):
        legacy=cases['legacy']['optical'][i]
        phonons=cases['phonons_only']['optical'][i]
        gaps=cases['gaps_only']['optical'][i]
        coupled=cases['coupled']['optical'][i]
        assert legacy['alpha_direct_m_inv']==phonons['alpha_direct_m_inv']
        assert legacy['alpha_urbach_m_inv']==phonons['alpha_urbach_m_inv']
        assert gaps['alpha_direct_m_inv']==coupled['alpha_direct_m_inv']
        assert gaps['alpha_urbach_m_inv']==coupled['alpha_urbach_m_inv']
    assert any(a['alpha_indirect_m_inv']!=b['alpha_indirect_m_inv'] for a,b in zip(cases['legacy']['optical'],cases['phonons_only']['optical']))
    assert any(a['direct_gap_eV']!=b['direct_gap_eV'] for a,b in zip(cases['legacy']['optical'],cases['gaps_only']['optical']))
    assert any(a['runs'][-1]['photo_contrast_V']!=b['runs'][-1]['photo_contrast_V'] for a,b in zip(cases['legacy']['programs'],cases['coupled']['programs']))


def test_legacy_disabled_and_zero_capture_controls(evidence):
    for control in evidence['controls']:
        assert control['disabled']==control['original']==control['legacy']
        assert control['zero_capture']['photo_contrast_V']==pytest.approx(0,abs=1e-14)


def test_room_temperature_gesn_limits_are_separate(evidence):
    rows=evidence['near_edge_300K_reference']
    assert all(r['temperature_K']==300 for r in rows)
    assert rows[0]['domain_status']==rows[1]['domain_status']==rows[2]['domain_status']
    assert rows[3]['domain_status']!=rows[0]['domain_status']
    assert rows[4]['domain_status']!=rows[0]['domain_status']
    assert all(r['context']['optical_bindings'][0]['gamma_profile']['sn_fraction']==0 for r in evidence['cases'])


@pytest.mark.parametrize('failure',['missing','duplicate','photons','actual_photons','refinement','actual_refinement','read','controls','nonfinite'])
def test_failed_audits_reject_export(evidence,failure):
    bad=deepcopy(evidence)
    if failure=='missing': bad['cases'].pop()
    elif failure=='duplicate': bad['cases'][1]=deepcopy(bad['cases'][0])
    elif failure=='photons': bad['cases'][0]['optical'][0]['photon_budget_relative_error']=.1
    elif failure=='actual_photons': bad['cases'][0]['optical'][0]['transmitted_photon_flux_m2_s']=0
    elif failure=='actual_refinement': bad['cases'][0]['programs'][0]['runs'][-1]['probabilities'][0][0]=.9
    elif failure=='controls': bad['controls'].pop()
    elif failure=='refinement': bad['cases'][0]['programs'][0]['finest_probability_error']=.1
    elif failure=='read': bad['cases'][0]['programs'][0]['runs'][0]['read_max_probability_change']=.1
    else: bad['cases'][0]['optical'][0]['absorption_fraction']=float('nan')
    with pytest.raises(ValueError): ref.validate_reference(bad)


@pytest.mark.parametrize('t',[249.,351.])
def test_no_out_of_domain_temperature(t):
    with pytest.raises(ValueError): ref.build_context().resolve(temperature_K=t)


def test_repeated_reference_is_deterministic(evidence):
    assert ref.run_reference()==evidence
