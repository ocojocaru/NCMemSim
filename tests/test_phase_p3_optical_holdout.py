# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""P3 mechanical holdout fixtures; no real experimental qualification."""
from copy import deepcopy
from dataclasses import replace,FrozenInstanceError
import json
import numpy as np
import pytest
from examples.phase_p3_optical_holdout_reference import setup,validation_package,run_reference,restore_reference
from ncmemsim.independent_data import IndependentStudySplit,ExperimentalDataPackage
from ncmemsim.independent_optical_validation import OpticalHoldoutPlan,OpticalHoldoutCriteria,OpticalHoldoutEvaluation,evaluate_optical_holdout,review_optical_holdout_admission
from ncmemsim.independent_optical_fit import fit_optical_training,OpticalTrainingContext,OpticalTrainingFitResult
from ncmemsim.fitting import LeastSquaresConfig
from ncmemsim.hashing import canonical_hash
from ncmemsim.workflows.evidence import DatasetEvidence


@pytest.fixture(scope='module')
def sources():
    plan,fit=setup();holdout=validation_package()
    split=IndependentStudySplit('synthetic unit split',(plan.training_context.data_package,),(holdout,),'unit reviewer','synthetic observations only')
    return plan,fit,split


@pytest.fixture(scope='module')
def evaluation(sources):return evaluate_optical_holdout(*sources)


def test_good_diagnostic_is_not_independent_calibration(evaluation):
    s=evaluation.summary
    assert s['status']=='diagnostic_validation_passed' and s['criteria_passed'] is True
    assert s['training_parameters_unchanged'] is True and s['parameters_promoted'] is False
    assert s['admission']['independent_experiment_certified'] is False
    assert s['admission']['p1_split_summary']['status']=='not_admissible'
    assert s['evaluated_count']==1
    assert OpticalHoldoutEvaluation.from_json(evaluation.to_json())==evaluation


def test_shifted_holdout_keeps_negative_without_parameter_change(sources):
    plan,fit,split=sources;before=fit.to_json()
    result=evaluate_optical_holdout(plan,fit,replace(split,validation=(validation_package('shifted',1.25),)))
    assert result.summary['status']=='validation_failed'
    assert 'rmse_m_inv' in result.summary['validation_outcomes'][0]['failed_criteria']
    assert fit.to_json()==before
    row=result.to_dict()['validation_records'][0]
    assert row['parameters_used']==fit.to_dict()['numerical_result']['fitted_parameters']


def test_no_optimizer_is_called_during_evaluation(sources,monkeypatch):
    import ncmemsim.independent_optical_fit as fitting
    def forbidden(*args,**kwargs):raise AssertionError('holdout must not optimize')
    monkeypatch.setattr(fitting,'run_least_squares_fit',forbidden)
    assert evaluate_optical_holdout(*sources).summary['criteria_passed'] is True


@pytest.mark.parametrize('field',['observation_groups','observation_ids','observation_artifact_sha256'])
def test_overlap_blocks_model_evaluation(sources,monkeypatch,field):
    import ncmemsim.independent_optical_validation as module
    plan,fit,split=sources;a=split.training[0];b=split.validation[0]
    # The vector lengths differ for row IDs; use one shared ID in a valid six-row list.
    value=(a.lineage.observation_ids[0],)+b.lineage.observation_ids[1:] if field=='observation_ids' else getattr(a.lineage,field)
    b=replace(b,lineage=replace(b.lineage,**{field:value}))
    def forbidden(*args,**kwargs):raise AssertionError('blocked source must not be evaluated')
    monkeypatch.setattr(module,'predict_optical_training',forbidden)
    result=module.evaluate_optical_holdout(plan,fit,replace(split,validation=(b,)))
    assert result.summary['status']=='not_admissible'
    assert result.to_dict()['validation_records']==[]
    assert result.summary['evaluated_count']==0


def test_training_source_and_plan_mismatch_rejected(sources):
    plan,fit,split=sources
    with pytest.raises(ValueError):evaluate_optical_holdout(plan,fit,replace(split,training=split.validation))
    other_context=replace(plan.training_context,specification=replace(plan.training_context.specification,name='different specification'))
    with pytest.raises(ValueError):evaluate_optical_holdout(replace(plan,training_context=other_context),fit,split)


def test_failed_training_does_not_invent_holdout_metrics(sources):
    plan,_,split=sources
    ctx=replace(plan.training_context,specification=replace(plan.training_context.specification,solver_config=LeastSquaresConfig(max_nfev=1)))
    new_plan=replace(plan,training_context=ctx);fit=fit_optical_training(ctx)
    result=evaluate_optical_holdout(new_plan,fit,split)
    assert result.summary['status']=='not_assessable'
    assert 'training_fit_not_successful' in result.summary['admission']['acquisition_gaps']
    assert result.to_dict()['validation_records']==[]


