# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Owned direct/Urbach training fit; no holdout or calibration qualification."""
from __future__ import annotations
from dataclasses import dataclass
import math,json
import numpy as np
from .independent_data import ExperimentalDataPackage,_Archive,_keys,_canonical,_match,_text,_number
from .workflows.evidence import DataOrigin,_encode
from .fitting import FitParameter,FitParameterSet,LeastSquaresConfig,DeterministicFitResult,run_least_squares_fit
from .fit_diagnostics import analyze_fit_uncertainty
from .materials.optics.near_edge import GeSnNearEdgeParameterSet
from .materials.optics.near_edge_fit import predict_gesn_near_edge_absorption_m_inv
from .materials.optics.models import direct_gap_gesn_eV
from .ensemble.execution import _runtime

__all__=['OpticalFitSpecification','OpticalTrainingContext','OpticalTrainingFitResult',
         'predict_optical_training','fit_optical_training']
_UNITS={'direct_prefactor_A':'m^-1 eV^(1/2)','urbach_energy_eV':'eV'}


def _parameters(data):
    _keys(data,('schema_version','parameters'))
    if type(data['parameters']) is not list:raise ValueError('parameter list required')
    params=[]
    for item in data['parameters']:
        _keys(item,('name','initial_value','lower_bound','upper_bound','unit','description'))
        params.append(FitParameter(**item))
    obj=FitParameterSet(tuple(params));_match(data,obj.to_dict());return obj


def _config(data):
    _keys(data,('method','jacobian','loss','parameter_scaling','ftol','xtol','gtol','max_nfev'))
    obj=LeastSquaresConfig(data['ftol'],data['xtol'],data['gtol'],data['max_nfev']);_match(data,obj.to_dict());return obj


@dataclass(frozen=True)
class OpticalFitSpecification(_Archive):
    name: str
    parameter_set: FitParameterSet
    solver_config: LeastSquaresConfig
    wavelength_min_nm: float
    wavelength_max_nm: float
    sample_form: str
    assumption_review: str

    def __post_init__(self):
        _text(self.name,'fit specification name');_text(self.assumption_review,'model/selection assumption review')
        if type(self.parameter_set) is not FitParameterSet or type(self.solver_config) is not LeastSquaresConfig:raise ValueError('typed parameter specification and solver configuration required')
        params=_parameters(self.parameter_set.to_dict());config=_config(self.solver_config.to_dict())
        if set(params.names)!=set(_UNITS) or params.n_parameters!=2:raise ValueError('only direct prefactor and Urbach energy may be fitted')
        for parameter in params.parameters:
            if parameter.unit!=_UNITS[parameter.name] or parameter.lower_bound<=0:raise ValueError('positive bounds and exact near-edge parameter units required')
        low=_number(self.wavelength_min_nm);high=_number(self.wavelength_max_nm)
        if not 1500<=low<high<=2500:raise ValueError('P2 domain must be an explicit subset of 1500-2500 nm')
        if self.sample_form not in ('bulk','film'):raise ValueError('no automatic nanocrystal/other-form transfer')
        object.__setattr__(self,'parameter_set',params);object.__setattr__(self,'solver_config',config)
        object.__setattr__(self,'wavelength_min_nm',low);object.__setattr__(self,'wavelength_max_nm',high)

    def to_dict(self):return {'schema_version':'optical-fit-specification-v1','name':self.name,
        'parameter_set':self.parameter_set.to_dict(),'solver_config':self.solver_config.to_dict(),
        'wavelength_min_nm':self.wavelength_min_nm,'wavelength_max_nm':self.wavelength_max_nm,'sample_form':self.sample_form,
        'assumption_review':self.assumption_review,'model':'existing-ge-direct-urbach-c1-reference-v1',
        'temperature_K':300.,'strain_policy':'unstrained_bulk_like_reference','fixed_direct_gap_eV':direct_gap_gesn_eV(0.),
        'objective':'linear-alpha-generalized-least-squares-v1','residual_sign':'prediction-minus-observation',
        'covariance_policy':'cholesky-of-symmetric-positive-definite-observable-covariance',
        'independent_axis_policy':'exact-or-explicitly-reviewed-negligible'}

    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','name','parameter_set','solver_config','wavelength_min_nm','wavelength_max_nm','sample_form','assumption_review','model','temperature_K','strain_policy','fixed_direct_gap_eV','objective','residual_sign','covariance_policy','independent_axis_policy'))
        obj=cls(data['name'],_parameters(data['parameter_set']),_config(data['solver_config']),data['wavelength_min_nm'],data['wavelength_max_nm'],data['sample_form'],data['assumption_review']);_match(data,obj.to_dict());return obj


