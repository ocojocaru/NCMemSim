# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from decimal import Decimal
from copy import deepcopy
import pytest
from ncmemsim.materials.provenance import ParameterStatus
from ncmemsim.materials.temperature import GapKind
from ncmemsim.materials.structural import StructuralEvidence,HydrostaticStrainDomain,HydrostaticStrainGapShiftProfile
from ncmemsim.materials.structural_strain import HydrostaticStrainGapShiftResult,evaluate_hydrostatic_strain_gap_shift

@pytest.fixture
def profile():
    e=StructuralEvidence('synthetic','O2 tests',ParameterStatus.ASSUMED,'not material qualified')
    return HydrostaticStrainGapShiftProfile('O2','FG1',GapKind.GAMMA,HydrostaticStrainDomain('Ge',300,300,-.01,.01,e),-1,e)

def evaluate(p,*,gap=.7985,strain=.01,temperature=300):
    return evaluate_hydrostatic_strain_gap_shift(p,unstrained_gap_eV=gap,unstrained_gap_evidence=p.coefficient_evidence,
        temperature_K=temperature,trace_strain=strain)

@pytest.mark.parametrize('kind,gap',[(GapKind.GAMMA,.7985),(GapKind.L,.664)])
@pytest.mark.parametrize('coefficient',[-1.,.75,0.])
@pytest.mark.parametrize('strain',[-.01,0.,.01])
def test_independent_signed_linear_law_and_zero_identity(profile,kind,gap,coefficient,strain):
    p=replace(profile,gap_kind=kind,gap_deformation_potential_eV_per_trace=coefficient)
    r=evaluate(p,gap=gap,strain=strain)
    shift=Decimal(str(coefficient))*Decimal(str(strain));expected=Decimal(str(gap))+shift
    assert r.gap_shift_eV==pytest.approx(float(shift),rel=1e-14,abs=1e-15)
    assert r.shifted_gap_eV==pytest.approx(float(expected),rel=1e-14,abs=1e-15)
    if strain==0 or coefficient==0:assert r.shifted_gap_eV==gap

def test_trace_is_not_one_diagonal_component_or_percent(profile):
    diagonal=.001
    r=evaluate(profile,strain=3*diagonal)
    assert r.gap_shift_eV==pytest.approx(-.003)
    assert r.gap_shift_eV!=pytest.approx(-diagonal)
    with pytest.raises(ValueError):evaluate(profile,strain=1)  # 1 percent is .01 trace, not 1.

@pytest.mark.parametrize('kwargs',[{'gap':0},{'gap':-1},{'gap':True},{'gap':'0.8'},{'gap':float('inf')},
    {'strain':True},{'strain':float('nan')},{'strain':.02},{'temperature':350}])
def test_invalid_or_outside_domain_requests_fail(profile,kwargs):
    with pytest.raises(ValueError):evaluate(profile,**kwargs)

def test_nonphysical_gap_overflow_and_underflow_rejected(profile):
    with pytest.raises(ValueError):evaluate(profile,gap=.001)
    huge=replace(profile,domain=replace(profile.domain,min_trace_strain=-2,max_trace_strain=2),gap_deformation_potential_eV_per_trace=1e308)
    with pytest.raises(ValueError):evaluate(huge,strain=2)
    with pytest.raises(ValueError):evaluate(huge,gap=1e308,strain=1)
    tiny=replace(profile,gap_deformation_potential_eV_per_trace=1e-308)
    with pytest.raises(ValueError):evaluate(tiny,strain=5e-324)

def test_owned_inputs_hash_and_strict_roundtrip(profile):
    before=deepcopy(profile.to_dict());r=evaluate(profile)
    assert profile.to_dict()==before
    assert HydrostaticStrainGapShiftResult.from_json(r.to_json())==r
    assert evaluate(profile,strain=-.01).contract_hash!=r.contract_hash
    raw=r.to_dict();raw['profile']['coefficient_evidence']['notes']='mutated copy'
    assert profile.coefficient_evidence.notes=='not material qualified'

@pytest.mark.parametrize('fault',['shift','gap','profile_hash','profile_coefficient','unit','coordinate','extra','schema'])
def test_reader_rebuilds_shift_and_rejects_partial_mutation(profile,fault):
    raw=evaluate(profile).to_dict()
    if fault=='shift':raw['gap_shift_eV']*=2
    elif fault=='gap':raw['shifted_gap_eV']+=.1
    elif fault=='profile_hash':raw['profile_hash']='0'*64
    elif fault=='profile_coefficient':raw['profile']['gap_deformation_potential_eV_per_trace']=-2
    elif fault=='unit':raw['energy_unit']='J'
    elif fault=='coordinate':raw['strain_coordinate']='diagonal_component'
    elif fault=='extra':raw['barrier_shift_eV']=.1
    else:raw['schema_version']='unknown'
    with pytest.raises(ValueError):HydrostaticStrainGapShiftResult.from_dict(raw)

def test_no_optical_model_or_preset_mutation(profile,monkeypatch):
    from ncmemsim.materials.optics.models import CompositeGeSnAbsorptionModel,GeSnOpticalParameterSet
    from ncmemsim.materials import make_ge
    material=make_ge();before=material.to_dict();parameters=GeSnOpticalParameterSet()
    def forbidden(*args,**kwargs):raise AssertionError('standalone law must not invoke optical evaluator')
    monkeypatch.setattr(CompositeGeSnAbsorptionModel,'evaluate',forbidden)
    r=evaluate(profile)
    assert HydrostaticStrainGapShiftResult.from_json(r.to_json())==r
    assert material.to_dict()==before and GeSnOpticalParameterSet()==parameters

def test_reference_population_and_independent_decimal_integrity():
    from examples.phase_o2_hydrostatic_strain_reference import run_reference,validate_reference
    from ncmemsim.hashing import canonical_hash
    raw=run_reference();assert raw['case_counts']=={'attempted':9,'completed':6,'failed':3}
    assert all(r['error_type']=='ValueError' for r in raw['failures'])
    raw['cases'][0]['independent_decimal_shift_eV']='99';raw['reference_hash']=canonical_hash({k:v for k,v in raw.items() if k!='reference_hash'})
    with pytest.raises(ValueError):validate_reference(raw)
