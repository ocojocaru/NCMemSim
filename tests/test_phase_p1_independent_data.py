# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Mechanical declaration fixtures only; none are admitted experimental data."""
from dataclasses import replace,FrozenInstanceError
import hashlib,json
import numpy as np
import pytest
from ncmemsim.experimental import OpticalAbsorptionDataset,ExperimentalDatasetMetadata
from ncmemsim.workflows.evidence import DatasetEvidence,DataOrigin,capture_dataset_evidence
from ncmemsim.independent_data import AcquisitionLineage,UncertaintyBudget,ExperimentalDataPackage,IndependentStudySplit,AcquisitionGap


def package(name='training',*,origin=DataOrigin.MEASURED):
    meta=ExperimentalDatasetMetadata(name,'P1 invented unit-test declaration; not a real measurement',temperature_K=300.)
    dataset=OpticalAbsorptionDataset([1500.,1600.],[1.,2.],0.,meta,[.1,.2])
    evidence=capture_dataset_evidence(dataset,origin=origin,source=meta.source,applicability='unit test only')
    lineage=AcquisitionLineage(name+'/study',name+'/specimen',name+'/acquisition',(name+'/root',),(name+'/curve',),(name+'/1',name+'/2'),(hashlib.sha256(name.encode()).hexdigest(),),'synthetic' if origin is DataOrigin.SYNTHETIC else 'raw_measured','invented declaration fixture',redistribution_terms='unit test only',temperature_K=300.,temperature_standard_uncertainty_K=1.,material_description='Ge fixture',specimen_characterization='bulk fixture',measurement_geometry='test geometry',instrument_and_calibration='invented test instrument')
    budget=UncertaintyBudget('m^-1','nm','reported',(.1,.2),'provided',(.5,.5),'independent',None,('invented uncertainty fixture',),'Mechanical standard-uncertainty fixture, not reported measurements',legacy_uncertainty_role='standard')
    return ExperimentalDataPackage(name,evidence,lineage,budget,'unit test declarations only','unit-test reviewer','mechanical test, no physical admission')


@pytest.fixture
def split():return IndependentStudySplit('unit-only declared split',(package(),),(package('validation'),),'unit-test reviewer','not a real independent experiment')


def test_complete_declarations_do_not_calibrate(split):
    assert split.summary['status']=='eligible_for_independent_study'
    assert split.summary['scientific_status']=='declared_evidence_not_calibrated'
    assert split.summary['statistical_independence_certified'] is False
    assert IndependentStudySplit.from_json(split.to_json())==split
    assert 'calibrated' not in split.to_dict()


@pytest.mark.parametrize('field',['specimen_id','acquisition_id','temperature_standard_uncertainty_K','redistribution_terms','material_description','specimen_characterization','measurement_geometry','instrument_and_calibration'])
def test_missing_lineage_is_not_assessable(field):
    p=package();p=replace(p,lineage=replace(p.lineage,**{field:None}))
    assert p.summary['status']=='not_assessable'
    assert field+'_missing' in p.summary['acquisition_gaps']
    assert ExperimentalDataPackage.from_json(p.to_json())==p


def test_temperature_missing_without_legacy_temperature():
    p=package();raw=p.dataset_evidence.to_dict();raw['dataset']['metadata']['temperature_K']=None
    from ncmemsim.hashing import canonical_hash
    raw['dataset_hash']=canonical_hash(raw['dataset']);raw.pop('evidence_hash')
    evidence=DatasetEvidence(json.dumps(raw))
    p=replace(p,dataset_evidence=evidence,lineage=replace(p.lineage,temperature_K=None))
    assert 'temperature_K_missing' in p.summary['acquisition_gaps']


@pytest.mark.parametrize('field',['acquisition_roots','observation_groups','observation_ids','observation_artifact_sha256'])
def test_empty_lineage_is_not_assessable(field):
    p=package();p=replace(p,lineage=replace(p.lineage,**{field:()}))
    assert p.summary['status']=='not_assessable'


@pytest.mark.parametrize('field',['specimen_id','acquisition_id','acquisition_roots','observation_groups','observation_ids','observation_artifact_sha256'])
def test_overlap_rejected_even_with_distinct_dataset_hashes(split,field):
    a,b=split.training[0],split.validation[0]
    assert a.dataset_evidence.dataset_hash!=b.dataset_evidence.dataset_hash
    b=replace(b,lineage=replace(b.lineage,**{field:getattr(a.lineage,field)}))
    result=replace(split,validation=(b,))
    assert result.summary['status']=='not_admissible'
    assert any(field in x for x in result.summary['negative_reasons'])
    assert IndependentStudySplit.from_json(result.to_json())==result


def test_identical_source_and_duplicate_identity_are_negative_results(split):
    result=replace(split,validation=split.training)
    assert result.summary['status']=='not_admissible'
    assert 'same_dataset_hash' in result.summary['negative_reasons']
    assert 'duplicate_dataset_identity' in result.summary['negative_reasons']


