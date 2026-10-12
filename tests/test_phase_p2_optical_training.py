# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""P2 numerical/mechanical fixtures only; no admitted experimental datasets."""
from dataclasses import replace,FrozenInstanceError
from copy import deepcopy
import json
import numpy as np
import pytest
from examples.phase_p2_optical_training_reference import build_context,run_reference,TRUE_PARAMETERS
from ncmemsim.independent_optical_fit import OpticalFitSpecification,OpticalTrainingContext,OpticalTrainingFitResult,predict_optical_training,fit_optical_training
from ncmemsim.independent_data import ExperimentalDataPackage
from ncmemsim.workflows.evidence import DatasetEvidence
from ncmemsim.hashing import canonical_hash
from ncmemsim.fitting import FitParameterSet,FitParameter,LeastSquaresConfig


def change_data(context,**updates):
    evidence=context.data_package.dataset_evidence.to_dict();evidence['dataset'].update(updates)
    evidence['dataset_hash']=canonical_hash(evidence['dataset']);evidence.pop('evidence_hash')
    return replace(context.data_package,dataset_evidence=DatasetEvidence(json.dumps(evidence)))


@pytest.fixture(scope='module')
def result():return run_reference()


def test_synthetic_recovery_is_not_calibration(result):
    assert result.summary['status']=='diagnostic_fitted'
    assert result.summary['scientific_status']=='training_only_not_calibrated'
    assert result.summary['parameter_status']=='FITTED'
    for name,value in TRUE_PARAMETERS.items():assert result.summary['fitted_parameters'][name]==pytest.approx(value,rel=1e-7)
    assert result.to_dict()['context']['summary']['validation_data_consumed'] is False
    assert OpticalTrainingFitResult.from_json(result.to_json())==result


def test_prediction_uses_unchanged_reference_equations():
    from ncmemsim.materials.optics.near_edge import GeSnNearEdgeReferenceModel,GeSnNearEdgeParameterSet
    from ncmemsim.materials import make_ge
    ctx=build_context();values=ctx.specification.parameter_set.initial_parameters if hasattr(ctx.specification.parameter_set,'initial_parameters') else ctx.specification.parameter_set.values_to_dict(ctx.specification.parameter_set.initial_values)
    model=GeSnNearEdgeReferenceModel(GeSnNearEdgeParameterSet(name=ctx.specification.name,**values))
    raw=ctx.data_package.dataset_evidence.to_dict()['dataset']
    expected=[model.evaluate(make_ge(),x).absorption_coefficient_m_inv for x in raw['wavelength_nm']]
    assert np.array_equal(predict_optical_training(ctx),expected)


def test_pointwise_whitening_matches_existing_objective():
    from ncmemsim.fitting import least_squares_residuals
    ctx=build_context();raw=ctx.data_package.dataset_evidence.to_dict()['dataset'];predicted=predict_optical_training(ctx)
    expected=least_squares_residuals(raw['absorption_coefficient_m_inv'],predicted,uncertainty=ctx.data_package.uncertainty.standard_uncertainty)
    assert np.array_equal(ctx._whiten(predicted-np.asarray(raw['absorption_coefficient_m_inv'])),expected)


def test_covariance_gls_quadratic_form_and_recovery():
    ctx=build_context();n=ctx.summary['n_observations'];covariance=1e6*(.8*np.eye(n)+.2*np.ones((n,n)))
    budget=replace(ctx.data_package.uncertainty,correlation_policy='covariance_supplied',covariance=tuple(tuple(float(x) for x in row) for row in covariance))
    ctx=replace(ctx,data_package=replace(ctx.data_package,uncertainty=budget))
    delta=np.arange(n,dtype=float)+1;white=ctx._whiten(delta)
    assert float(white@white)==pytest.approx(float(delta@np.linalg.solve(covariance,delta)))
    r=fit_optical_training(ctx)
    assert r.summary['status']=='diagnostic_fitted'
    assert r.summary['fitted_parameters']['urbach_energy_eV']==pytest.approx(TRUE_PARAMETERS['urbach_energy_eV'],rel=1e-7)
    assert OpticalTrainingFitResult.from_json(r.to_json())==r


def test_singular_covariance_is_not_silently_pseudoinverted():
    ctx=build_context();n=ctx.summary['n_observations'];matrix=tuple(tuple([1e6]*n) for _ in range(n))
    package=replace(ctx.data_package,uncertainty=replace(ctx.data_package.uncertainty,correlation_policy='covariance_supplied',covariance=matrix))
    with pytest.raises(ValueError,match='positive-definite'):replace(ctx,data_package=package)