@dataclass(frozen=True)
class OpticalTrainingContext(_Archive):
    data_package: ExperimentalDataPackage
    specification: OpticalFitSpecification
    mode: str

    def __post_init__(self):
        if type(self.data_package) is not ExperimentalDataPackage or type(self.specification) is not OpticalFitSpecification:raise ValueError('typed training package and fit specification required')
        package=ExperimentalDataPackage.from_dict(self.data_package.to_dict());spec=OpticalFitSpecification.from_dict(self.specification.to_dict())
        if self.mode=='measured_training':
            if package.dataset_evidence.origin is not DataOrigin.MEASURED or package.summary['status']!='eligible_for_independent_study':raise ValueError('measured training requires P1-eligible declared data')
        elif self.mode=='synthetic_diagnostic':
            if package.dataset_evidence.origin is not DataOrigin.SYNTHETIC:raise ValueError('synthetic diagnostic mode cannot bypass measured-data admission')
        else:raise ValueError('explicit measured-training or synthetic-diagnostic mode required')
        data=package.dataset_evidence.to_dict()['dataset'];budget=package.uncertainty
        if data['dataset_type']!='optical_absorption' or data['sn_fraction']!=0:raise ValueError('first P2 adapter supports optical absorption in pure Ge only')
        if package.lineage.temperature_K!=300.:raise ValueError('existing near-edge model has fixed nominal 300 K; no temperature response is fitted')
        wavelengths=np.asarray(data['wavelength_nm'])
        if wavelengths.size<2 or np.any(wavelengths<spec.wavelength_min_nm) or np.any(wavelengths>spec.wavelength_max_nm):raise ValueError('all training rows must remain inside the declared domain; no silent trimming')
        if budget.standard_uncertainty is None or any(x<=0 for x in budget.standard_uncertainty):raise ValueError('strictly positive declared observable standard uncertainties required')
        if budget.observable_origin=='unknown' or budget.missing_components or not budget.sources or budget.legacy_uncertainty_role=='unknown':raise ValueError('unresolved observable error budget cannot be fitted by P2')
        if budget.independent_policy!='reviewed_negligible' and not (budget.independent_policy=='provided' and all(x==0 for x in budget.independent_standard_uncertainty)):raise ValueError('non-negligible/unresolved wavelength error needs a separately reviewed errors-in-variables adapter')
        if budget.correlation_policy=='unresolved':raise ValueError('unresolved observable correlations are not diagonalized silently')
        object.__setattr__(self,'data_package',package);object.__setattr__(self,'specification',spec)
        self._whiten(np.zeros(wavelengths.size))

    def _whiten(self,residuals):
        budget=self.data_package.uncertainty
        values=np.asarray(residuals,dtype=float)
        if budget.correlation_policy=='independent':answer=values/np.asarray(budget.standard_uncertainty)
        else:
            covariance=np.asarray(budget.covariance,dtype=float)
            try:lower=np.linalg.cholesky(covariance+.5*(covariance.T-covariance))
            except np.linalg.LinAlgError as exc:raise ValueError('P2 requires positive-definite covariance; no silent pseudoinverse') from exc
            if not np.all(np.isfinite(lower)):raise ValueError("nonfinite covariance factor")
            answer=np.linalg.solve(lower,values)
        if not np.all(np.isfinite(answer)):raise ValueError('nonfinite whitened residuals')
        return answer

    @property
    def summary(self):
        data=self.data_package.dataset_evidence.to_dict()['dataset']
        return {'mode':self.mode,'data_origin':self.data_package.dataset_evidence.origin.value,
            'training_package_hash':self.data_package.contract_hash,'specification_hash':self.specification.contract_hash,
            'n_observations':len(data['wavelength_nm']),'weighting':'full_covariance_gls' if self.data_package.uncertainty.covariance is not None else 'pointwise_standard_uncertainties',
            'scientific_status':'training_only_not_calibrated','validation_data_consumed':False}

    def to_dict(self):return {'schema_version':'optical-training-context-v1','data_package':self.data_package.to_dict(),'specification':self.specification.to_dict(),'mode':self.mode,'summary':self.summary}

    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','data_package','specification','mode','summary'))
        obj=cls(ExperimentalDataPackage.from_dict(data['data_package']),OpticalFitSpecification.from_dict(data['specification']),data['mode']);_match(data,obj.to_dict());return obj