def test_transformed_copy_preserves_root_and_is_rejected(split):
    a,b=split.training[0],split.validation[0]
    b=replace(b,lineage=replace(b.lineage,data_kind='model_derived',transformations=('rescale unit-test observations',),acquisition_roots=a.lineage.acquisition_roots))
    assert replace(split,validation=(b,)).summary['status']=='not_admissible'


def test_synthetic_status_is_never_admissible(split):
    p=package('synthetic',origin=DataOrigin.SYNTHETIC)
    assert p.summary['status']=='not_admissible'
    assert replace(split,validation=(p,)).summary['status']=='not_admissible'


def test_shared_systematic_requires_review_and_never_certifies_independent_errors(split):
    a=replace(split.training[0],lineage=replace(split.training[0].lineage,shared_systematic_ids=('shared instrument calibration',)))
    b=replace(split.validation[0],lineage=replace(split.validation[0].lineage,shared_systematic_ids=('shared instrument calibration',)))
    s=replace(split,training=(a,),validation=(b,))
    assert s.summary['status']=='not_assessable'
    s=replace(s,shared_systematics_assessment='explicit conditional review in a unit fixture')
    assert s.summary['status']=='eligible_for_independent_study'
    assert s.summary['statistical_independence_certified'] is False


def test_missing_review_and_explicit_gaps(split):
    p=replace(package('validation'),reviewer=None,review_notes=None,acquisition_gaps=('instrument uncertainty budget missing',))
    assert p.summary['status']=='not_assessable'
    assert replace(split,validation=(p,)).summary['status']=='not_assessable'
    assert replace(split,reviewer=None,review_notes=None).summary['status']=='not_assessable'


@pytest.mark.parametrize('kwargs',[{'observable_origin':'unknown'},{'standard_uncertainty':None,'legacy_uncertainty_role':'unknown'},{'correlation_policy':'unresolved'},{'independent_policy':'unresolved','independent_standard_uncertainty':None},{'missing_components':('shared systematic unbounded',)},{'legacy_uncertainty_role':'unknown'}])
def test_unresolved_uncertainty_is_not_assessable(kwargs):
    p=package();p=replace(p,uncertainty=replace(p.uncertainty,**kwargs))
    assert p.summary['status']=='not_assessable'


def test_covariance_is_checked_and_preserved():
    p=package();budget=replace(p.uncertainty,correlation_policy='covariance_supplied',covariance=((.01,.01),(.01,.04)))
    p=replace(p,uncertainty=budget)
    assert p.summary['status']=='eligible_for_independent_study'
    assert UncertaintyBudget.from_json(budget.to_json())==budget
    assert budget.to_dict()['covariance_unit']=='(m^-1)^2'


@pytest.mark.parametrize('matrix',[((.01,.02),(.01,.04)),((.01,.03),(.03,.04)),((-.01,0.),(0.,.04)),((.02,0.),(0.,.04)),((.01,),(.04,))])
def test_bad_covariance_rejected(matrix):
    with pytest.raises(ValueError):replace(package().uncertainty,correlation_policy='covariance_supplied',covariance=matrix)


@pytest.mark.parametrize('kwargs',[{'standard_uncertainty':(True,.2)},{'standard_uncertainty':(float('nan'),.2)},{'standard_uncertainty':(-.1,.2)},{'standard_uncertainty':[.1,.2]},{'independent_policy':'provided','independent_standard_uncertainty':None},{'correlation_policy':'independent','covariance':((.01,0.),(0.,.04))},{'observable_origin':'CALIBRATED'}])
def test_invalid_uncertainty_contract_rejected(kwargs):
    with pytest.raises(ValueError):replace(package().uncertainty,**kwargs)


@pytest.mark.parametrize('kwargs',[{'observation_ids':('duplicate','duplicate')},{'observation_artifact_sha256':('BAD',)},{'acquisition_roots':['mutable']},{'data_kind':'digitized','transformations':()},{'temperature_K':0},{'temperature_standard_uncertainty_K':True}])
def test_invalid_lineage_contract_rejected(kwargs):
    with pytest.raises(ValueError):replace(package().lineage,**kwargs)


@pytest.mark.parametrize('fault',['units','length','legacy','temperature','doi','origin'])
def test_source_budget_identity_mismatch_rejected(fault):
    p=package()
    with pytest.raises(ValueError):
        if fault=='units':replace(p,uncertainty=replace(p.uncertainty,observable_unit='cm^-1'))
        elif fault=='length':replace(p,lineage=replace(p.lineage,observation_ids=('one',)))
        elif fault=='legacy':replace(p,uncertainty=replace(p.uncertainty,standard_uncertainty=(.3,.4)))
        elif fault=='temperature':replace(p,lineage=replace(p.lineage,temperature_K=301.))
        elif fault=='doi':
            raw=p.dataset_evidence.to_dict();raw['dataset']['metadata']['doi']='10.0000/unit-test'
            from ncmemsim.hashing import canonical_hash
            raw['dataset_hash']=canonical_hash(raw['dataset']);raw.pop('evidence_hash');replace(p,dataset_evidence=DatasetEvidence(json.dumps(raw)))
        else:replace(p,lineage=replace(p.lineage,data_kind='synthetic'))