def test_measured_mode_cannot_be_used_with_synthetic_or_incomplete_data():
    ctx=build_context()
    with pytest.raises(ValueError,match='P1-eligible'):replace(ctx,mode='measured_training')
    evidence=ctx.data_package.dataset_evidence.to_dict();evidence['origin']='measured';evidence.pop('evidence_hash')
    package=replace(ctx.data_package,dataset_evidence=DatasetEvidence(json.dumps(evidence)),lineage=replace(ctx.data_package.lineage,data_kind='model_derived'))
    with pytest.raises(ValueError,match='P1-eligible'):replace(ctx,data_package=package,mode='measured_training')
    with pytest.raises(ValueError,match='cannot bypass'):replace(ctx,data_package=package)


def test_complete_measured_declarations_are_training_only():
    # Invented fixture metadata tests the mode, not real experimental approval.
    ctx=build_context();evidence=ctx.data_package.dataset_evidence.to_dict();evidence['origin']='measured';evidence.pop('evidence_hash')
    lineage=replace(ctx.data_package.lineage,data_kind='model_derived',study_id='P2 invented fixture',specimen_id='unit/specimen',acquisition_id='unit/acquisition',acquisition_roots=('unit/root',),redistribution_terms='unit test only',temperature_standard_uncertainty_K=1.,specimen_characterization='invented bulk fixture',measurement_geometry='test geometry',instrument_and_calibration='not a real instrument')
    package=replace(ctx.data_package,dataset_evidence=DatasetEvidence(json.dumps(evidence)),lineage=lineage,reviewer='unit fixture reviewer',review_notes='mechanical invented declarations; no physical measurement authentication')
    assert package.summary['status']=='eligible_for_independent_study'
    result=fit_optical_training(replace(ctx,data_package=package,mode='measured_training'))
    assert result.summary['status']=='fitted'
    assert result.summary['scientific_status']=='training_only_not_calibrated'


@pytest.mark.parametrize('fault',['composition','domain','temperature','wavelength_error','missing_sigma','unknown_correlation','uncertainty_gap'])
def test_unsupported_source_or_objective_rejected(fault):
    ctx=build_context();package=ctx.data_package
    if fault=='composition':package=change_data(ctx,sn_fraction=.1)
    elif fault=='domain':package=change_data(ctx,wavelength_nm=[1499.]+ctx.data_package.dataset_evidence.to_dict()['dataset']['wavelength_nm'][1:])
    elif fault=='temperature':
        evidence=package.dataset_evidence.to_dict();evidence['dataset']['metadata']['temperature_K']=301.;evidence['dataset_hash']=canonical_hash(evidence['dataset']);evidence.pop('evidence_hash')
        package=replace(package,dataset_evidence=DatasetEvidence(json.dumps(evidence)),lineage=replace(package.lineage,temperature_K=301.))
    elif fault=='wavelength_error':package=replace(package,uncertainty=replace(package.uncertainty,independent_policy='provided',independent_standard_uncertainty=tuple([.5]*8)))
    elif fault=='missing_sigma':package=replace(package,uncertainty=replace(package.uncertainty,standard_uncertainty=None,legacy_uncertainty_role='unknown'))
    elif fault=='unknown_correlation':package=replace(package,uncertainty=replace(package.uncertainty,correlation_policy='unresolved'))
    else:package=replace(package,uncertainty=replace(package.uncertainty,missing_components=('unbounded systematic',)))
    with pytest.raises(ValueError):replace(ctx,data_package=package)


@pytest.mark.parametrize('fault',['domain','nc_form','wrong_parameter','wrong_unit','nonpositive_bound','method'])
def test_invalid_specification_rejected(fault):
    spec=build_context().specification
    with pytest.raises(ValueError):
        if fault=='domain':replace(spec,wavelength_min_nm=1499.)
        elif fault=='nc_form':replace(spec,sample_form='nanocrystal')
        elif fault=='method':
            raw=spec.to_dict();raw['solver_config']['loss']='soft_l1';OpticalFitSpecification.from_dict(raw)
        else:
            parameters=list(spec.parameter_set.parameters)
            if fault=='wrong_parameter':parameters[0]=replace(parameters[0],name='direct_gap_eV')
            elif fault=='wrong_unit':parameters[0]=replace(parameters[0],unit='cm^-1')
            else:parameters[0]=replace(parameters[0],lower_bound=0.)
            replace(spec,parameter_set=FitParameterSet(tuple(parameters)))


def test_owned_inputs_and_frozen_context():
    old=build_context();ctx=OpticalTrainingContext(old.data_package,old.specification,old.mode)
    before=ctx.to_json();object.__setattr__(old.specification.parameter_set.parameters[0],'initial_value',4e6)
    assert ctx.to_json()==before
    with pytest.raises(FrozenInstanceError):ctx.mode='measured_training'


