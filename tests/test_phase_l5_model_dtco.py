# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""MODEL DTCO linkage, denominators, eligibility and exact Pareto semantics."""
from dataclasses import replace
import pytest

from ncmemsim.dtco import SweepPoint, MetricAnalysisSpec, MetricDefinition, ConstraintOperator, ObjectiveDirection
from ncmemsim.ensemble import EnsembleScalarDefinition, EnsembleScalarKind, EnsembleConstraint, EnsembleObjective, EnsembleStatisticsSpec
from ncmemsim.ensemble.model_analysis import analyze_model_execution
from ncmemsim.ensemble.model_execution import execute_model_sample_manifest
from ncmemsim.ensemble.model_dtco import ModelDTCOStudy, evaluate_model_scalar, evaluate_model_eligibility, analyze_model_pareto
from test_phase_l2_model_execution import make


def study(index, values=(1,3), *, failing=(), link=True, experiment='a'*64, metric_unit='Hz', quantiles=(.05,.5,.95)):
    device, spec, manifest = make(count=len(values))
    point = SweepPoint(experiment,index,(("geometry",float(index+1)),))
    def evaluator(realization, settings):
        i=realization.sample.sample_index
        if i in failing:
            raise ArithmeticError('controlled failure')
        return {'x':values[i]}
    context={'scope':'synthetic'}
    if link:context['dtco_design_point']=point.to_dict()
    source=execute_model_sample_manifest(manifest,device,evaluator,evaluation_id='L5-tests',workflow_context=context)
    analysis=analyze_model_execution(source,MetricAnalysisSpec('metrics',(MetricDefinition('x',('x',),metric_unit),)),
                                     statistics_spec=EnsembleStatisticsSpec(quantiles))
    return point,analysis


def linked(index, values=(1,3), **kwargs):
    return ModelDTCOStudy(*study(index,values,**kwargs))


def scalar(kind=EnsembleScalarKind.MEAN,unit='Hz',metric='x',quantile=None):
    return EnsembleScalarDefinition('scalar',kind,unit,metric,quantile)


def objective(direction=ObjectiveDirection.MINIMIZE):
    return EnsembleObjective('objective',scalar(),direction)


def test_linkage_is_mandatory_and_exact():
    point,source=study(0,link=False)
    with pytest.raises(ValueError,match='linkage'):ModelDTCOStudy(point,source)
    point,source=study(0)
    with pytest.raises(ValueError,match='linkage'):ModelDTCOStudy(replace(point,index=1),source)
    with pytest.raises(TypeError):ModelDTCOStudy(point,object())
    s=ModelDTCOStudy(point,source)
    assert s.to_dict()['point_hash']==point.point_hash
    assert s.to_dict()['source_analysis_hash']==source.analysis_hash


@pytest.mark.parametrize('kind,value',[(EnsembleScalarKind.MEAN,2),(EnsembleScalarKind.STANDARD_DEVIATION,1),
    (EnsembleScalarKind.MINIMUM,1),(EnsembleScalarKind.MAXIMUM,3),(EnsembleScalarKind.MEDIAN,2)])
def test_scalar_projections(kind,value):
    result=evaluate_model_scalar(linked(0),scalar(kind))
    assert result['value']==value and result['denominator']==2
    assert result['status']=='defined'


def test_quantile_declared_only_and_units():
    s=linked(0)
    assert evaluate_model_scalar(s,scalar(EnsembleScalarKind.QUANTILE,quantile=.5))['value']==2
    with pytest.raises(ValueError,match='quantile'):evaluate_model_scalar(s,scalar(EnsembleScalarKind.QUANTILE,quantile=.25))
    with pytest.raises(ValueError,match='unit'):evaluate_model_scalar(s,scalar(unit='V'))
    with pytest.raises(ValueError):evaluate_model_scalar(s,scalar(metric='unknown'))


@pytest.mark.parametrize('kind,value,denominator',[(EnsembleScalarKind.COVERAGE_FRACTION,.5,2),
    (EnsembleScalarKind.SIMULATED_PASS_FRACTION,.5,2),(EnsembleScalarKind.FAILURE_FRACTION,.5,2),
    (EnsembleScalarKind.ENSEMBLE_FEASIBILITY_FRACTION,1,1)])
def test_fraction_denominators_preserved(kind,value,denominator):
    result=evaluate_model_scalar(linked(0,failing=(1,)),scalar(kind,'1',None))
    assert result['value']==value and result['denominator']==denominator


@pytest.mark.parametrize('operator,threshold,status',[(ConstraintOperator.LE,2,'eligible'),
    (ConstraintOperator.GE,2,'eligible'),(ConstraintOperator.LE,1,'ineligible'),(ConstraintOperator.GE,3,'ineligible')])
def test_inclusive_eligibility_bounds(operator,threshold,status):
    result=evaluate_model_eligibility(linked(0),(EnsembleConstraint('bound',scalar(),operator,threshold,'Hz'),))
    assert result.status==status


def test_undefined_precedes_violation_and_failure_coverage_is_explicit():
    s=linked(0,failing=(0,1))
    c=EnsembleConstraint('mean',scalar(),ConstraintOperator.LE,3,'Hz')
    coverage=EnsembleConstraint('coverage',scalar(EnsembleScalarKind.COVERAGE_FRACTION,'1',None),ConstraintOperator.GE,1,'1')
    assert evaluate_model_eligibility(s,(coverage,c)).status=='unevaluable'
    assert evaluate_model_eligibility(s,(coverage,)).status=='ineligible'
    assert evaluate_model_eligibility(s).status=='eligible' # No implicit policy.
    result=analyze_model_pareto((evaluate_model_eligibility(s),),(objective(),)).to_dict()
    assert result['points'][0]['exclusion_reason']=='undefined-objective'
    assert result['fronts']==[]