def predict_optical_training(context: OpticalTrainingContext,values=None):
    """Evaluate unchanged direct/Urbach equations on owned training wavelengths."""
    if type(context) is not OpticalTrainingContext:raise ValueError('typed optical training context required')
    spec=context.specification;params=spec.parameter_set
    values=params.initial_values if values is None else params.validate_values(values)
    named=params.values_to_dict(values)
    model=GeSnNearEdgeParameterSet(name=spec.name,direct_prefactor_A=named['direct_prefactor_A'],urbach_energy_eV=named['urbach_energy_eV'],temperature_K=300.)
    data=context.data_package.dataset_evidence.to_dict()['dataset']
    return predict_gesn_near_edge_absorption_m_inv(data['wavelength_nm'],sn_fraction=0.,parameters=model)


def _numeric(data):
    _keys(data,('schema_version','solver','scipy_version','solver_configuration','solver_configuration_hash','parameter_specification','parameter_specification_hash','initial_values','fitted_values','initial_parameters','fitted_parameters','objective_residuals','objective_sum_squares','cost','success','status','message','nfev','njev','optimality','active_mask','jacobian_parameterization','jacobian'))
    obj=DeterministicFitResult(_parameters(data['parameter_specification']),_config(data['solver_configuration']),data['initial_values'],data['fitted_values'],data['objective_residuals'],data['success'],data['status'],data['message'],data['nfev'],data['njev'],data['optimality'],data['active_mask'],data['scipy_version'],data['jacobian'])
    _match(data,obj.to_dict());return obj


def _result_projection(raw):
    _keys(raw,('schema_version','context','context_hash','runtime','numerical_result','observations','diagnostics','failure'))
    if raw['schema_version']!='optical-training-fit-result-v1':raise ValueError('unsupported optical fit result schema')
    context=OpticalTrainingContext.from_dict(raw['context'])
    if raw['context_hash']!=context.contract_hash:raise ValueError('fit context identity mismatch')
    _keys(raw['runtime'],('python','python_implementation','numpy','ncmemsim'))
    for value in raw['runtime'].values():_text(value,'runtime version')
    if raw['numerical_result'] is None:
        if raw['observations'] is not None or raw['diagnostics'] is not None:raise ValueError('failed exception cannot invent numerical observations')
        _keys(raw['failure'],('stage','error_type','message'))
        for value in raw['failure'].values():_text(value,'failure detail')
        return {'status':'failed','mode':context.mode,'parameter_status':None,'training_objective_sum_squares':None,'locally_identifiable':None,'scientific_status':'training_only_not_calibrated'}
    if raw['failure'] is not None:raise ValueError('numerical solver outcome retains its own failure status')
    result=_numeric(raw['numerical_result']);spec=context.specification
    _match(result.parameter_set.to_dict(),spec.parameter_set.to_dict());_match(result.config.to_dict(),spec.solver_config.to_dict())
    if not np.array_equal(result.initial_values,spec.parameter_set.initial_values):raise ValueError('initial parameter/specification mismatch')
    data=context.data_package.dataset_evidence.to_dict()['dataset'];observed=np.asarray(data['absorption_coefficient_m_inv'])
    o=raw['observations'];_keys(o,('predicted_absorption_m_inv','raw_residuals_m_inv','rmse_m_inv'))
    if type(o['predicted_absorption_m_inv']) is not list or len(o['predicted_absorption_m_inv'])!=observed.size:raise ValueError('complete stored prediction vector required')
    predicted=np.asarray([_number(x) for x in o['predicted_absorption_m_inv']]);residual=predicted-observed
    if result.objective_residuals.size!=observed.size or not np.allclose(context._whiten(residual),result.objective_residuals,rtol=1e-10,atol=1e-12):raise ValueError('stored predictions/residuals/source uncertainty disagree')
    _match(o,{'predicted_absorption_m_inv':predicted.tolist(),'raw_residuals_m_inv':residual.tolist(),'rmse_m_inv':float(np.sqrt(np.mean(residual**2)))})
    expected=_encode(analyze_fit_uncertainty(result).to_dict()) if result.success else None
    _match(raw['diagnostics'],expected)
    return {'status':'diagnostic_fitted' if result.success and context.mode=='synthetic_diagnostic' else 'fitted' if result.success else 'failed',
        'mode':context.mode,'parameter_status':'FITTED' if result.success else None,'fitted_parameters':result.fitted_parameters,
        'training_objective_sum_squares':result.objective_sum_squares,'training_rmse_m_inv':o['rmse_m_inv'],
        'locally_identifiable':None if expected is None else expected['locally_identifiable'],'scientific_status':'training_only_not_calibrated'}


