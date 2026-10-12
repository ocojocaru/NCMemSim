# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Synthetic P2 optimizer/reference exercise; not measured-data calibration."""
from pathlib import Path
import argparse,json,hashlib,sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ncmemsim.experimental import ExperimentalDatasetMetadata,OpticalAbsorptionDataset
from ncmemsim.workflows.evidence import DataOrigin,capture_dataset_evidence
from ncmemsim.independent_data import AcquisitionLineage,UncertaintyBudget,ExperimentalDataPackage
from ncmemsim.fitting import FitParameter,FitParameterSet,LeastSquaresConfig
from ncmemsim.materials.optics.near_edge import GeSnNearEdgeParameterSet
from ncmemsim.materials.optics.near_edge_fit import predict_gesn_near_edge_absorption_m_inv
from ncmemsim.independent_optical_fit import OpticalFitSpecification,OpticalTrainingContext,OpticalTrainingFitResult,fit_optical_training

TRUE_PARAMETERS={'direct_prefactor_A':3.9e6,'urbach_energy_eV':.012}


def build_context():
    wavelength=(1505.,1515.,1525.,1540.,1560.,1580.,1600.,1620.)
    truth=GeSnNearEdgeParameterSet(name='P2 synthetic truth',**TRUE_PARAMETERS)
    observed=predict_gesn_near_edge_absorption_m_inv(wavelength,sn_fraction=0.,parameters=truth)
    metadata=ExperimentalDatasetMetadata('p2-synthetic-ge-training','P2 generated direct/Urbach observations; not experimental measurements',temperature_K=300.,notes='Exact synthetic recovery is a software check, not experimental qualification.')
    dataset=OpticalAbsorptionDataset(wavelength,observed,0.,metadata,[1000.]*len(wavelength))
    evidence=capture_dataset_evidence(dataset,origin=DataOrigin.SYNTHETIC,source=metadata.source,applicability='unstrained 300 K bulk-like synthetic reference only')
    lineage=AcquisitionLineage('P2 synthetic reference',None,None,(),('p2/generated-observations',),tuple('p2/row/'+str(i) for i in range(len(wavelength))),(hashlib.sha256(evidence.to_json().encode()).hexdigest(),),'synthetic','existing NCMemSim near-edge equation evaluation',transformations=('predict from fixed synthetic truth',),temperature_K=300.,material_description='synthetic bulk-like pure Ge reference')
    budget=UncertaintyBudget('m^-1','nm','estimated',tuple([1000.]*len(wavelength)),'reviewed_negligible',None,'independent',None,('explicit synthetic constant error scale',),'Synthetic objective weighting only; wavelength coordinates exact by construction.',legacy_uncertainty_role='standard')
    package=ExperimentalDataPackage('P2 synthetic training',evidence,lineage,budget,'software regression only')
    parameters=FitParameterSet((FitParameter('direct_prefactor_A',3.0e6,1.0e6,7.0e6,'m^-1 eV^(1/2)'),FitParameter('urbach_energy_eV',.009,.005,.02,'eV')))
    spec=OpticalFitSpecification('P2 declared synthetic fit',parameters,LeastSquaresConfig(),1500.,1650.,'bulk','Synthetic unstrained 300 K reference; fixed gap, no indirect/excitonic response; no validation data used to choose bounds.')
    return OpticalTrainingContext(package,spec,'synthetic_diagnostic')


def run_reference():return fit_optical_training(build_context())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--input',type=Path);args=parser.parse_args()
    result=OpticalTrainingFitResult.from_json(args.input.read_text(encoding='utf-8')) if args.input else run_reference()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result.to_dict(),indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'result_hash':result.contract_hash,'summary':result.summary}))
