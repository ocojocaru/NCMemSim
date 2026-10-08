# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
from dataclasses import FrozenInstanceError,replace
import pytest
from ncmemsim.materials.provenance import ParameterStatus as Status
from ncmemsim.materials.temperature import GapKind
from ncmemsim.materials.structural import (StructuralEvidence,HydrostaticStrainDomain,ConfinementDomain,
    HydrostaticStrainGapShiftProfile,SphericalConfinementProfile)

@pytest.fixture
def evidence():return StructuralEvidence('synthetic diagnostic','O1 test',Status.ASSUMED,'not material qualified')

@pytest.fixture
def profiles(evidence):
    strain=HydrostaticStrainDomain('Ge',300,300,-.01,.01,evidence)
    size=ConfinementDomain('Ge',300,300,2e-9,1e-8,evidence)
    return (HydrostaticStrainGapShiftProfile('strain','FG1',GapKind.GAMMA,strain,-1,evidence),
        SphericalConfinementProfile('size','FG1',GapKind.L,'effective_scalar',size,.3,.4,evidence,evidence,evidence))

def test_independent_profiles_and_no_implicit_evaluation(profiles):
    a,b=profiles
    assert a.gap_kind is GapKind.GAMMA and b.gap_kind is GapKind.L
    assert not hasattr(a,'evaluate') and not hasattr(b,'evaluate')
    assert a.to_dict()['coefficient_semantics']=='optical_transition_gap_derivative'
    assert b.to_dict()['interaction_terms']=='kinetic_only'
    with pytest.raises(FrozenInstanceError):a.layer_name='other'

@pytest.mark.parametrize('index',[0,1])
def test_strict_roundtrip_hash_and_owned_payload(profiles,index):
    p=profiles[index];restored=type(p).from_json(p.to_json())
    assert restored==p and restored.contract_hash==p.contract_hash
    assert replace(p,layer_name='FG2').contract_hash!=p.contract_hash
    raw=p.to_dict();raw['domain']['evidence']['notes']='caller mutation'
    assert p.domain.evidence.notes=='not material qualified'

@pytest.mark.parametrize('name',['coefficient_evidence','domain'])
def test_hydrostatic_profile_requires_typed_sources(profiles,name):
    with pytest.raises(ValueError):replace(profiles[0],**{name:None})

@pytest.mark.parametrize('value',[True,'1',float('nan'),float('inf'),10**400])
def test_coefficient_is_finite_signed_number(profiles,value):
    with pytest.raises(ValueError):replace(profiles[0],gap_deformation_potential_eV_per_trace=value)
    assert replace(profiles[0],gap_deformation_potential_eV_per_trace=0).gap_deformation_potential_eV_per_trace==0

@pytest.mark.parametrize('field',['electron_mass_m0','hole_mass_m0'])
@pytest.mark.parametrize('value',[0,-1,True,'1',float('nan'),float('inf')])
def test_masses_explicit_positive_and_finite(profiles,field,value):
    with pytest.raises(ValueError):replace(profiles[1],**{field:value})

@pytest.mark.parametrize('index',[0,1])
def test_substrate_gap_and_string_target_rejected(profiles,index):
    with pytest.raises(ValueError):replace(profiles[index],gap_kind=GapKind.SUBSTRATE)
    with pytest.raises(ValueError):replace(profiles[index],gap_kind='optical_gamma_gap')

@pytest.mark.parametrize('index',[0,1])
def test_other_materials_and_bad_temperature_domains_rejected(profiles,index):
    d=profiles[index].domain
    for changes in ({'material':'GeSn'},{'material':'Si'},{'min_temperature_K':0},{'min_temperature_K':301}):
        with pytest.raises(ValueError):replace(d,**changes)

def test_zero_anchor_radius_order_and_point_bounds(profiles):
    a,b=profiles
    with pytest.raises(ValueError):replace(a.domain,min_trace_strain=.001)
    with pytest.raises(ValueError):replace(b.domain,min_radius_m=0)
    with pytest.raises(ValueError):replace(b.domain,max_radius_m=1e-9)
    a.domain.validate_point(temperature_K=300,trace_strain=-.01)
    b.domain.validate_point(temperature_K=300,radius_m=2e-9)
    with pytest.raises(ValueError):a.domain.validate_point(temperature_K=300,trace_strain=.011)
    with pytest.raises(ValueError):a.domain.validate_point(temperature_K=True,trace_strain=0)
    with pytest.raises(ValueError):b.domain.validate_point(temperature_K=350,radius_m=3e-9)
    with pytest.raises(ValueError):b.domain.validate_point(temperature_K=300,radius_m=1)

