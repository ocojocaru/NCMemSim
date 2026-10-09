# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""P1 declaration/data-gap review; never fit or promote calibration status."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ncmemsim.experimental import ExperimentalDatasetMetadata
from ncmemsim.io import load_optical_absorption_csv
from ncmemsim.workflows.evidence import DataOrigin,capture_dataset_evidence
from ncmemsim.independent_data import AcquisitionLineage,UncertaintyBudget,ExperimentalDataPackage,IndependentStudySplit,AcquisitionGap
from ncmemsim.hashing import canonical_hash


def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate review JSON key')
        result[key]=value
    return result


def _constant(value):raise ValueError('nonfinite review JSON: '+value)


def _read(path):return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=_unique,parse_constant=_constant)


def _hash(path):return hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()


def build_review(root):
    base=root/'data/reference/tran2016';metadata=_read(base/'tran2016_sampleA_fig6a_metadata.json')
    workflow=_read(base/'tran2016_sampleA_fig6a_workflow_result.json');p0=_read(root/'docs/independent_calibration_audit.json')
    if metadata['split_policy']['independent_experiment'] is not False:raise ValueError('legacy same-curve limitation changed')
    if workflow['calibration_result']['calibrated'] is not False:raise ValueError('legacy negative qualification changed')
    packages=[];doi=metadata['source']['doi'];group=doi+'/figure6a'
    for role in ('fit','validation'):
        meta=ExperimentalDatasetMetadata(metadata['dataset_family']+'-'+role,metadata['source']['citation'],doi=doi,sample_id='A',temperature_description='room temperature',notes='Same published curve; digitized model-derived experimental observations, not independent acquisition.')
        dataset=load_optical_absorption_csv(base/f'tran2016_sampleA_fig6a_{role}.csv',sn_fraction=0.,metadata=meta)
        evidence=capture_dataset_evidence(dataset,origin=DataOrigin.MEASURED,source=meta.source,applicability='legacy bulk/film Ge digitized holdout only')
        lineage=AcquisitionLineage(doi,doi+'/sample-A',None,(),(group,),tuple(group+'/'+pid for pid in metadata['split_policy'][role+'_point_ids']),(_hash(base/'tran2016_sampleA_fig6a_near_edge_all.csv'),),'digitized','Figure 6(a); repository metadata/digitization audit',source_doi=doi,transformations=tuple(metadata['data_lineage']),shared_systematic_ids=(group+'/optical-extraction',group+'/digitization-axis-map'),material_description='Repository metadata: pure Ge film',specimen_characterization='Repository metadata: Sample A, nominal 300 nm film; no new specimen verification')
        budget=UncertaintyBudget('m^-1','nm','estimated',None,'unresolved',None,'unresolved',None,('repository 5% digitization estimate',),'Legacy uncertainty is a digitization estimate, not a reported experimental standard deviation; no standard-error conversion is declared.',missing_components=('experimental_measurement_error_budget','wavelength_uncertainty','source_covariance_review'),legacy_uncertainty_role='unknown')
        packages.append(ExperimentalDataPackage('Tran2016 '+role,evidence,lineage,budget,'legacy disjoint holdout; not independent experimental qualification','P1 repository audit','Identity/source inspection only; incomplete acquisition and uncertainty evidence retained.',('exact_measurement_temperature_missing','redistribution_terms_not_reviewed','original_raw_measurements_not_available')))
    split=IndependentStudySplit('Tran2016 same-curve holdout rejection',(packages[0],),(packages[1],),'P1 repository audit','Shared specimen, curve ancestry and observation artifact; hashes alone do not establish independence.')
    gaps=[]
    for candidate in p0['literature_candidates']:
        excluded=candidate['id']=='zhao2020_ge_nk'
        missing=('near_edge_spectral_coverage',) if excluded else ('numerical_observations_or_audited_digitization','specimen_acquisition_genealogy','uncertainty_budget_and_units','redistribution_terms_review')
        gaps.append(AcquisitionGap(candidate['id'],candidate['url'],missing,candidate['admission'],'excluded' if excluded else 'pending',candidate['doi']))
    return {'schema_version':'independent-data-review-v1','status':'P1_contracts_reviewed_no_new_independent_data_admitted',
        'implementation_baseline':'fab21a926798e01e940921517acf0fda10006f36',
        'source_sha256':{name:_hash(root/name) for name in ('ncmemsim/independent_data.py','ncmemsim/experimental.py','ncmemsim/io.py','ncmemsim/workflows/evidence.py')},
        'p0_audit_sha256':canonical_hash(p0),
        'legacy_artifact_sha256':{p.relative_to(root).as_posix():_hash(p) for p in sorted(base.iterdir()) if p.is_file()},
        'legacy_split':split.to_dict(),'candidate_gaps':[g.to_dict() for g in gaps],
        'new_admitted_independent_dataset_count':0,'new_calibrated_parameter_count':0,
        'legacy_qualification':{'calibrated':False,'failed_criteria':workflow['calibration_result']['failed_criteria']},
        'scientific_limits':['declared genealogy/reviewer evidence is not measurement authentication','eligible-for-study status is not CALIBRATED or numerical qualification','no new observation acquisition or fitting claimed by this review']}


def validate(root):
    raw=_read(root/'docs/independent_data_review.json')
    if raw!=build_review(root):raise ValueError('independent data/source/review drift')
    split=IndependentStudySplit.from_dict(raw['legacy_split'])
    if split.summary['status']!='not_admissible':raise ValueError('same-curve holdout cannot pass independent study admission')
    for item in raw['candidate_gaps']:AcquisitionGap.from_dict(item)
    if raw['new_admitted_independent_dataset_count'] or raw['new_calibrated_parameter_count']:raise ValueError('P1 has no new admitted or calibrated data')
    return {'status':raw['status'],'legacy_split_status':split.summary['status'],
        'candidate_gap_count':len(raw['candidate_gaps']),'admitted_independent_datasets':0,'new_calibrated_parameters':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-review',action='store_true');args=parser.parse_args()
    if args.write_review:(ROOT/'docs/independent_data_review.json').write_text(json.dumps(build_review(ROOT),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(validate(ROOT),indent=2))
