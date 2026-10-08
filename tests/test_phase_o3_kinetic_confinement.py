# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from copy import deepcopy
from decimal import Decimal,localcontext
import math
import pytest
from ncmemsim.constants import PLANCK_J_S,ELECTRON_MASS_KG,ELEMENTARY_CHARGE_C,HBAR_J_S
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.temperature import GapKind
from ncmemsim.materials.structural import StructuralEvidence,ConfinementDomain,SphericalConfinementProfile
from ncmemsim.materials.structural_confinement import SphericalKineticConfinementGapShiftResult,evaluate_spherical_kinetic_confinement_gap_shift

@pytest.fixture
def profile():
    e=StructuralEvidence('synthetic masses','O3 tests',ParameterStatus.ASSUMED,'not material qualified')
    return SphericalConfinementProfile('O3','FG1',GapKind.GAMMA,'effective_scalar',ConfinementDomain('Ge',300,300,2e-9,1e-8,e),.2,.4,e,e,e)

def evaluate(p,*,gap=.7985,radius=4e-9,temperature=300):
    return evaluate_spherical_kinetic_confinement_gap_shift(p,unconfined_gap_eV=gap,unconfined_gap_evidence=p.approximation_evidence,temperature_K=temperature,radius_m=radius)

@pytest.mark.parametrize('radius',[2e-9,4e-9,8e-9])
@pytest.mark.parametrize('kind',[GapKind.GAMMA,GapKind.L])
def test_independent_decimal_energy_components_and_conversion(profile,radius,kind):
    p=replace(profile,gap_kind=kind);r=evaluate(p,radius=radius)
    with localcontext() as ctx:
        ctx.prec=60
        h=Decimal(str(PLANCK_J_S));m0=Decimal(str(ELECTRON_MASS_KG));q=Decimal(str(ELEMENTARY_CHARGE_C));size=Decimal(str(radius))
        expected=[h*h/(Decimal(8)*m0*Decimal(str(m))*size*size*q) for m in (p.electron_mass_m0,p.hole_mass_m0)]
    assert r.electron_confinement_energy_eV==pytest.approx(float(expected[0]),rel=1e-14)
    assert r.hole_confinement_energy_eV==pytest.approx(float(expected[1]),rel=1e-14)
    assert r.kinetic_gap_shift_eV==pytest.approx(sum(map(float,expected)),rel=1e-14)
    assert r.confined_gap_eV==pytest.approx(r.unconfined_gap_eV+r.kinetic_gap_shift_eV)
    legacy_hbar_term=math.pi**2*HBAR_J_S**2/(2*ELECTRON_MASS_KG*radius**2)*(.2**-1+.4**-1)/ELEMENTARY_CHARGE_C
    assert r.kinetic_gap_shift_eV==pytest.approx(legacy_hbar_term,rel=2e-9)

def test_inverse_square_radius_and_factor_four_diameter_mistake(profile):
    diameter=8e-9;correct=evaluate(profile,radius=diameter/2);wrong=evaluate(profile,radius=diameter)
    assert correct.kinetic_gap_shift_eV/wrong.kinetic_gap_shift_eV==pytest.approx(4,rel=1e-14)
    a=evaluate(profile,radius=2e-9);b=evaluate(profile,radius=4e-9);c=evaluate(profile,radius=8e-9)
    assert a.kinetic_gap_shift_eV>b.kinetic_gap_shift_eV>c.kinetic_gap_shift_eV>0

def test_inverse_mass_sensitivity_is_independent_per_carrier(profile):
    a=evaluate(profile);b=evaluate(replace(profile,electron_mass_m0=.4))
    assert b.electron_confinement_energy_eV==pytest.approx(a.electron_confinement_energy_eV/2)
    assert b.hole_confinement_energy_eV==a.hole_confinement_energy_eV

@pytest.mark.parametrize('kwargs',[{'gap':0},{'gap':-1},{'gap':True},{'gap':float('nan')},{'radius':0},{'radius':-1},
    {'radius':True},{'radius':float('inf')},{'radius':1e-9},{'radius':1},{'temperature':350},{'temperature':True}])