@pytest.mark.parametrize('status',[Status.CALIBRATED,'assumed',None])
def test_calibration_or_untyped_provenance_not_inferred(evidence,status):
    with pytest.raises(ValueError):replace(evidence,status=status)

def test_uncertainty_pair_and_parameter_units(evidence,profiles):
    with pytest.raises(ValueError):replace(evidence,reported_uncertainty=.1)
    with pytest.raises(ValueError):replace(evidence,reported_uncertainty=-.1,uncertainty_unit='m0')
    uncertain=replace(evidence,reported_uncertainty=.1,uncertainty_unit='m0')
    with pytest.raises(ValueError):replace(profiles[0],coefficient_evidence=uncertain)
    assert replace(profiles[1],electron_mass_evidence=uncertain).electron_mass_evidence==uncertain
    with pytest.raises(ValueError):replace(profiles[1],hole_mass_evidence=replace(uncertain,uncertainty_unit='kg'))

@pytest.mark.parametrize('index,field,value',[(0,'coefficient_unit','eV_per_percent'),(0,'coefficient_semantics','conduction_band_offset'),
    (0,'law_id','shear_tensor'),(1,'mass_unit','kg'),(1,'geometry','cylinder'),(1,'barrier_model','finite'),
    (1,'mass_basis','anisotropic_tensor'),(1,'interaction_terms','kinetic_plus_Coulomb'),(1,'hole_branch','unknown')])
def test_other_physics_units_or_geometry_cannot_relabel_archive(profiles,index,field,value):
    p=profiles[index];raw=p.to_dict();raw[field]=value
    with pytest.raises(ValueError):type(p).from_dict(raw)

@pytest.mark.parametrize('index',[0,1])
def test_nested_unknown_schema_fields_and_coordinate_units_rejected(profiles,index):
    p=profiles[index];raw=p.to_dict();raw['domain']['unknown']=True
    with pytest.raises(ValueError):type(p).from_dict(raw)
    raw=p.to_dict();raw['domain']['strain_unit' if index==0 else 'size_unit']='percent' if index==0 else 'nm'
    with pytest.raises(ValueError):type(p).from_dict(raw)
    raw=p.to_dict();raw['schema_version']='future'
    with pytest.raises(ValueError):type(p).from_dict(raw)

def test_duplicate_nonfinite_json_and_model_preset_inference_rejected(profiles):
    p=profiles[0]
    with pytest.raises(ValueError,match='duplicate'):type(p).from_json(p.to_json().replace('{','{"name":"forged",',1))
    with pytest.raises(ValueError,match='nonfinite'):type(p).from_json(p.to_json().replace('-1.0','NaN'))
    with pytest.raises(TypeError):SphericalConfinementProfile(name='missing',layer_name='FG1')


def test_parameter_review_is_explicit_synthetic_not_physical_default():
    from pathlib import Path
    from scripts.validate_structural_parameters import validate
    assert validate(Path(__file__).resolve().parents[1])['qualified_physical_presets']==0


@pytest.mark.parametrize('fault',['physical_claim','value','duplicate'])
def test_parameter_review_cannot_silently_change_assumptions(tmp_path,fault):
    import json
    from scripts.validate_structural_parameters import build_review,validate
    raw=build_review()
    if fault=='physical_claim':raw['shipped_physical_presets']=['Ge qualified default']
    elif fault=='value':raw['synthetic_diagnostic_profiles']['hydrostatic_gamma']['gap_deformation_potential_eV_per_trace']=-10
    text=json.dumps(raw)
    if fault=='duplicate':text=text.replace('{','{"status":"calibrated",',1)
    (tmp_path/'docs').mkdir();(tmp_path/'docs/structural_parameters_review.json').write_text(text,encoding='utf-8')
    with pytest.raises(ValueError):validate(tmp_path)