@pytest.mark.parametrize('fault',['extra','schema','summary','nested_summary','unit','source_hash'])
def test_coherent_archive_changes_do_not_bypass_readers(split,fault):
    raw=split.to_dict()
    if fault=='extra':raw['unreviewed']=True
    elif fault=='schema':raw['schema_version']='independent-study-split-v2'
    elif fault=='summary':raw['summary']['status']='CALIBRATED'
    elif fault=='nested_summary':raw['validation'][0]['summary']['status']='CALIBRATED'
    elif fault=='unit':raw['validation'][0]['uncertainty']['covariance_unit']='V^2'
    else:raw['validation'][0]['dataset_evidence']['dataset_hash']='0'*64
    with pytest.raises(ValueError):IndependentStudySplit.from_dict(raw)


def test_duplicate_nonfinite_json_and_immutability(split):
    with pytest.raises(ValueError):IndependentStudySplit.from_json(split.to_json().replace('{','{"name":"duplicate",',1))
    with pytest.raises(ValueError):IndependentStudySplit.from_json(split.to_json().replace('300.0','NaN',1))
    with pytest.raises(FrozenInstanceError):split.name='changed'
    raw=split.to_dict();raw['validation'][0]['lineage']['acquisition_roots'].append('changed')
    assert 'changed' not in split.validation[0].lineage.acquisition_roots


def test_restoration_uses_no_solver_optical_model_or_rng(split,monkeypatch):
    from ncmemsim.simulator import Simulator
    from ncmemsim.materials.optics.models import CompositeGeSnAbsorptionModel
    def forbidden(*args,**kwargs):raise AssertionError('no replay')
    monkeypatch.setattr(Simulator,'relax_voltage',forbidden)
    monkeypatch.setattr(CompositeGeSnAbsorptionModel,'evaluate',forbidden)
    monkeypatch.setattr(np.random,'default_rng',forbidden)
    assert IndependentStudySplit.from_json(split.to_json())==split


def test_acquisition_gap_has_no_admission_escape():
    gap=AcquisitionGap('candidate','https://example.invalid',('measurement table',),'unit test pending')
    assert AcquisitionGap.from_json(gap.to_json())==gap
    for kwargs in ({'missing_evidence':()},{'decision':'admitted'},{'missing_evidence':['mutable']}):
        with pytest.raises(ValueError):replace(gap,**kwargs)

def test_singular_psd_covariance_is_retained_not_an_identifiability_claim():
    p=package();budget=replace(p.uncertainty,correlation_policy='covariance_supplied',covariance=((.01,.02),(.02,.04)))
    p=replace(p,uncertainty=budget)
    assert ExperimentalDataPackage.from_json(p.to_json())==p
    assert p.summary['scientific_status']=='declared_evidence_not_calibrated'


def test_missing_legacy_units_remain_not_assessable():
    from ncmemsim.experimental import DeviceObservableDataset
    meta=ExperimentalDatasetMetadata('unknown-units','P1 unit fixture',temperature_K=300.)
    data=DeviceObservableDataset('time',None,[1.,2.],'read shift',None,[.1,.2],meta)
    evidence=capture_dataset_evidence(data,origin=DataOrigin.MEASURED,source=meta.source,applicability='unit fixture')
    budget=UncertaintyBudget(None,None,'unknown',None,'unresolved',None,'unresolved',None,(),'Unspecified units and uncertainty retained',legacy_uncertainty_role='absent')
    p=ExperimentalDataPackage('unknown units',evidence,package().lineage,budget,'unit fixture')
    assert p.summary['status']=='not_assessable'
    assert 'canonical_units_unresolved' in p.summary['acquisition_gaps']


def test_reviewed_repository_split_and_candidate_gaps():
    from pathlib import Path
    from scripts.validate_independent_data_review import validate
    result=validate(Path(__file__).resolve().parents[1])
    assert result['legacy_split_status']=='not_admissible'
    assert result['admitted_independent_datasets']==0 and result['new_calibrated_parameters']==0
    assert result['candidate_gap_count']==4


@pytest.mark.parametrize('fault',['admitted_count','source_hash','extra'])
def test_review_cannot_be_promoted_or_rehashed_by_declaration(monkeypatch,fault):
    from pathlib import Path
    from scripts import validate_independent_data_review as gate
    root=Path(__file__).resolve().parents[1];read=gate._read
    raw=read(root/'docs/independent_data_review.json')
    if fault=='admitted_count':raw['new_admitted_independent_dataset_count']=1
    elif fault=='source_hash':raw['source_sha256']['ncmemsim/independent_data.py']='0'*64
    else:raw['unreviewed']=True
    monkeypatch.setattr(gate,'_read',lambda path:raw if path.name=='independent_data_review.json' else read(path))
    with pytest.raises(ValueError,match='review drift'):gate.validate(root)