def test_invalid_or_undeclared_inputs_rejected(profile,kwargs):
    with pytest.raises(ValueError):evaluate(profile,**kwargs)

def test_extreme_numeric_limits_and_large_radius_formal_identity(profile):
    e=profile.domain.evidence
    tiny=replace(profile,domain=ConfinementDomain('Ge',300,300,5e-324,1e-8,e))
    with pytest.raises(ValueError):evaluate(tiny,radius=5e-324)
    huge=replace(profile,domain=ConfinementDomain('Ge',300,300,2e-9,1e308,e))
    with pytest.raises(ValueError):evaluate(huge,radius=1e308)
    # Explicit assumed extended diagnostic domain; no physical large-R extrapolation claim.
    large=evaluate(replace(profile,domain=ConfinementDomain('Ge',300,300,2e-9,1e4,e)),radius=1e4)
    assert large.kinetic_gap_shift_eV>0 and large.confined_gap_eV==large.unconfined_gap_eV
    # Exponent scaling avoids R^2 underflow where the final energies are representable.
    stable=replace(profile,domain=ConfinementDomain('Ge',300,300,1e-200,1e-200,e),electron_mass_m0=1e200,hole_mass_m0=1e200)
    assert math.isfinite(evaluate(stable,radius=1e-200).kinetic_gap_shift_eV)

def test_roundtrip_identity_and_no_input_mutation(profile):
    before=deepcopy(profile.to_dict());r=evaluate(profile)
    assert SphericalKineticConfinementGapShiftResult.from_json(r.to_json())==r
    assert profile.to_dict()==before
    assert evaluate(profile,radius=8e-9).contract_hash!=r.contract_hash

@pytest.mark.parametrize('fault',['electron','hole','sum','gap','radius','mass','hash','unit','coordinate','constants','extra','schema'])
def test_strict_reader_recomputes_law_and_rejects_mixed_projection(profile,fault):
    raw=evaluate(profile).to_dict()
    keys={'electron':'electron_confinement_energy_eV','hole':'hole_confinement_energy_eV','sum':'kinetic_gap_shift_eV','gap':'confined_gap_eV'}
    if fault in keys:raw[keys[fault]]*=2
    elif fault=='radius':raw['radius_m']*=2
    elif fault=='mass':raw['profile']['electron_mass_m0']*=2
    elif fault=='hash':raw['profile_hash']='0'*64
    elif fault=='unit':raw['mass_unit']='kg'
    elif fault=='coordinate':raw['size_coordinate']='diameter'
    elif fault=='constants':raw['constants']['electron_mass_kg']*=2
    elif fault=='extra':raw['coulomb_energy_eV']=-1
    else:raw['schema_version']='unknown'
    with pytest.raises(ValueError):SphericalKineticConfinementGapShiftResult.from_dict(raw)

def test_legacy_mass_barriers_charging_and_optics_remain_distinct(profile,monkeypatch):
    from ncmemsim.materials import make_ge
    from ncmemsim.materials.optics.models import CompositeGeSnAbsorptionModel
    from ncmemsim.kinetics import OccupancyEngine
    from ncmemsim.tunneling import TunnelingEngine
    material=make_ge();before=deepcopy(material.to_dict());engine=OccupancyEngine(TunnelingEngine());charging=engine.charging_energy_J(8e-9)
    def forbidden(*args,**kwargs):raise AssertionError('no optical evaluator')
    monkeypatch.setattr(CompositeGeSnAbsorptionModel,'evaluate',forbidden)
    r=evaluate(profile)
    assert SphericalKineticConfinementGapShiftResult.from_dict(r.to_dict())==r
    assert material.to_dict()==before and engine.charging_energy_J(8e-9)==charging

def test_reference_attempts_and_independent_values():
    from examples.phase_o3_kinetic_confinement_reference import run_reference,validate_reference
    from ncmemsim.hashing import canonical_hash
    raw=run_reference();assert raw['case_counts']=={'attempted':8,'completed':6,'failed':2}
    raw['cases'][0]['independent_decimal_electron_eV']='9';raw['reference_hash']=canonical_hash({k:v for k,v in raw.items() if k!='reference_hash'})
    with pytest.raises(ValueError):validate_reference(raw)