def test_incompatible_holdout_is_unassessed_and_retained(sources):
    plan,fit,split=sources;package=split.validation[0];raw=package.dataset_evidence.to_dict()
    raw['dataset']['wavelength_nm'][0]=1499.;raw['dataset_hash']=canonical_hash(raw['dataset']);raw.pop('evidence_hash')
    package=replace(package,dataset_evidence=DatasetEvidence(json.dumps(raw)))
    result=evaluate_optical_holdout(plan,fit,replace(split,validation=(package,)))
    assert result.summary['status']=='not_assessable'
    assert result.summary['validation_outcomes'][0]['metrics'] is None
    assert result.to_dict()['validation_records'][0]['predicted_absorption_m_inv'] is None
    assert OpticalHoldoutEvaluation.from_json(result.to_json())==result


def test_prediction_exception_is_retained(sources,monkeypatch):
    import ncmemsim.independent_optical_validation as module
    def forbidden(*args,**kwargs):raise RuntimeError('injected holdout evaluation failure')
    monkeypatch.setattr(module,'predict_optical_training',forbidden)
    result=module.evaluate_optical_holdout(*sources)
    assert result.summary['status']=='evaluation_failed'
    assert result.to_dict()['validation_records'][0]['failure']['message']=='injected holdout evaluation failure'
    assert result.summary['criteria_passed'] is None
    assert OpticalHoldoutEvaluation.from_json(result.to_json())==result


def test_all_packages_must_pass_not_just_pooled_rmse(sources):
    plan,fit,split=sources
    result=evaluate_optical_holdout(plan,fit,replace(split,validation=(split.validation[0],validation_package('bad-two',1.25))))
    assert result.summary['evaluated_count']==2
    assert result.summary['status']=='validation_failed'
    assert not result.summary['validation_outcomes'][0]['failed_criteria']
    assert result.summary['validation_outcomes'][1]['failed_criteria']


def test_covariance_and_marginal_metrics_have_explicit_meaning(sources):
    plan,fit,split=sources;p=split.validation[0];n=p.summary['n_observations']
    covariance=1e6*(.8*np.eye(n)+.2*np.ones((n,n)))
    p=replace(p,uncertainty=replace(p.uncertainty,correlation_policy='covariance_supplied',covariance=tuple(tuple(float(x) for x in row) for row in covariance)))
    result=evaluate_optical_holdout(plan,fit,replace(split,validation=(p,)))
    o=result.summary['validation_outcomes'][0];r=np.asarray(o['raw_residuals_m_inv'])
    assert o['metrics']['whitened_rmse']==pytest.approx(np.sqrt(float(r@np.linalg.solve(covariance,r))/n),abs=1e-15)
    assert o['metrics']['max_abs_marginal_standardized_residual']==pytest.approx(float(np.max(abs(r)/1000.)))


@pytest.mark.parametrize('kwargs',[{'max_rmse_m_inv':-1},{'max_whitened_rmse':float('inf')},{'max_whitened_rmse':True},{'min_observations':True},{'min_observations':0},{'require_local_identifiability':'yes'}])
def test_invalid_criteria_rejected(kwargs):
    with pytest.raises(ValueError):replace(OpticalHoldoutCriteria(1000.,1.,3.,4),**kwargs)


def test_predeclared_threshold_failure_is_not_relaxed(sources):
    plan,fit,split=sources
    result=evaluate_optical_holdout(replace(plan,criteria=replace(plan.criteria,min_observations=100)),fit,split)
    assert result.summary['status']=='validation_failed'
    assert 'minimum_observations' in result.summary['validation_outcomes'][0]['failed_criteria']
    assert result.to_dict()['plan']['criteria']['min_observations']==100


def test_measured_declaration_mode_does_not_authenticate_or_calibrate():
    # Invented complete measured declarations test mechanics only.
    from examples.phase_p2_optical_training_reference import build_context
    ctx=build_context()
    def declared(package,prefix):
        data=package.dataset_evidence.to_dict();data['origin']='measured';data.pop('evidence_hash')
        lineage=replace(package.lineage,data_kind='model_derived',specimen_id=prefix+'/specimen',acquisition_id=prefix+'/acquisition',acquisition_roots=(prefix+'/root',),redistribution_terms='test fixture only',temperature_standard_uncertainty_K=1.,specimen_characterization='invented fixture',measurement_geometry='invented fixture',instrument_and_calibration='not a real instrument')
        return replace(package,dataset_evidence=DatasetEvidence(json.dumps(data)),lineage=lineage,reviewer='unit-test reviewer',review_notes='invented declarations; no real experiment')
    train=declared(ctx.data_package,'train');val=declared(validation_package(),'validation')
    ctx=replace(ctx,data_package=train,mode='measured_training')
    plan=OpticalHoldoutPlan('unit plan',ctx,OpticalHoldoutCriteria(1000.,1.,3.,4),'independent_measured','unit-only declaration')
    fit=fit_optical_training(ctx);split=IndependentStudySplit('unit independent declarations',(train,),(val,),'unit reviewer','not real data')
    result=evaluate_optical_holdout(plan,fit,split)
    assert result.summary['status']=='declared_independent_validation_passed'
    assert result.summary['parameters_promoted'] is False
    assert result.summary['admission']['independent_experiment_certified'] is False


