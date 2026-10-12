# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Numerical study contracts, not experimental qualification."""
from copy import deepcopy
import pytest
from examples.phase_p5a_om2_numerical_study import run_reference,restore_study,summarize,specification,LABELS
from ncmemsim.om2_sweep import OM2SweepPrediction,_projection


@pytest.fixture(scope='module')
def study():
    return run_reference()


def test_temporal_refinement_keeps_physical_sequence(study):
    rows=study['results'];base=rows['dt']['experiment']['protocol']
    for key,factor in [('dt_half',2),('dt_quarter',4)]:
        p=rows[key]['experiment']['protocol']
        assert p['internal_dt_s']==base['internal_dt_s']/factor
        assert {k:v for k,v in p.items() if k!='internal_dt_s'}=={k:v for k,v in base.items() if k!='internal_dt_s'}
    summary=study['summary']
    assert all(x['within_example_thresholds'] for x in summary['temporal_refinement'])
    assert 0<summary['window_change_ratio']<1
    assert summary['rigorous_error_bound_established'] is False


def test_product_confounds_independent_parameters(study):
    s=study['summary'];pair=s['power_capture_product_check']
    assert pair['max_capacitance_change_F_m2']<1e-15
    assert pair['window_contrast_change_V']<1e-12
    assert s['independent_identifiability_established'] is False
    assert s['local_sensitivity']['sample_power']['central_secant_V_per_input_unit']==pytest.approx(
        10*s['local_sensitivity']['capture']['central_secant_V_per_input_unit'],rel=1e-9)


def test_zero_controls_and_reference_failures_are_retained(study):
    s=study['summary']
    assert all(x['dark_recovery'] for x in s['zero_photo_controls'].values())
    assert s['reference_selection'][-1]['observable_status']=='not_assessable'
    assert s['reference_selection'][-1]['contrast_V'] is None
    assert s['experimental_qualification'] is False and s['parameters_fitted'] is False
    assert len(study['results'])==13


def test_restore_never_calls_occupancy_optics_or_rng(study,monkeypatch):
    from ncmemsim.spectral_context import SpectralSimulator
    from ncmemsim.materials.optics.near_edge import GeSnNearEdgeReferenceModel
    import numpy as np
    def fail(*a,**k):raise AssertionError('unexpected dynamics/model replay')
    monkeypatch.setattr(SpectralSimulator,'relax_voltage',fail)
    monkeypatch.setattr(GeSnNearEdgeReferenceModel,'evaluate',fail)
    monkeypatch.setattr(np.random,'default_rng',fail)
    assert restore_study(deepcopy(study))==study


@pytest.mark.parametrize('change',['missing','extra','threshold','summary','spec_hash','source','case_name'])
def test_tampered_or_relabelled_study_rejected(study,change):
    raw=deepcopy(study)
    if change=='missing':raw['results'].pop('equal_product')
    if change=='extra':raw['extra']=None
    if change=='threshold':raw['specification']['numerical_thresholds']['max_window_step_change_V']=1
    if change=='summary':raw['summary']['experimental_qualification']=True
    if change=='spec_hash':raw['specification_hash']='0'*64
    if change=='source':raw['results']['power_high']['experiment']['device_photo']['illumination']['uniform_spot_area_m2']*=2
    if change=='case_name':raw['results']['capture_low'],raw['results']['capture_high']=raw['results']['capture_high'],raw['results']['capture_low']
    with pytest.raises(ValueError):restore_study(raw)


def test_failed_case_does_not_become_passed_refinement(study):
    raw=deepcopy(study)
    failed=raw['results']['dt_half']
    failed['illuminated_writing']=failed['illuminated_writing'][:2]
    failed['matched_dark']=[]
    failed['failure']={'run':'illuminated_writing','step_index':2,'exception_type':'builtins.RuntimeError','message':'numerical diagnostic failure'}
    failed['summary']=_projection(failed)
    results={k:OM2SweepPrediction.from_dict(raw['results'][k]) for k in LABELS}
    raw['summary']=summarize(results,specification())
    out=restore_study(raw)
    assert out['summary']['case_status']['dt_half']=='sequence_failed'
    assert all(not row['within_example_thresholds'] for row in out['summary']['temporal_refinement'])
    assert out['summary']['window_change_ratio'] is None