def test_exact_fronts_ties_and_source_order():
    sources=tuple(evaluate_model_eligibility(linked(i,v)) for i,v in enumerate([(1,1),(1,1),(2,2),(3,3)]))
    data=analyze_model_pareto(sources,(objective(),)).to_dict()
    assert data['fronts']==[[0,1],[2],[3]]
    assert [p['rank'] for p in data['points']]==[0,0,1,2]
    assert analyze_model_pareto(sources,(objective(ObjectiveDirection.MAXIMIZE),)).to_dict()['fronts']==[[3],[2],[0,1]]


def test_tradeoff_two_objectives_and_explicit_excluded_design():
    coverage=EnsembleConstraint('coverage',scalar(EnsembleScalarKind.COVERAGE_FRACTION,'1',None),ConstraintOperator.GE,1,'1')
    sources=tuple(evaluate_model_eligibility(linked(i,v,failing=(1,) if i==2 else ()),(coverage,))
                  for i,v in enumerate([(1,3),(3,3),(0,0)]))
    objectives=(objective(),EnsembleObjective('spread',scalar(EnsembleScalarKind.STANDARD_DEVIATION),ObjectiveDirection.MINIMIZE))
    data=analyze_model_pareto(sources,objectives).to_dict()
    assert data['fronts']==[[0,1]]
    assert data['points'][2]['exclusion_reason']=='ineligible'
    assert data['ranked_design_count']==2 and data['excluded_design_count']==1
    assert data['points'][2]['objective_values'][0]['denominator']==1


@pytest.mark.parametrize('change', ['units','quantiles','experiment','eligibility','index'])
def test_incompatible_or_duplicate_design_identities_rejected(change):
    first=evaluate_model_eligibility(linked(0))
    kwargs={'metric_unit':'V'} if change=='units' else {'quantiles':()} if change=='quantiles' else {'experiment':'b'*64} if change=='experiment' else {}
    second=evaluate_model_eligibility(linked(0 if change=='index' else 1,**kwargs),
         (EnsembleConstraint('extra',scalar(),ConstraintOperator.LE,3,'Hz'),) if change=='eligibility' else ())
    with pytest.raises(ValueError):analyze_model_pareto((first,second),(objective(),))


def test_invalid_policy_declarations_and_empty_population():
    s=linked(0);c=EnsembleConstraint('c',scalar(),ConstraintOperator.LE,3,'Hz')
    with pytest.raises(ValueError):evaluate_model_eligibility(s,(c,c))
    with pytest.raises(TypeError):evaluate_model_eligibility(s,(object(),))
    with pytest.raises(ValueError):analyze_model_pareto((),())
    with pytest.raises(ValueError):analyze_model_pareto((),(objective(),objective()))
    assert analyze_model_pareto((),(objective(),)).to_dict()['fronts']==[]


def test_projection_owns_output_and_never_reruns_physics(monkeypatch):
    import ncmemsim.ensemble.model_execution as module
    source=evaluate_model_eligibility(linked(0))
    monkeypatch.setattr(module,'execute_model_sample_manifest',lambda *a,**k:pytest.fail('rerun'))
    result=analyze_model_pareto((source,),(objective(),))
    old=result.to_dict()
    data=result.to_dict();data['points'][0]['rank']=99
    assert result.to_dict()==old


@pytest.fixture(scope='module')
def reference():
    from examples.phase_l5_model_dtco_reference import run_reference
    return run_reference()


def test_real_reference_geometry_pairing_linkage_and_numerical_audit(reference):
    from ncmemsim.ensemble.model_analysis import ModelPopulationAnalysis
    pareto=reference['pareto']
    assert pareto['attempted_design_count']==pareto['ranked_design_count']==3
    values=[]; hashes=[]
    for archive in pareto['sources']:
        restored=ModelPopulationAnalysis.from_dict(archive['source'])
        assert restored.counts['attempted_count']==restored.counts['assessed_count']==16
        assert restored.counts['failed_count']==0
        values.append([s.values for s in restored.source.manifest.samples])
        hashes.append(restored.source.manifest.sampling_spec.study.base_device_hash)
        thickness=archive['design_point']['assignments'][0]['value']
        nominal=restored.source.to_dict()['execution']['nominal']['device']
        # The candidate hash and distinct declared thickness bind actual source baselines.
        assert thickness in (1,1.1,1.2)
        layer = next(layer for layer in nominal['device']['layers'] if layer['name'] == 'inter_fg1_sio2')
        assert layer['thickness_nm'] == thickness
    assert values[0]==values[1]==values[2] and len(set(hashes))==3
    assert all(max(a['occupation_deltas_16_vs_32'])<=a['occupation_atol'] for a in reference['timestep_audit'])
    assert 'occupation spread is not claimed numerically resolved' in reference['limits']


def test_reference_export_no_overwrite_and_hash_validation(reference,tmp_path):
    from examples.phase_l5_model_dtco_reference import write_reference
    write_reference(tmp_path/'reference',reference)
    with pytest.raises(FileExistsError):write_reference(tmp_path/'reference',reference)
    with pytest.raises(ValueError):write_reference(tmp_path/'bad',{**reference,'reference_hash':'0'*64})


@pytest.mark.parametrize('value', [3.0, -3.0, 0.1, 1e100])
@pytest.mark.parametrize('probability', [.05, .95, .33])
def test_constant_quantile_preserves_exact_value(value, probability):
    from ncmemsim.ensemble.statistics import _linear_quantile
    assert _linear_quantile([value, value], probability) == value