def test_real_tran_limitation_and_synthetic_reference_unchanged():
    raw=run_reference();assert restore_reference(raw)==raw
    assert raw['legacy_admission']['status']=='not_admissible'
    assert raw['legacy_admission']['model_evaluated'] is False
    assert raw['legacy_admission']['parameters_promoted'] is False
    assert [item['summary']['status'] for item in raw['evaluations']]==['diagnostic_validation_passed','validation_failed']


@pytest.mark.parametrize('fault',['parameters','summary','prediction','metrics','source','plan','extra','missing_record'])
def test_archive_tampering_rejected(evaluation,fault):
    raw=deepcopy(evaluation.to_dict())
    if fault=='parameters':raw['validation_records'][0]['parameters_used']['direct_prefactor_A']*=1.01
    elif fault=='summary':raw['summary']['parameters_promoted']=True
    elif fault=='prediction':raw['validation_records'][0]['predicted_absorption_m_inv'][0]*=1.01
    elif fault=='metrics':raw['summary']['validation_outcomes'][0]['metrics']['rmse_m_inv']+=1
    elif fault=='source':raw['split_hash']='0'*64
    elif fault=='plan':raw['plan']['criteria']['max_whitened_rmse']*=2
    elif fault=='extra':raw['unreviewed']=True
    else:raw['validation_records']=[]
    with pytest.raises(ValueError):OpticalHoldoutEvaluation.from_dict(raw)


def test_restore_without_optimizer_optical_or_rng_replay(evaluation,monkeypatch):
    import ncmemsim.independent_optical_validation as validation
    import ncmemsim.independent_optical_fit as fitting
    def forbidden(*args,**kwargs):raise AssertionError('no replay')
    monkeypatch.setattr(validation,'predict_optical_training',forbidden)
    monkeypatch.setattr(fitting,'predict_gesn_near_edge_absorption_m_inv',forbidden)
    monkeypatch.setattr(fitting,'run_least_squares_fit',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    assert OpticalHoldoutEvaluation.from_json(evaluation.to_json())==evaluation


def test_strict_json_and_frozen_owned_plan(sources,evaluation):
    with pytest.raises(ValueError):OpticalHoldoutEvaluation.from_json(evaluation.to_json().replace('{','{"summary":null,',1))
    with pytest.raises(ValueError):OpticalHoldoutEvaluation.from_json(evaluation.to_json().replace('300.0','NaN',1))
    plan,_,_=sources
    with pytest.raises(FrozenInstanceError):plan.mode='independent_measured'
    raw=plan.to_dict();raw['criteria']['max_rmse_m_inv']=0
    assert plan.criteria.max_rmse_m_inv==1000.



def test_reference_does_not_drop_or_relabel_outcomes():
    raw=run_reference();raw['evaluations'].pop();raw['reference_hash']=canonical_hash({k:v for k,v in raw.items() if k!='reference_hash'})
    with pytest.raises(ValueError,match='complete'):restore_reference(raw)


def test_synthetic_mode_does_not_bypass_shared_systematic_review(sources):
    plan,fit,split=sources
    train=replace(split.training[0],lineage=replace(split.training[0].lineage,shared_systematic_ids=('shared-error',)))
    valid=replace(split.validation[0],lineage=replace(split.validation[0].lineage,shared_systematic_ids=('shared-error',)))
    ctx=replace(plan.training_context,data_package=train);plan=replace(plan,training_context=ctx);fit=fit_optical_training(ctx)
    split=replace(split,training=(train,),validation=(valid,))
    result=evaluate_optical_holdout(plan,fit,split)
    assert result.summary['status']=='not_assessable'
    assert 'shared_systematics_review_missing' in result.summary['admission']['acquisition_gaps']


def test_source_record_cannot_invent_unassessable_context(evaluation):
    raw=deepcopy(evaluation.to_dict());row=raw['validation_records'][0]
    row.update(status='not_assessable',parameters_used=None,predicted_absorption_m_inv=None,failure={'stage':'validation_context','error_type':'ValueError','message':'forged gap'})
    with pytest.raises(ValueError,match='compatible holdout'):OpticalHoldoutEvaluation.from_dict(raw)
