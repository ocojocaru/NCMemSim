# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Additive declared-data admission contracts; not experimental calibration."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import hashlib,json,math
import numpy as np
from .workflows.evidence import DatasetEvidence,DataOrigin

__all__=['AcquisitionLineage','UncertaintyBudget','ExperimentalDataPackage',
         'IndependentStudySplit','AcquisitionGap']


def _text(value,name):
    if type(value) is not str or not value or value!=value.strip():raise ValueError(name+' must be nonempty trimmed text')


def _optional(value,name):
    if value is not None:_text(value,name)


def _labels(values,name):
    if type(values) is not tuple:raise ValueError(name+' must be an immutable tuple')
    for value in values:_text(value,name)
    if len(set(values))!=len(values):raise ValueError('duplicate '+name)


def _number(value,*,signed=False):
    if type(value) not in (int,float):raise ValueError('real uncertainty value required')
    try:value=float(value)
    except OverflowError as exc:raise ValueError('finite uncertainty required') from exc
    if not math.isfinite(value) or (not signed and value<0):raise ValueError('invalid uncertainty value')
    return value


def _values(values):
    if values is None:return None
    if type(values) is not tuple or not values:raise ValueError('nonempty immutable uncertainty vector required')
    return tuple(_number(x) for x in values)


def _canonical(data):return json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False)


def _keys(data,names):
    if type(data) is not dict or set(data)!=set(names):raise ValueError('unsupported admission archive fields')


def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate admission JSON key')
        result[key]=value
    return result


def _constant(value):raise ValueError('nonfinite admission JSON value: '+value)


def _match(actual,expected):
    if _canonical(actual)!=_canonical(expected):raise ValueError('inconsistent admission schema/source/summary')


class _Archive:
    def to_json(self):return _canonical(self.to_dict())
    @property
    def contract_hash(self):return hashlib.sha256(self.to_json().encode('utf-8')).hexdigest()
    @classmethod
    def from_json(cls,text):
        if type(text) is not str:raise ValueError('admission JSON text required')
        return cls.from_dict(json.loads(text,object_pairs_hook=_unique,parse_constant=_constant))


@dataclass(frozen=True)
class AcquisitionLineage(_Archive):
    study_id: str
    specimen_id: str | None
    acquisition_id: str | None
    acquisition_roots: tuple[str,...]
    observation_groups: tuple[str,...]
    observation_ids: tuple[str,...]
    observation_artifact_sha256: tuple[str,...]
    data_kind: str
    source_locator: str
    source_doi: str | None = None
    transformations: tuple[str,...] = ()
    shared_systematic_ids: tuple[str,...] = ()
    redistribution_terms: str | None = None
    temperature_K: float | None = None
    temperature_standard_uncertainty_K: float | None = None
    material_description: str | None = None
    specimen_characterization: str | None = None
    measurement_geometry: str | None = None
    instrument_and_calibration: str | None = None

    def __post_init__(self):
        _text(self.study_id,'study_id');_text(self.source_locator,'source_locator')
        for name in ('specimen_id','acquisition_id','source_doi','redistribution_terms','material_description','specimen_characterization','measurement_geometry','instrument_and_calibration'):_optional(getattr(self,name),name)
        for name in ('temperature_K','temperature_standard_uncertainty_K'):
            value=getattr(self,name)
            if value is not None:
                value=_number(value)
                if name=='temperature_K' and value==0:raise ValueError('positive temperature required')
                object.__setattr__(self,name,value)
        for name in ('acquisition_roots','observation_groups','observation_ids','observation_artifact_sha256','transformations','shared_systematic_ids'):_labels(getattr(self,name),name)
        for digest in self.observation_artifact_sha256:
            if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('lowercase observation SHA-256 required')
        if self.data_kind not in ('raw_measured','instrument_processed','model_derived','digitized','synthetic'):raise ValueError('unsupported data kind')
        if self.data_kind in ('instrument_processed','model_derived','digitized') and not self.transformations:raise ValueError('derived observations require transformation history')

    def to_dict(self):
        raw=asdict(self)
        for key,value in raw.items():
            if type(value) is tuple:raw[key]=list(value)
        return {'schema_version':'acquisition-lineage-v1',**raw}

    @classmethod
    def from_dict(cls,data):
        names=tuple(cls.__dataclass_fields__);_keys(data,('schema_version',*names));raw={k:data[k] for k in names}
        for key in ('acquisition_roots','observation_groups','observation_ids','observation_artifact_sha256','transformations','shared_systematic_ids'):
            if type(raw[key]) is not list:raise ValueError('archived lineage list required')
            raw[key]=tuple(raw[key])
        obj=cls(**raw);_match(data,obj.to_dict());return obj


