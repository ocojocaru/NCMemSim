# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""O1 framework/parameter review: synthetic fixtures only; no physical presets."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ncmemsim.materials.structural import StructuralEvidence,HydrostaticStrainDomain,ConfinementDomain,HydrostaticGapProfile,SphericalConfinementProfile
from ncmemsim.materials.temperature import GapKind
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.spectral_sources import _unique,_constant

def build_review():
    e=StructuralEvidence('O1 synthetic parameter review','explicit diagnostic fixture, not literature data',
        ParameterStatus.ASSUMED,'Arbitrary slopes/masses and applicability bounds; no Ge material qualification')
    sd=HydrostaticStrainDomain('Ge',300,300,-.01,.01,e);cd=ConfinementDomain('Ge',300,300,2e-9,1e-8,e)
    profiles={}
    for kind,slope,mass in ((GapKind.GAMMA,-1.,.2),(GapKind.L,-.5,.3)):
        profiles['hydrostatic_'+kind.name.lower()]=HydrostaticGapProfile('synthetic-'+kind.name,'FG1',kind,sd,slope,e).to_dict()
        profiles['confinement_'+kind.name.lower()]=SphericalConfinementProfile('synthetic-'+kind.name,'FG1',kind,'effective_scalar',cd,mass,.4,e,e,e).to_dict()
    return {'schema_version':'structural-parameters-review-v1','status':'contracts_reviewed_physical_parameters_not_qualified',
        'implementation_baseline':'90d0f7146afb048b9a6d8d0a6df0285245a93356','shipped_physical_presets':[],
        'framework_references':[{'doi':'10.1103/PhysRevB.39.1871','role':'deformation-potential framework, not selected Ge gap coefficients'},
            {'doi':'10.1063/1.447218','role':'effective-mass/interactions framework, not selected Ge confinement masses'}],
        'parameter_policy':'explicit caller parameters; synthetic fixtures do not establish material/domain calibration',
        'pending_physical_review':['Ge Gamma/L optical transition-gap deformation coefficients and sign conventions',
            'valley/hole confinement masses and applicability in embedded Ge nanocrystals',
            'qualified strain, temperature and radius domains; GeSn requires separate evidence'],
        'synthetic_diagnostic_profiles':profiles}

def validate(root):
    raw=json.loads((root/'docs/structural_parameters_review.json').read_text(encoding='utf-8'),object_pairs_hook=_unique,parse_constant=_constant)
    if raw!=build_review():raise ValueError('structural parameter review differs from explicit reviewed diagnostic contracts')
    for name,data in raw['synthetic_diagnostic_profiles'].items():
        cls=HydrostaticGapProfile if name.startswith('hydrostatic') else SphericalConfinementProfile
        if cls.from_dict(data).to_dict()!=data:raise ValueError('structural parameter fixture roundtrip failed')
    return {'status':raw['status'],'synthetic_profiles':4,'qualified_physical_presets':0}

if __name__=='__main__':
    if '--write-review' in sys.argv:(ROOT/'docs/structural_parameters_review.json').write_text(json.dumps(build_review(),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(validate(ROOT),indent=2))
