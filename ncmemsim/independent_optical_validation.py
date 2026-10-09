# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Fixed-parameter holdout evaluation; no optimization or calibration promotion."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import json,math
import numpy as np
from .independent_data import _Archive,_keys,_canonical,_match,_text,_number,_unique,_constant,IndependentStudySplit
from .independent_optical_fit import OpticalTrainingContext,OpticalTrainingFitResult,predict_optical_training
from .workflows.evidence import DataOrigin
from .ensemble.execution import _runtime

__all__=['OpticalHoldoutCriteria','OpticalHoldoutPlan','OpticalHoldoutEvaluation',
         'review_optical_holdout_admission','evaluate_optical_holdout']


@dataclass(frozen=True)
class OpticalHoldoutCriteria(_Archive):
    max_rmse_m_inv: float
    max_whitened_rmse: float
    max_abs_marginal_standardized_residual: float
    min_observations: int
    require_local_identifiability: bool = True

    def __post_init__(self):
        for name in ('max_rmse_m_inv','max_whitened_rmse','max_abs_marginal_standardized_residual'):object.__setattr__(self,name,_number(getattr(self,name)))
        if type(self.min_observations) is not int or self.min_observations<1:raise ValueError('positive integer observation criterion required')
        if type(self.require_local_identifiability) is not bool:raise ValueError('boolean identifiability criterion required')

    def to_dict(self):return {'schema_version':'optical-holdout-criteria-v1',**asdict(self),'rmse_unit':'m^-1','standardized_metric_unit':'1','application':'every validation package separately'}
    @classmethod
    def from_dict(cls,data):
        names=tuple(cls.__dataclass_fields__);_keys(data,('schema_version',*names,'rmse_unit','standardized_metric_unit','application'))
        obj=cls(**{k:data[k] for k in names});_match(data,obj.to_dict());return obj


@dataclass(frozen=True)
class OpticalHoldoutPlan(_Archive):
    name: str
    training_context: OpticalTrainingContext
    criteria: OpticalHoldoutCriteria
    mode: str
    predeclaration_evidence: str

    def __post_init__(self):
        _text(self.name,'holdout plan name');_text(self.predeclaration_evidence,'predeclaration evidence')
        if type(self.training_context) is not OpticalTrainingContext or type(self.criteria) is not OpticalHoldoutCriteria:raise ValueError('typed training context/criteria required')
        expected={'independent_measured':'measured_training','synthetic_diagnostic':'synthetic_diagnostic'}
        if self.mode not in expected or self.training_context.mode!=expected[self.mode]:raise ValueError('plan and training modes disagree')
        object.__setattr__(self,'training_context',OpticalTrainingContext.from_dict(self.training_context.to_dict()))
        object.__setattr__(self,'criteria',OpticalHoldoutCriteria.from_dict(self.criteria.to_dict()))

    def to_dict(self):return {'schema_version':'optical-holdout-plan-v1','name':self.name,'training_context':self.training_context.to_dict(),
        'criteria':self.criteria.to_dict(),'mode':self.mode,'predeclaration_evidence':self.predeclaration_evidence,
        'declared_timing':'before_training_and_holdout_inspection','timing_authenticated':False}
    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','name','training_context','criteria','mode','predeclaration_evidence','declared_timing','timing_authenticated'))
        obj=cls(data['name'],OpticalTrainingContext.from_dict(data['training_context']),OpticalHoldoutCriteria.from_dict(data['criteria']),data['mode'],data['predeclaration_evidence']);_match(data,obj.to_dict());return obj


def review_optical_holdout_admission(split: IndependentStudySplit):
    """Retain P1 admission and negatives without evaluating a model."""
    if type(split) is not IndependentStudySplit:raise ValueError('typed independent-study split required')
    return {'split_hash':split.contract_hash,**split.summary,'model_evaluated':False,'parameters_promoted':False}


def _admission(plan,fit,split):
    fit_raw=fit.to_dict();fit_context=OpticalTrainingContext.from_dict(fit_raw['context'])
    if fit_context.contract_hash!=plan.training_context.contract_hash:raise ValueError('training fit does not belong to the frozen plan context')
    if len(split.training)!=1 or split.training[0].contract_hash!=fit_context.data_package.contract_hash:raise ValueError('split training package must match the complete P2 training source')
    source=split.summary;bad=[];gaps=[]
    if plan.mode=='independent_measured':
        if source['status']=='not_admissible':bad.extend(source['negative_reasons'])
        elif source['status']=='not_assessable':gaps.extend(source['acquisition_gaps'])
    else:
        if any(p.dataset_evidence.origin is not DataOrigin.SYNTHETIC for p in split.training+split.validation):bad.append('diagnostic_mode_requires_all_synthetic_sources')
        # Bypass only the experimental-origin prohibition, never actual overlap.
        bad.extend(x for x in source['negative_reasons'] if not x.startswith('package_not_admissible:'))
        for package in split.training+split.validation:
            if not package.lineage.observation_groups or not package.lineage.observation_ids or not package.lineage.observation_artifact_sha256:gaps.append('diagnostic_observation_lineage_missing:'+package.name)
        if source['shared_systematic_ids'] and split.shared_systematics_assessment is None:gaps.append('shared_systematics_review_missing')
    if fit.summary['status']=='failed':gaps.append('training_fit_not_successful')
    status='not_admissible' if bad else 'not_assessable' if gaps else 'ready'
    return {'status':status,'negative_reasons':sorted(set(bad)),'acquisition_gaps':sorted(set(gaps)),
        'p1_split_summary':source,'independent_experiment_certified':False}