@dataclass(frozen=True)
class OpticalTrainingFitResult(_Archive):
    record_json: str

    def __post_init__(self):
        from .independent_data import _unique,_constant
        raw=json.loads(self.record_json,object_pairs_hook=_unique,parse_constant=_constant)
        summary=raw.pop('summary',None);expected=_result_projection(raw)
        if summary is not None:_match(summary,expected)
        object.__setattr__(self,'record_json',_canonical(raw))

    @property
    def summary(self):return _result_projection(json.loads(self.record_json))
    def to_dict(self):return {**json.loads(self.record_json),'summary':self.summary}
    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','context','context_hash','runtime','numerical_result','observations','diagnostics','failure','summary'))
        obj=cls(_canonical(data));_match(data,obj.to_dict());return obj


def fit_optical_training(context: OpticalTrainingContext):
    """Optimize training data only. Retain failed numerical/exception outcomes."""
    if type(context) is not OpticalTrainingContext:raise ValueError('typed optical training context required')
    owned=OpticalTrainingContext.from_dict(context.to_dict());data=owned.data_package.dataset_evidence.to_dict()['dataset'];observed=np.asarray(data['absorption_coefficient_m_inv'])
    raw={'schema_version':'optical-training-fit-result-v1','context':owned.to_dict(),'context_hash':owned.contract_hash,
        'runtime':_runtime(),'numerical_result':None,'observations':None,'diagnostics':None,'failure':None}
    try:
        result=run_least_squares_fit(owned.specification.parameter_set,lambda values:owned._whiten(predict_optical_training(owned,values)-observed),config=owned.specification.solver_config)
        predicted=predict_optical_training(owned,result.fitted_values);residual=predicted-observed
        raw.update(numerical_result=result.to_dict(),observations={'predicted_absorption_m_inv':predicted.tolist(),'raw_residuals_m_inv':residual.tolist(),'rmse_m_inv':float(np.sqrt(np.mean(residual**2)))},diagnostics=_encode(analyze_fit_uncertainty(result).to_dict()) if result.success else None)
        return OpticalTrainingFitResult(_canonical(raw))
    except (ValueError,OverflowError,FloatingPointError,RuntimeError,ImportError,np.linalg.LinAlgError) as error:
        raw.update(numerical_result=None,observations=None,diagnostics=None,failure={'stage':'optimizer/model/fit-evidence','error_type':type(error).__module__+'.'+type(error).__name__,'message':str(error) or type(error).__name__})
        return OpticalTrainingFitResult(_canonical(raw))
