# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Independent Decimal reference for kinetic spherical confinement; synthetic masses."""
from pathlib import Path
from decimal import Decimal,localcontext
import argparse,json,math,sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ncmemsim._version import __version__
from ncmemsim.hashing import canonical_hash
from ncmemsim.constants import PLANCK_J_S,ELECTRON_MASS_KG,ELEMENTARY_CHARGE_C
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.temperature import GapKind
from ncmemsim.materials.structural import StructuralEvidence,ConfinementDomain,SphericalConfinementProfile
from ncmemsim.materials.structural_confinement import evaluate_spherical_kinetic_confinement_gap_shift,SphericalKineticConfinementGapShiftResult

SCOPE='Synthetic kinetic-only spherical infinite-barrier EMA diagnostic; masses/domain ASSUMED, not qualified embedded-Ge NC data. No Coulomb, polarization, finite barrier, strain or transport change.'

def independent_energies(profile,radius):
    with localcontext() as ctx:
        ctx.prec=60
        h=Decimal(str(PLANCK_J_S));m0=Decimal(str(ELECTRON_MASS_KG));q=Decimal(str(ELEMENTARY_CHARGE_C));r=Decimal(str(radius))
        return tuple(h*h/(Decimal(8)*m0*Decimal(str(m))*r*r*q) for m in (profile.electron_mass_m0,profile.hole_mass_m0))

def run_reference():
    e=StructuralEvidence('O3 synthetic masses/domain','explicit diagnostic fixtures',ParameterStatus.ASSUMED,SCOPE)
    baseline=StructuralEvidence('retained nominal Ge optical gaps','300 K GeSnOpticalParameterSet',ParameterStatus.DERIVED,'Inherited .7985/.664 eV baselines, not confined-NC qualification')
    domain=ConfinementDomain('Ge',300,300,2e-9,1e-8,e);cases=[]
    for kind,gap,mass in ((GapKind.GAMMA,.7985,.2),(GapKind.L,.664,.3)):
        p=SphericalConfinementProfile('O3-'+kind.name,'FG1',kind,'effective_scalar',domain,mass,.4,e,e,e)
        for radius in (2e-9,4e-9,8e-9):
            r=evaluate_spherical_kinetic_confinement_gap_shift(p,unconfined_gap_eV=gap,unconfined_gap_evidence=baseline,temperature_K=300,radius_m=radius)
            independent=independent_energies(p,radius)
            cases.append({'result':r.to_dict(),'independent_decimal_electron_eV':str(independent[0]),'independent_decimal_hole_eV':str(independent[1])})
    failures=[]
    for name,radius,temp in (('radius_domain',1e-9,300),('temperature_domain',4e-9,350)):
        p=SphericalConfinementProfile('O3-failure','FG1',GapKind.GAMMA,'effective_scalar',domain,.2,.4,e,e,e)
        request={'profile':p.to_dict(),'unconfined_gap_eV':.7985,'unconfined_gap_evidence':baseline.to_dict(),'temperature_K':temp,'radius_m':radius}
        try:evaluate_spherical_kinetic_confinement_gap_shift(p,unconfined_gap_eV=.7985,unconfined_gap_evidence=baseline,temperature_K=temp,radius_m=radius)
        except ValueError as exc:failures.append({'case':name,'request':request,'status':'failed','error_type':'ValueError','message':str(exc)})
        else:raise AssertionError('expected domain failure')
    raw={'schema_version':'o3-kinetic-confinement-reference-v1','software_version':__version__,'implementation_baseline':'eb88e2ef5a76381669141158c96d76ab03606da4',
        'scope':SCOPE,'cases':cases,'failures':failures,'case_counts':{'attempted':8,'completed':6,'failed':2}}
    raw['reference_hash']=canonical_hash(raw);validate_reference(raw);return raw

def validate_reference(raw):
    if raw['reference_hash']!=canonical_hash({k:v for k,v in raw.items() if k!='reference_hash'}):raise ValueError('reference hash mismatch')
    if raw['case_counts']!={'attempted':8,'completed':6,'failed':2} or len(raw['cases'])!=6 or len(raw['failures'])!=2:raise ValueError('attempted population mismatch')
    groups={}
    for row in raw['cases']:
        result=SphericalKineticConfinementGapShiftResult.from_dict(row['result']);expected=independent_energies(result.profile,result.radius_m)
        for value,decimal,key in zip((result.electron_confinement_energy_eV,result.hole_confinement_energy_eV),expected,
            ('independent_decimal_electron_eV','independent_decimal_hole_eV')):
            if Decimal(row[key])!=decimal or not math.isclose(value,float(decimal),rel_tol=1e-14,abs_tol=0):raise ValueError('independent energy reference failed')
        groups.setdefault(result.profile.gap_kind.value,[]).append((result.radius_m,result.kinetic_gap_shift_eV))
    if set(groups)!={GapKind.GAMMA.value,GapKind.L.value}:raise ValueError('incomplete valley grid')
    for rows in groups.values():
        rows.sort()
        if [x[0] for x in rows]!=[2e-9,4e-9,8e-9] or any(not math.isclose(a[1]/b[1],4,rel_tol=1e-14) for a,b in zip(rows,rows[1:])):raise ValueError('inverse-square scaling failed')
    if {x['case'] for x in raw['failures']}!={'radius_domain','temperature_domain'}:raise ValueError('failure grid mismatch')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    raw=run_reference();args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(raw,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'case_counts':raw['case_counts'],'reference_hash':raw['reference_hash']}))