def _rmse(values):
    a=np.asarray(values,dtype=float);scale=float(np.max(abs(a)))
    return 0. if scale==0 else scale*float(np.sqrt(np.mean((a/scale)**2)))


def _record_projection(record,package,plan,fit):
    _keys(record,('package_hash','status','parameters_used','predicted_absorption_m_inv','failure'))
    if record['package_hash']!=package.contract_hash:raise ValueError('validation package identity mismatch')
    if record['status'] in ('not_assessable','evaluation_failed'):
        if record['parameters_used'] is not None or record['predicted_absorption_m_inv'] is not None:raise ValueError('unassessed holdout must not invent predictions')
        _keys(record['failure'],('stage','error_type','message'))
        for value in record['failure'].values():_text(value,'holdout failure evidence')
        if record['failure']['stage']!='validation_context' and record['status']=='not_assessable':raise ValueError('unassessable source stage mismatch')
        if record['status']=='not_assessable':
            try:OpticalTrainingContext(package,plan.training_context.specification,plan.training_context.mode)
            except (ValueError,TypeError):pass
            else:raise ValueError('compatible holdout context cannot be declared unassessable')
        return {'status':record['status'],'metrics':None,'criteria_results':[],'failed_criteria':[],'failure':record['failure']}
    if record['status']!='evaluated' or record['failure'] is not None:raise ValueError('invalid holdout evaluation record')
    numeric=fit.to_dict()['numerical_result'];_match(record['parameters_used'],numeric['fitted_parameters'])
    context=OpticalTrainingContext(package,plan.training_context.specification,plan.training_context.mode)
    raw=package.dataset_evidence.to_dict()['dataset'];observed=np.asarray(raw['absorption_coefficient_m_inv'])
    if type(record['predicted_absorption_m_inv']) is not list or len(record['predicted_absorption_m_inv'])!=observed.size:raise ValueError('complete stored holdout predictions required')
    predicted=np.asarray([_number(x) for x in record['predicted_absorption_m_inv']]);residual=predicted-observed;white=context._whiten(residual)
    marginal=residual/np.asarray(package.uncertainty.standard_uncertainty)
    if not np.all(np.isfinite(marginal)):raise ValueError('nonfinite marginal standardized residual')
    metrics={'n_observations':int(observed.size),'rmse_m_inv':_rmse(residual),'whitened_rmse':_rmse(white),'max_abs_marginal_standardized_residual':float(np.max(abs(marginal)))}
    criteria=plan.criteria;results=[]
    def criterion(name,observed,threshold,comparison,passed):results.append({'name':name,'observed':observed,'threshold':threshold,'comparison':comparison,'passed':bool(passed)})
    criterion('minimum_observations',metrics['n_observations'],criteria.min_observations,'>=',metrics['n_observations']>=criteria.min_observations)
    for name,limit in (('rmse_m_inv',criteria.max_rmse_m_inv),('whitened_rmse',criteria.max_whitened_rmse),('max_abs_marginal_standardized_residual',criteria.max_abs_marginal_standardized_residual)):
        criterion(name,metrics[name],limit,'<=',metrics[name]<=limit)
    if criteria.require_local_identifiability:criterion('training_local_identifiability',fit.summary['locally_identifiable'],True,'is_true',fit.summary['locally_identifiable'] is True)
    return {'status':'evaluated','metrics':metrics,'raw_residuals_m_inv':residual.tolist(),'whitened_residuals':white.tolist(),
        'criteria_results':results,'failed_criteria':[x['name'] for x in results if not x['passed']],'failure':None}


