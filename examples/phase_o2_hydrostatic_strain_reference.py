# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Independent decimal check of hydrostatic strain-induced optical gap shifts."""
from pathlib import Path
from decimal import Decimal
import argparse,json,sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ncmemsim._version import __version__
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.temperature import GapKind
from ncmemsim.materials.structural import StructuralEvidence,HydrostaticStrainDomain,HydrostaticStrainGapShiftProfile
from ncmemsim.materials.structural_strain import evaluate_hydrostatic_strain_gap_shift,HydrostaticStrainGapShiftResult

SCOPE='Synthetic hydrostatic strain-induced transition-gap shifts; coefficients/domain ASSUMED, not qualified Ge strain data. No shear, splitting, band-offset/barrier or optical-amplitude change.'

def run_reference():
    e=StructuralEvidence('O2 synthetic coefficient/domain','explicit diagnostic fixture',ParameterStatus.ASSUMED,SCOPE)
    baseline=StructuralEvidence('Retained nominal bulk-Ge optical gaps','GeSnOpticalParameterSet at 300 K',ParameterStatus.DERIVED,'Inherited .7985/.664 eV baselines; not strained-NC qualification')
    d=HydrostaticStrainDomain('Ge',300,300,-.01,.01,e);cases=[]
    for kind,gap,slope in ((GapKind.GAMMA,.7985,-1.),(GapKind.L,.664,-.5)):
        p=HydrostaticStrainGapShiftProfile('O2-'+kind.name,'FG1',kind,d,slope,e)
        for strain in (-.01,0.,.01):
            result=evaluate_hydrostatic_strain_gap_shift(p,unstrained_gap_eV=gap,unstrained_gap_evidence=baseline,temperature_K=300,trace_strain=strain)
            expected_shift=Decimal(str(slope))*Decimal(str(strain));expected_gap=Decimal(str(gap))+expected_shift
            cases.append({'result':result.to_dict(),'independent_decimal_shift_eV':str(expected_shift),
                'independent_decimal_gap_eV':str(expected_gap)})
    failures=[]
    for name,strain,temp,gap in (('strain_domain',.02,300,.7985),('temperature_domain',0,350,.7985),('nonpositive_gap',.01,300,.001)):
        p=HydrostaticStrainGapShiftProfile('O2-deliberate-failure','FG1',GapKind.GAMMA,d,-1,e)
        request={'profile':p.to_dict(),'unstrained_gap_eV':gap,'unstrained_gap_evidence':baseline.to_dict(),'temperature_K':temp,'trace_strain':strain}
        try:evaluate_hydrostatic_strain_gap_shift(p,unstrained_gap_eV=gap,unstrained_gap_evidence=baseline,temperature_K=temp,trace_strain=strain)
        except ValueError as exc:failures.append({'case':name,'request':request,'status':'failed','error_type':'ValueError','message':str(exc)})
        else:raise AssertionError('expected failure did not occur')
    raw={'schema_version':'o2-hydrostatic-strain-reference-v1','software_version':__version__,
        'implementation_baseline':'625d5d1ef4f50076dc1283ca1fd7d255dfad1427','scope':SCOPE,'cases':cases,'failures':failures,
        'case_counts':{'attempted':9,'completed':6,'failed':3}}
    raw['reference_hash']=canonical_hash(raw);validate_reference(raw);return raw

def validate_reference(raw):
    import math
    if raw['reference_hash']!=canonical_hash({k:v for k,v in raw.items() if k!='reference_hash'}):raise ValueError('reference hash mismatch')
    if raw['case_counts']!={'attempted':9,'completed':6,'failed':3} or len(raw['cases'])!=6 or len(raw['failures'])!=3:raise ValueError('attempt population mismatch')
    seen=set()
    for case in raw['cases']:
        result=HydrostaticStrainGapShiftResult.from_dict(case['result'])
        seen.add((result.profile.gap_kind.value,result.trace_strain))
        expected=Decimal(str(result.profile.gap_deformation_potential_eV_per_trace))*Decimal(str(result.trace_strain))
        gap=Decimal(str(result.unstrained_gap_eV))+expected
        if Decimal(case['independent_decimal_shift_eV'])!=expected or Decimal(case['independent_decimal_gap_eV'])!=gap:raise ValueError('independent decimal projection differs')
        if not math.isclose(result.gap_shift_eV,float(expected),rel_tol=1e-14,abs_tol=1e-15) or not math.isclose(result.shifted_gap_eV,float(gap),rel_tol=1e-14,abs_tol=1e-15):raise ValueError('linear reference failed')
        if result.trace_strain==0 and result.shifted_gap_eV!=result.unstrained_gap_eV:raise ValueError('zero-strain identity failed')
    if seen!={(k.value,s) for k in (GapKind.GAMMA,GapKind.L) for s in (-.01,0.,.01)}:raise ValueError('incomplete/duplicate reference grid')
    if {x['case'] for x in raw['failures']}!={'strain_domain','temperature_domain','nonpositive_gap'}:raise ValueError('failure population mismatch')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    raw=run_reference();args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(raw,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'case_counts':raw['case_counts'],'reference_hash':raw['reference_hash']}))
