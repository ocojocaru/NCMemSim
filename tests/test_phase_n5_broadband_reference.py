# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import numpy as np
import pytest
from examples import phase_n5_broadband_reference as ref
from ncmemsim.hashing import canonical_hash
from ncmemsim.spectral_context import SpectralSimulationContext


@pytest.fixture(scope='module')
def evidence():return ref.run_reference()


def test_complete_matrix_and_failure_denominators(evidence):
    assert evidence['case_counts']=={'attempted':11,'completed':9,'failed':2}
    assert len(evidence['cases'])==9 and len(evidence['controls'])==3
    assert {r['case'] for r in evidence['failures']}=={'unsupported_domain','incomplete_path'}
    assert all(r['error_type']=='ValueError' and r['message'] for r in evidence['failures'])
    assert set(evidence['assumptions'].values())=={'ASSUMED'}
    assert 'No measured spectrum' in evidence['scope']
    raw=deepcopy(evidence);digest=raw.pop('reference_hash');assert canonical_hash(raw)==digest


@pytest.mark.parametrize('index',range(9))
def test_equal_power_sequential_budgets_and_refinement(evidence,index):
    case=evidence['cases'][index];context=SpectralSimulationContext.from_dict(case['context'])
    result=context.optical_result.projection
    assert context.optical_result.source.in_band_irradiance_W_m2==pytest.approx(ref.POWER_W_M2)
    previous=ref.POWER_W_M2
    for row in result['layers']:
        summary=row['absorption']['summary']
        assert summary['incident_irradiance_W_m2']==pytest.approx(previous)
        assert summary['absorbed_irradiance_W_m2']+summary['transmitted_irradiance_W_m2']==pytest.approx(previous,rel=1e-12)
        assert summary['absorbed_photon_flux_m2_s']+summary['transmitted_photon_flux_m2_s']==pytest.approx(summary['incident_photon_flux_m2_s'],rel=1e-12)
        previous=summary['transmitted_irradiance_W_m2']
    total=result['summary']
    assert total['absorbed_irradiance_W_m2']+total['transmitted_irradiance_W_m2']==pytest.approx(ref.POWER_W_M2,rel=1e-12)
    a,b=case['programs'][-2:]
    assert np.max(abs(np.asarray(a['light']['probabilities'])-np.asarray(b['light']['probabilities'])))<ref.PROBABILITY_ATOL
    assert abs(a['photo_contrast_V']-b['photo_contrast_V'])<ref.READ_VFB_ATOL_V
    expected_flux=[next(r for r in result['layers'] if r['layer_name']==fg.name)['nc_absorbed_photon_flux_m2_s'] for fg in context.resolution.device.floating_gates()]
    for row in case['programs']:
        np.testing.assert_allclose(row['light']['absorbed_photon_flux_by_fg_m2_s'],expected_flux,rtol=1e-14)
        probabilities=np.asarray(row['light']['probabilities'])
        assert probabilities.shape==(case['n_fgs'],3,3) and probabilities.min()>=0
        np.testing.assert_allclose(probabilities.sum(axis=2),1,rtol=0,atol=1e-12)


def test_fixed_source_thermal_control_and_passive_loss(evidence):
    a,b=evidence['thermal_source_controls']
    assert a['source']==b['source'] and a['device_temperature_K']==300 and b['device_temperature_K']==350
    assert a['optical_summary']['fg_absorbed_photon_flux_m2_s']!=b['optical_summary']['fg_absorbed_photon_flux_m2_s']
    for row in evidence['controls']:
        assert row['zero_capture']['probabilities']==row['dark']['probabilities']==row['disabled']['probabilities']
        assert row['passive_loss_summary']['passive_absorbed_photon_flux_m2_s']>0
        assert row['passive_loss_summary']['fg_absorbed_photon_flux_m2_s']<row['transparent_summary']['fg_absorbed_photon_flux_m2_s']


def test_equal_power_is_not_equal_photon_flux(evidence):
    rows=[c for c in evidence['cases'] if c['n_fgs']==1]
    photons=[c['spectral_grid_audit'][-1]['summary']['incident_photon_flux_m2_s'] for c in rows]
    assert len(set(photons))==3


@pytest.mark.parametrize('fault',['hash','missing_case','context','refinement','failure','source_temperature'])
def test_reference_rejects_incomplete_or_inconsistent_evidence(evidence,fault):
    raw=deepcopy(evidence)
    if fault=='hash':raw['scope']='changed'
    elif fault=='missing_case':raw['cases'].pop()
    elif fault=='context':raw['cases'][0]['context']['optical_result']['projection']['summary']['absorbed_irradiance_W_m2']+=1
    elif fault=='refinement':raw['cases'][0]['programs'][-1]['photo_contrast_V']+=1
    elif fault=='failure':raw['failures'].pop()
    else:raw['thermal_source_controls'][1]['source']['enabled']=False
    if fault!='hash':
        raw.pop('reference_hash');raw['reference_hash']=canonical_hash(raw)
    with pytest.raises(ValueError):ref.validate_reference(raw)