@dataclass(frozen=True)
class UncertaintyBudget(_Archive):
    observable_unit: str | None
    independent_unit: str | None
    observable_origin: str
    standard_uncertainty: tuple[float,...] | None
    independent_policy: str
    independent_standard_uncertainty: tuple[float,...] | None
    correlation_policy: str
    covariance: tuple[tuple[float,...],...] | None
    sources: tuple[str,...]
    notes: str
    missing_components: tuple[str,...] = ()
    legacy_uncertainty_role: str = 'unknown'

    def __post_init__(self):
        _optional(self.observable_unit,'observable_unit');_optional(self.independent_unit,'independent_unit');_text(self.notes,'notes')
        _labels(self.sources,'uncertainty sources');_labels(self.missing_components,'missing uncertainty components')
        if self.observable_origin not in ('reported','estimated','mixed','unknown'):raise ValueError('unsupported uncertainty origin')
        if self.independent_policy not in ('provided','reviewed_negligible','unresolved'):raise ValueError('unsupported independent uncertainty policy')
        if self.correlation_policy not in ('independent','covariance_supplied','unresolved'):raise ValueError('unsupported correlation policy')
        if self.legacy_uncertainty_role not in ('standard','converted','absent','unknown'):raise ValueError('unsupported legacy uncertainty interpretation')
        object.__setattr__(self,'standard_uncertainty',_values(self.standard_uncertainty))
        object.__setattr__(self,'independent_standard_uncertainty',_values(self.independent_standard_uncertainty))
        if (self.independent_policy=='provided')!=(self.independent_standard_uncertainty is not None):raise ValueError('independent vector/policy mismatch')
        if self.independent_standard_uncertainty is not None and self.independent_unit is None:raise ValueError('independent uncertainty unit required')
        if (self.correlation_policy=='covariance_supplied')!=(self.covariance is not None):raise ValueError('covariance/policy mismatch')
        if (self.standard_uncertainty is not None or self.covariance is not None) and self.observable_unit is None:raise ValueError('observable uncertainty unit required')
        if self.covariance is not None:
            if type(self.covariance) is not tuple or not self.covariance or any(type(row) is not tuple for row in self.covariance):raise ValueError('immutable covariance matrix required')
            matrix=tuple(tuple(_number(x,signed=True) for x in row) for row in self.covariance);n=len(matrix)
            if any(len(row)!=n for row in matrix):raise ValueError('square covariance required')
            if self.standard_uncertainty is None or len(self.standard_uncertainty)!=n:raise ValueError('covariance needs matching standard uncertainties')
            a=np.asarray(matrix);scale=float(np.max(abs(a)))
            scaled=a/scale if scale else a
            if not np.allclose(scaled,scaled.T,rtol=0,atol=1e-12) or np.any(np.diag(a)<0):raise ValueError('symmetric nonnegative-variance covariance required')
            if np.linalg.eigvalsh((scaled+scaled.T)/2).min() < -1e-12*n:raise ValueError('positive-semidefinite covariance required')
            if any(not math.isclose(math.sqrt(matrix[i][i]),self.standard_uncertainty[i],rel_tol=1e-10,abs_tol=0) for i in range(n)):raise ValueError('covariance diagonal/std mismatch')
            object.__setattr__(self,'covariance',matrix)

    def to_dict(self):
        raw=asdict(self)
        for key in ('standard_uncertainty','independent_standard_uncertainty','sources','missing_components'):
            if raw[key] is not None:raw[key]=list(raw[key])
        if raw['covariance'] is not None:raw['covariance']=[list(row) for row in raw['covariance']]
        return {'schema_version':'uncertainty-budget-v1','covariance_unit':None if self.observable_unit is None else '('+self.observable_unit+')^2',**raw}

    @classmethod
    def from_dict(cls,data):
        names=tuple(cls.__dataclass_fields__);_keys(data,('schema_version','covariance_unit',*names));raw={k:data[k] for k in names}
        for key in ('standard_uncertainty','independent_standard_uncertainty','sources','missing_components'):
            if raw[key] is not None:
                if type(raw[key]) is not list:raise ValueError('archived uncertainty list required')
                raw[key]=tuple(raw[key])
        if raw['covariance'] is not None:
            if type(raw['covariance']) is not list or any(type(row) is not list for row in raw['covariance']):raise ValueError('archived covariance lists required')
            raw['covariance']=tuple(tuple(row) for row in raw['covariance'])
        obj=cls(**raw);_match(data,obj.to_dict());return obj


