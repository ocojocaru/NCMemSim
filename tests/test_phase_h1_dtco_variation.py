from dataclasses import FrozenInstanceError, replace
import math
import pytest
from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (BindingScope, ParameterBinding, UniformVariation,
    TruncatedNormalVariation, VariationDefinition, VariationKind, VariationProvenance)
from ncmemsim.hashing import canonical_hash
from ncmemsim.program_protocol import ProgramPulseReadProtocol


def definition(path=("temperature_K",), scope=BindingScope.DEVICE, unit="K", lower=290, upper=310):
    return VariationDefinition("variation", ParameterBinding(scope,path),
        UniformVariation(lower,upper), unit, VariationKind.PARAMETER_ESTIMATION,
        VariationProvenance("Assumed test interval", "Reference device"))


@pytest.mark.parametrize("law", [UniformVariation, lambda a,b: TruncatedNormalVariation(a,b,0,1)])
@pytest.mark.parametrize("bounds", [(1,1),(2,1),(math.nan,1),(0,math.inf),(-math.inf,1)])
def test_invalid_bounds(law,bounds):
    with pytest.raises(ValueError): law(*bounds)


@pytest.mark.parametrize("value", [True,"1",None,{},[]])
def test_nonnumeric(value):
    with pytest.raises(TypeError): UniformVariation(value,2)


@pytest.mark.parametrize("std", [0,-1,math.inf,math.nan])
def test_invalid_std(std):
    with pytest.raises(ValueError): TruncatedNormalVariation(0,1,0,std)


def test_underlying_mean_outside_interval_and_finite():
    assert TruncatedNormalVariation(0,1,3,2).mean == 3
    with pytest.raises(ValueError): TruncatedNormalVariation(0,1,math.inf,1)
    with pytest.raises(ValueError): UniformVariation(10**1000,10**1001)


CONTRACTS = [
    (BindingScope.DEVICE,("gate_work_function_eV",),"eV",-1,1),
    (BindingScope.DEVICE,("substrate_doping_m3",),"m^-3",1,2),
    (BindingScope.DEVICE,("temperature_K",),"K",1,2),
    *[(BindingScope.DEVICE,("layers","FG1",field),unit,lo,hi) for field,unit,lo,hi in
      [("thickness_nm","nm",1,2),("nc_diameter_nm","nm",1,2),
       ("nc_volume_fraction","1",0,1),("electrically_active_fraction","1",0,1)]],
    (BindingScope.DEVICE,("layers","FG1","nc_material","sn_fraction"),"1",0,1),
    *[(BindingScope.OPERATING,path,unit,lo,hi) for path,unit,lo,hi in
      [(("program","voltage_V"),"V",-1,1),(("read","voltage_V"),"V",-1,1),
       (("program","time_s"),"s",1,2),(("program","internal_dt_s"),"s",1,2),
       (("optical","wavelength_nm"),"nm",1,2),(("optical","power_density_W_m2"),"W/m^2",1,2)]]]


@pytest.mark.parametrize("scope,path,unit,lo,hi", CONTRACTS)
def test_all_canonical_contracts(scope,path,unit,lo,hi):
    item=definition(path,scope,unit,lo,hi)
    assert item.unit == unit
    with pytest.raises(ValueError): replace(item,unit="incorrect")


@pytest.mark.parametrize("scope,path,unit,lo,hi", [c for c in CONTRACTS if c[3] > 0])
def test_positive_binding_bounds(scope,path,unit,lo,hi):
    with pytest.raises(ValueError): definition(path,scope,unit,0,hi)


@pytest.mark.parametrize("field", ["nc_volume_fraction","electrically_active_fraction","sn_fraction"])
@pytest.mark.parametrize("bounds", [(-0.1,1),(0,1.1)])
def test_fraction_ranges(field,bounds):
    path=("layers","FG1",field) if field != "sn_fraction" else ("layers","FG1","nc_material",field)
    with pytest.raises(ValueError): definition(path,unit="1",lower=bounds[0],upper=bounds[1])


@pytest.mark.parametrize("scope,path", [(BindingScope.MODEL,("temperature_K",)),
    (BindingScope.DEVICE,("layers","FG1","grid_points")),
    (BindingScope.DEVICE,("unknown",)),(BindingScope.OPERATING,("unknown",))])
def test_excluded_bindings(scope,path):
    with pytest.raises(ValueError): definition(path,scope)


@pytest.mark.parametrize("field", ["source","applicability","notes"])
@pytest.mark.parametrize("value", ["", " text", "text ", "\t", None])
def test_provenance_contract(field,value):
    if field == "notes" and value is None: return
    kwargs=dict(source="source",applicability="scope",notes="notes");kwargs[field]=value
    with pytest.raises(ValueError): VariationProvenance(**kwargs)


def test_identity_immutability_and_no_aliases():
    item=definition(); data=item.to_dict(); data["distribution"]["lower"]=0
    assert item.distribution.lower == 290
    assert item.definition_hash == definition(lower=290.0).definition_hash
    for changed in [replace(item,name="changed"),replace(item,kind=VariationKind.FABRICATION),
                    replace(item,provenance=VariationProvenance("different","scope"))]:
        assert changed.definition_hash != item.definition_hash
    with pytest.raises(FrozenInstanceError): item.unit="V"
    with pytest.raises(TypeError): replace(item,kind="fabrication")
    with pytest.raises(TypeError): replace(item,distribution={})
    with pytest.raises(TypeError): replace(item,provenance=None)
    with pytest.raises(ValueError): replace(item,name=" variation ")


def device():
    return DeviceBuilder.v2(n_fgs=1,control_sio2_nm=20,fg_thickness_nm=12,
        tunnel_sio2_nm=8,nc_diameter_nm=5,nc_volume_fraction=0.6,active_fraction=0.22)


def test_context_validation_isolated_and_missing_layer():
    nominal=device(); before=canonical_hash(nominal.to_dict())
    definition().validate_context(nominal)
    assert canonical_hash(nominal.to_dict()) == before
    with pytest.raises(ValueError): definition(("layers","missing","thickness_nm"),unit="nm",lower=1,upper=2).validate_context(nominal)


def test_operating_context_requires_protocol_and_optical_support():
    nominal=device(); protocol=ProgramPulseReadProtocol(5,1e-6)
    item=definition(("program","time_s"),BindingScope.OPERATING,"s",1e-7,2e-6)
    before=protocol.to_dict(); item.validate_context(nominal,protocol)
    assert protocol.to_dict() == before
    with pytest.raises(ValueError): item.validate_context(nominal)
    optical=definition(("optical","wavelength_nm"),BindingScope.OPERATING,"nm",400,600)
    with pytest.raises(ValueError): optical.validate_context(nominal,protocol)