def _evaluation_projection(raw):
    _keys(raw,('schema_version','plan','plan_hash','training_fit','training_fit_hash','split','split_hash','runtime','validation_records'))
    if raw['schema_version']!='optical-holdout-evaluation-v1':raise ValueError('unsupported holdout schema')
    plan=OpticalHoldoutPlan.from_dict(raw['plan']);fit=OpticalTrainingFitResult.from_dict(raw['training_fit']);split=IndependentStudySplit.from_dict(raw['split'])
    if raw['plan_hash']!=plan.contract_hash or raw['training_fit_hash']!=fit.contract_hash or raw['split_hash']!=split.contract_hash:raise ValueError('holdout source identities mismatch')
    _keys(raw['runtime'],('python','python_implementation','numpy','ncmemsim'))
    for value in raw['runtime'].values():_text(value,'runtime version')
    admission=_admission(plan,fit,split);records=raw['validation_records']
    if type(records) is not list:raise ValueError('validation records list required')
    if admission['status']!='ready':
        if records:raise ValueError('blocked admission cannot retain model predictions')
        summaries=[];status=admission['status'];passed=None
    else:
        if len(records)!=len(split.validation):raise ValueError('one outcome per validation package required')
        summaries=[_record_projection(row,pkg,plan,fit) for row,pkg in zip(records,split.validation,strict=True)]
        if any(x['status']=='evaluation_failed' for x in summaries):status='evaluation_failed';passed=None
        elif any(x['status']=='not_assessable' for x in summaries):status='not_assessable';passed=None
        else:
            passed=all(not x['failed_criteria'] for x in summaries)
            status=('diagnostic_validation_passed' if plan.mode=='synthetic_diagnostic' else 'declared_independent_validation_passed') if passed else 'validation_failed'
    return {'status':status,'mode':plan.mode,'admission':admission,'criteria_passed':passed,
        'validation_package_count':len(split.validation),'evaluated_count':sum(x['status']=='evaluated' for x in summaries),
        'validation_outcomes':summaries,'training_parameters_unchanged':True,'parameters_promoted':False,
        'scientific_status':'synthetic_holdout_diagnostic_not_calibrated' if plan.mode=='synthetic_diagnostic' else 'declared_holdout_evidence_not_calibrated'}


@dataclass(frozen=True)
class OpticalHoldoutEvaluation(_Archive):
    record_json: str

    def __post_init__(self):
        raw=json.loads(self.record_json,object_pairs_hook=_unique,parse_constant=_constant)
        summary=raw.pop('summary',None);expected=_evaluation_projection(raw)
        if summary is not None:_match(summary,expected)
        object.__setattr__(self,'record_json',_canonical(raw))
    @property
    def summary(self):return _evaluation_projection(json.loads(self.record_json))
    def to_dict(self):return {**json.loads(self.record_json),'summary':self.summary}
    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','plan','plan_hash','training_fit','training_fit_hash','split','split_hash','runtime','validation_records','summary'))
        obj=cls(_canonical(data));_match(data,obj.to_dict());return obj


def evaluate_optical_holdout(plan: OpticalHoldoutPlan,training_fit: OpticalTrainingFitResult,split: IndependentStudySplit):
    """Apply fixed P2 parameters; never optimize or promote calibration."""
    if type(plan) is not OpticalHoldoutPlan or type(training_fit) is not OpticalTrainingFitResult or type(split) is not IndependentStudySplit:raise ValueError('typed plan, fit and split required')
    plan=OpticalHoldoutPlan.from_dict(plan.to_dict());training_fit=OpticalTrainingFitResult.from_dict(training_fit.to_dict());split=IndependentStudySplit.from_dict(split.to_dict())
    raw={'schema_version':'optical-holdout-evaluation-v1','plan':plan.to_dict(),'plan_hash':plan.contract_hash,
        'training_fit':training_fit.to_dict(),'training_fit_hash':training_fit.contract_hash,
        'split':split.to_dict(),'split_hash':split.contract_hash,'runtime':_runtime(),'validation_records':[]}
    if _admission(plan,training_fit,split)['status']=='ready':
        numeric=training_fit.to_dict()['numerical_result']
        for package in split.validation:
            row={'package_hash':package.contract_hash,'status':'not_assessable','parameters_used':None,'predicted_absorption_m_inv':None,'failure':None}
            try:context=OpticalTrainingContext(package,plan.training_context.specification,plan.training_context.mode)
            except (ValueError,TypeError) as error:row['failure']={'stage':'validation_context','error_type':type(error).__name__,'message':str(error)}
            else:
                try:
                    row.update(status='evaluated',parameters_used=numeric['fitted_parameters'],predicted_absorption_m_inv=predict_optical_training(context,numeric['fitted_values']).tolist())
                    _record_projection(row,package,plan,training_fit)
                except (ValueError,RuntimeError,OverflowError,FloatingPointError,np.linalg.LinAlgError) as error:row.update(status='evaluation_failed',parameters_used=None,predicted_absorption_m_inv=None,failure={'stage':'holdout_model_or_metric','error_type':type(error).__name__,'message':str(error) or type(error).__name__})
            raw['validation_records'].append(row)
    return OpticalHoldoutEvaluation(_canonical(raw))