def _dataset_parts(evidence):
    raw=evidence.to_dict()['dataset']
    if raw['dataset_type']=='optical_absorption':return raw,len(raw['wavelength_nm']),'nm','m^-1',raw['absorption_uncertainty_m_inv']
    return raw,len(raw['observable']['values']),raw['independent_variable']['unit'],raw['observable']['unit'],raw['observable']['uncertainty']


@dataclass(frozen=True)
class ExperimentalDataPackage(_Archive):
    name: str
    dataset_evidence: DatasetEvidence
    lineage: AcquisitionLineage
    uncertainty: UncertaintyBudget
    applicability: str
    reviewer: str | None = None
    review_notes: str | None = None
    acquisition_gaps: tuple[str,...] = ()

    def __post_init__(self):
        _text(self.name,'package name');_text(self.applicability,'applicability')
        if type(self.dataset_evidence) is not DatasetEvidence or type(self.lineage) is not AcquisitionLineage or type(self.uncertainty) is not UncertaintyBudget:raise ValueError('typed dataset/lineage/budget required')
        if (self.reviewer is None)!=(self.review_notes is None):raise ValueError('reviewer and review notes required together')
        _optional(self.reviewer,'reviewer');_optional(self.review_notes,'review notes');_labels(self.acquisition_gaps,'acquisition gaps')
        raw,n,xunit,yunit,legacy=_dataset_parts(self.dataset_evidence);budget=self.uncertainty
        if budget.observable_unit!=yunit or budget.independent_unit!=xunit:raise ValueError('budget must use canonical dataset units')
        if self.lineage.observation_ids and len(self.lineage.observation_ids)!=n:raise ValueError('one ordered observation identity per dataset row required')
        for values in (budget.standard_uncertainty,budget.independent_standard_uncertainty):
            if values is not None and len(values)!=n:raise ValueError('uncertainty vector length mismatch')
        if budget.covariance is not None and len(budget.covariance)!=n:raise ValueError('covariance dimension mismatch')
        if budget.legacy_uncertainty_role=='absent' and legacy is not None:raise ValueError('legacy uncertainty is present')
        if budget.legacy_uncertainty_role in ('standard','converted') and (legacy is None or budget.standard_uncertainty is None):raise ValueError('legacy interpretation requires both source and standard uncertainty')
        if budget.legacy_uncertainty_role=='standard' and not np.allclose(legacy,budget.standard_uncertainty,rtol=1e-12,atol=0):raise ValueError('legacy standard uncertainty mismatch')
        if budget.legacy_uncertainty_role=='converted' and not self.lineage.transformations:raise ValueError('uncertainty conversion must be recorded')
        temperature=raw['metadata']['temperature_K']
        if temperature is not None and self.lineage.temperature_K!=temperature:raise ValueError('dataset/lineage temperature mismatch')
        doi=raw['metadata']['doi']
        if doi is not None and self.lineage.source_doi!=doi:raise ValueError('dataset/lineage DOI mismatch')
        if (self.dataset_evidence.origin is DataOrigin.SYNTHETIC)!=(self.lineage.data_kind=='synthetic'):raise ValueError('declared origin/data-kind mismatch')

    @property
    def summary(self):
        raw,n,_,_,legacy=_dataset_parts(self.dataset_evidence);lineage=self.lineage;budget=self.uncertainty;gaps=list(self.acquisition_gaps)
        if self.reviewer is None:gaps.append('review_not_recorded')
        for name in ('specimen_id','acquisition_id','redistribution_terms','temperature_K','temperature_standard_uncertainty_K','material_description','specimen_characterization','measurement_geometry','instrument_and_calibration'):
            if getattr(lineage,name) is None:gaps.append(name+'_missing')
        for name in ('acquisition_roots','observation_groups','observation_ids','observation_artifact_sha256'):
            if not getattr(lineage,name):gaps.append(name+'_missing')
        if budget.observable_unit is None or budget.independent_unit is None:gaps.append('canonical_units_unresolved')
        if budget.standard_uncertainty is None or any(x==0 for x in budget.standard_uncertainty):gaps.append('positive_observable_standard_uncertainty_missing')
        if budget.observable_origin=='unknown' or not budget.sources:gaps.append('uncertainty_origin_or_source_unresolved')
        if budget.independent_policy=='unresolved':gaps.append('independent_axis_uncertainty_unresolved')
        if budget.correlation_policy=='unresolved':gaps.append('correlation_unresolved')
        if legacy is not None and budget.legacy_uncertainty_role=='unknown':gaps.append('legacy_uncertainty_interpretation_unresolved')
        gaps.extend(budget.missing_components)
        negative=[]
        if self.dataset_evidence.origin is not DataOrigin.MEASURED:negative.append('synthetic_not_experimental')
        return {'status':'not_admissible' if negative else 'not_assessable' if gaps else 'eligible_for_independent_study',
            'dataset_id':raw['metadata']['dataset_id'],'dataset_hash':self.dataset_evidence.dataset_hash,
            'n_observations':n,'negative_reasons':negative,'acquisition_gaps':sorted(set(gaps)),
            'uncertainty_origin':budget.observable_origin,'scientific_status':'declared_evidence_not_calibrated'}

    def to_dict(self):return {'schema_version':'experimental-data-package-v1','name':self.name,
        'dataset_evidence':self.dataset_evidence.to_dict(),'lineage':self.lineage.to_dict(),'uncertainty':self.uncertainty.to_dict(),
        'applicability':self.applicability,'reviewer':self.reviewer,'review_notes':self.review_notes,
        'acquisition_gaps':list(self.acquisition_gaps),'summary':self.summary}

    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','name','dataset_evidence','lineage','uncertainty','applicability','reviewer','review_notes','acquisition_gaps','summary'))
        if type(data['acquisition_gaps']) is not list:raise ValueError('archived acquisition gap list required')
        obj=cls(data['name'],DatasetEvidence.from_json(_canonical(data['dataset_evidence'])),AcquisitionLineage.from_dict(data['lineage']),UncertaintyBudget.from_dict(data['uncertainty']),data['applicability'],data['reviewer'],data['review_notes'],tuple(data['acquisition_gaps']))
        _match(data,obj.to_dict());return obj


