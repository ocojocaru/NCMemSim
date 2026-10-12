# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""P3 synthetic fixed-parameter holdouts and real Tran2016 admission rejection."""
from pathlib import Path
from dataclasses import replace
import argparse,json,hashlib,sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from examples.phase_p2_optical_training_reference import build_context,TRUE_PARAMETERS
from ncmemsim.experimental import ExperimentalDatasetMetadata,OpticalAbsorptionDataset
from ncmemsim.workflows.evidence import DataOrigin,capture_dataset_evidence
from ncmemsim.independent_data import AcquisitionLineage,UncertaintyBudget,ExperimentalDataPackage,IndependentStudySplit
from ncmemsim.independent_optical_fit import fit_optical_training
from ncmemsim.independent_optical_validation import OpticalHoldoutCriteria,OpticalHoldoutPlan,OpticalHoldoutEvaluation,evaluate_optical_holdout,review_optical_holdout_admission
from ncmemsim.materials.optics.near_edge import GeSnNearEdgeParameterSet
from ncmemsim.materials.optics.near_edge_fit import predict_gesn_near_edge_absorption_m_inv
from ncmemsim.hashing import canonical_hash
from ncmemsim.independent_data import _unique,_constant


def validation_package(name='p3-good',scale=1.):
    wavelengths=(1510.,1530.,1550.,1570.,1590.,1610.)
    truth=GeSnNearEdgeParameterSet(name='P3 synthetic truth',**TRUE_PARAMETERS)
    observed=predict_gesn_near_edge_absorption_m_inv(wavelengths,sn_fraction=0.,parameters=truth)*scale
    metadata=ExperimentalDatasetMetadata(name,'Generated P3 numerical holdout, not real measured data',temperature_K=300.,notes='Synthetic model-only holdout; scale='+str(scale))
    dataset=OpticalAbsorptionDataset(wavelengths,observed,0.,metadata,[1000.]*len(wavelengths))
    evidence=capture_dataset_evidence(dataset,origin=DataOrigin.SYNTHETIC,source=metadata.source,applicability='synthetic 300 K unstrained bulk-like reference')
    lineage=AcquisitionLineage('P3 synthetic source',None,None,(),(name+'/generated-holdout',),tuple(name+'/row/'+str(i) for i in range(len(wavelengths))),(hashlib.sha256(evidence.to_json().encode()).hexdigest(),),'synthetic','existing near-edge equations; synthetic shifted observations',transformations=('predict synthetic truth; multiply by declared scale '+str(scale),),temperature_K=300.,material_description='synthetic bulk-like Ge')
    budget=UncertaintyBudget('m^-1','nm','estimated',tuple([1000.]*len(wavelengths)),'reviewed_negligible',None,'independent',None,('explicit synthetic error scale',),'Synthetic weighting and exact coordinates; no experimental uncertainty claim.',legacy_uncertainty_role='standard')
    return ExperimentalDataPackage(name,evidence,lineage,budget,'mechanical synthetic holdout only')


def setup():
    context=build_context()
    criteria=OpticalHoldoutCriteria(1000.,1.,3.,4)
    plan=OpticalHoldoutPlan('P3 synthetic predeclared plan',context,criteria,'synthetic_diagnostic','Example code declares these diagnostic criteria before fitting and generating holdout observations; not measured-data thresholds.')
    fitted=fit_optical_training(context)
    return plan,fitted


def run_reference():
    plan,fitted=setup();evaluations=[]
    for name,scale in (('p3-good',1.),('p3-shifted',1.25)):
        holdout=validation_package(name,scale)
        split=IndependentStudySplit(name,(plan.training_context.data_package,),(holdout,),reviewer='P3 synthetic-code audit',review_notes='Different generated coordinates/IDs; numerical diagnostic, not independent physical acquisitions.')
        evaluations.append(evaluate_optical_holdout(plan,fitted,split).to_dict())
    root=Path(__file__).resolve().parents[1]
    legacy_raw=json.loads((root/'docs/independent_data_review.json').read_text(encoding='utf-8'))['legacy_split']
    legacy=IndependentStudySplit.from_dict(legacy_raw)
    raw={'schema_version':'p3-holdout-reference-v1','evaluations':evaluations,
        'legacy_split':legacy.to_dict(),'legacy_admission':review_optical_holdout_admission(legacy),
        'scope':'Synthetic pass/negative validation mechanics; real Tran2016 same-curve rejection without fitting or model evaluation; zero new admitted experimental data.'}
    return {**raw,'reference_hash':canonical_hash(raw)}


def restore_reference(raw):
    if set(raw)!={'schema_version','evaluations','legacy_split','legacy_admission','scope','reference_hash'} or raw['schema_version']!='p3-holdout-reference-v1':raise ValueError('unsupported P3 reference')
    if raw['reference_hash']!=canonical_hash({k:v for k,v in raw.items() if k!='reference_hash'}):raise ValueError('reference identity mismatch')
    if type(raw['evaluations']) is not list or len(raw['evaluations'])!=2:raise ValueError('complete pass/negative reference outcomes required')
    outcomes=[OpticalHoldoutEvaluation.from_dict(item).summary['status'] for item in raw['evaluations']]
    if outcomes!=['diagnostic_validation_passed','validation_failed']:raise ValueError('reference outcome population changed')
    legacy=IndependentStudySplit.from_dict(raw['legacy_split'])
    if legacy.summary['status']!='not_admissible':raise ValueError('legacy same-curve limitation changed')
    if raw['legacy_admission']!=review_optical_holdout_admission(legacy):raise ValueError('legacy admission mismatch')
    return raw


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--input',type=Path);args=parser.parse_args()
    raw=restore_reference(json.loads(args.input.read_text(encoding='utf-8'),object_pairs_hook=_unique,parse_constant=_constant)) if args.input else run_reference()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(raw,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'reference_hash':raw['reference_hash'],'outcomes':[x['summary']['status'] for x in raw['evaluations']],'legacy':raw['legacy_admission']['status']}))