def test_unsuccessful_solver_is_retained():
    ctx=build_context();ctx=replace(ctx,specification=replace(ctx.specification,solver_config=LeastSquaresConfig(max_nfev=1)))
    result=fit_optical_training(ctx)
    assert result.summary['status']=='failed'
    assert result.to_dict()['numerical_result']['success'] is False
    assert result.to_dict()['diagnostics'] is None
    assert result.summary['parameter_status'] is None
    assert OpticalTrainingFitResult.from_json(result.to_json())==result


def test_model_or_dependency_exception_retained(monkeypatch):
    import ncmemsim.independent_optical_fit as module
    ctx=build_context()
    def forbidden(*args,**kwargs):raise RuntimeError('injected numerical failure')
    monkeypatch.setattr(module,'run_least_squares_fit',forbidden)
    result=module.fit_optical_training(ctx)
    assert result.summary['status']=='failed'
    assert result.to_dict()['numerical_result'] is None
    assert result.to_dict()['failure']['message']=='injected numerical failure'
    assert OpticalTrainingFitResult.from_json(result.to_json())==result


@pytest.mark.parametrize('fault',['extra','summary','source','predictions','residuals','jacobian','specification','runtime','diagnostics'])
def test_archive_inconsistencies_rejected(result,fault):
    raw=deepcopy(result.to_dict())
    if fault=='extra':raw['unreviewed']=True
    elif fault=='summary':raw['summary']['parameter_status']='CALIBRATED'
    elif fault=='source':raw['context_hash']='0'*64
    elif fault=='predictions':raw['observations']['predicted_absorption_m_inv'][0]*=1.01
    elif fault=='residuals':raw['numerical_result']['objective_residuals'][0]+=1
    elif fault=='jacobian':raw['numerical_result']['jacobian']=[]
    elif fault=='specification':raw['numerical_result']['parameter_specification']['parameters'][0]['initial_value']*=1.01
    elif fault=='runtime':raw['runtime']['unreviewed']='yes'
    else:raw['diagnostics']['locally_identifiable']=False
    with pytest.raises((ValueError,TypeError)):OpticalTrainingFitResult.from_dict(raw)


def test_no_optimizer_optical_or_rng_replay(result,monkeypatch):
    import ncmemsim.independent_optical_fit as module
    from ncmemsim.materials.optics.near_edge import GeSnNearEdgeReferenceModel
    def forbidden(*args,**kwargs):raise AssertionError('no replay')
    monkeypatch.setattr(module,'run_least_squares_fit',forbidden)
    monkeypatch.setattr(module,'predict_gesn_near_edge_absorption_m_inv',forbidden)
    monkeypatch.setattr(GeSnNearEdgeReferenceModel,'evaluate',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    assert OpticalTrainingFitResult.from_json(result.to_json())==result


def test_duplicate_nonfinite_and_owned_result(result):
    with pytest.raises(ValueError):OpticalTrainingFitResult.from_json(result.to_json().replace('{','{"summary":null,',1))
    with pytest.raises(ValueError):OpticalTrainingFitResult.from_json(result.to_json().replace('300.0','NaN',1))
    raw=result.to_dict();raw['context']['mode']='wrong'
    assert result.to_dict()['context']['mode']=='synthetic_diagnostic'



def test_large_finite_covariance_does_not_overflow_during_symmetrization():
    ctx=build_context();n=ctx.summary['n_observations'];matrix=tuple(tuple(1e308 if i==j else 0. for j in range(n)) for i in range(n))
    budget=replace(ctx.data_package.uncertainty,standard_uncertainty=tuple([1e154]*n),legacy_uncertainty_role='converted',correlation_policy='covariance_supplied',covariance=matrix)
    ctx=replace(ctx,data_package=replace(ctx.data_package,uncertainty=budget))
    residual=np.ones(n)
    assert np.all(ctx._whiten(residual)>0)
    assert np.allclose(ctx._whiten(residual),residual/1e154,rtol=1e-12,atol=0)



def test_subnormal_covariance_is_not_rounded_to_zero_by_symmetrization():
    import math
    ctx=build_context();n=ctx.summary['n_observations'];variance=5e-324
    matrix=tuple(tuple(variance if i==j else 0. for j in range(n)) for i in range(n))
    std=math.sqrt(variance)
    budget=replace(ctx.data_package.uncertainty,standard_uncertainty=tuple([std]*n),legacy_uncertainty_role='converted',correlation_policy='covariance_supplied',covariance=matrix)
    ctx=replace(ctx,data_package=replace(ctx.data_package,uncertainty=budget))
    residual=np.ones(n)*1e-160
    assert np.allclose(ctx._whiten(residual),residual/std,rtol=1e-12,atol=0)