@dataclass(frozen=True)
class IndependentStudySplit(_Archive):
    name: str
    training: tuple[ExperimentalDataPackage,...]
    validation: tuple[ExperimentalDataPackage,...]
    reviewer: str | None = None
    review_notes: str | None = None
    shared_systematics_assessment: str | None = None

    def __post_init__(self):
        _text(self.name,'split name')
        for items in (self.training,self.validation):
            if type(items) is not tuple or not items or any(type(x) is not ExperimentalDataPackage for x in items):raise ValueError('nonempty typed immutable dataset groups required')
        if (self.reviewer is None)!=(self.review_notes is None):raise ValueError('reviewer/notes mismatch')
        for name in ('reviewer','review_notes','shared_systematics_assessment'):_optional(getattr(self,name),name)

    @property
    def summary(self):
        bad=[];gaps=[];all_packages=self.training+self.validation
        if self.reviewer is None:gaps.append('split_review_missing')
        identities=[x.summary['dataset_id'] for x in all_packages]
        if len(set(identities))!=len(identities):bad.append('duplicate_dataset_identity')
        for package in all_packages:
            if package.summary['status']=='not_admissible':bad.append('package_not_admissible:'+package.name)
            elif package.summary['status']=='not_assessable':gaps.append('package_not_assessable:'+package.name)
        shared=set()
        for train in self.training:
            for valid in self.validation:
                if train.dataset_evidence.dataset_hash==valid.dataset_evidence.dataset_hash:bad.append('same_dataset_hash')
                a,b=train.lineage,valid.lineage
                for field in ('specimen_id','acquisition_id'):
                    if getattr(a,field) is not None and getattr(a,field)==getattr(b,field):bad.append('shared_'+field)
                for field in ('acquisition_roots','observation_groups','observation_ids','observation_artifact_sha256'):
                    if set(getattr(a,field))&set(getattr(b,field)):bad.append('overlapping_'+field)
                shared.update(set(a.shared_systematic_ids)&set(b.shared_systematic_ids))
        if shared and self.shared_systematics_assessment is None:gaps.append('shared_systematics_review_missing')
        status='not_admissible' if bad else 'not_assessable' if gaps else 'eligible_for_independent_study'
        return {'status':status,'policy':'disjoint_specimen_acquisition_and_observation_lineage-v1',
            'training_count':len(self.training),'validation_count':len(self.validation),
            'negative_reasons':sorted(set(bad)),'acquisition_gaps':sorted(set(gaps)),
            'shared_systematic_ids':sorted(shared),'statistical_independence_certified':False,
            'scientific_status':'declared_evidence_not_calibrated'}

    def to_dict(self):return {'schema_version':'independent-study-split-v1','name':self.name,
        'training':[x.to_dict() for x in self.training],'validation':[x.to_dict() for x in self.validation],
        'reviewer':self.reviewer,'review_notes':self.review_notes,'shared_systematics_assessment':self.shared_systematics_assessment,'summary':self.summary}

    @classmethod
    def from_dict(cls,data):
        _keys(data,('schema_version','name','training','validation','reviewer','review_notes','shared_systematics_assessment','summary'))
        if type(data['training']) is not list or type(data['validation']) is not list:raise ValueError('archived dataset group lists required')
        obj=cls(data['name'],tuple(ExperimentalDataPackage.from_dict(x) for x in data['training']),tuple(ExperimentalDataPackage.from_dict(x) for x in data['validation']),data['reviewer'],data['review_notes'],data['shared_systematics_assessment'])
        _match(data,obj.to_dict());return obj


@dataclass(frozen=True)
class AcquisitionGap(_Archive):
    candidate_id: str
    source_url: str
    missing_evidence: tuple[str,...]
    reason: str
    decision: str = 'pending'
    source_doi: str | None = None

    def __post_init__(self):
        for name in ('candidate_id','source_url','reason'):_text(getattr(self,name),name)
        _optional(self.source_doi,'source_doi');_labels(self.missing_evidence,'missing evidence')
        if not self.missing_evidence:raise ValueError('explicit missing evidence required')
        if self.decision not in ('pending','excluded'):raise ValueError('gap cannot admit or calibrate a candidate')

    def to_dict(self):return {'schema_version':'acquisition-gap-v1',**asdict(self),'missing_evidence':list(self.missing_evidence)}

    @classmethod
    def from_dict(cls,data):
        names=tuple(cls.__dataclass_fields__);_keys(data,('schema_version',*names))
        if type(data['missing_evidence']) is not list:raise ValueError('archived gap list required')
        raw={k:data[k] for k in names};raw['missing_evidence']=tuple(raw['missing_evidence']);obj=cls(**raw);_match(data,obj.to_dict());return obj
