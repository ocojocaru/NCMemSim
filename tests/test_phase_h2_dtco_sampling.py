from dataclasses import FrozenInstanceError, replace
import json
import math
import numpy as np
import pytest
from ncmemsim.dtco import (BindingScope, ParameterBinding, UniformVariation,
    TruncatedNormalVariation, VariationDefinition, VariationKind, VariationProvenance,
    SamplingSpec, SampleManifest, SamplingError, sample_variations)


def variation(name="voltage", law=None, path=("program","voltage_V")):
    return VariationDefinition(name, ParameterBinding(BindingScope.OPERATING,path),
        law or UniformVariation(-1,2), "V", VariationKind.PARAMETER_ESTIMATION,
        VariationProvenance("Assumed", "Test protocol"))


def spec(count=20):
    return SamplingSpec((variation(),variation("read",TruncatedNormalVariation(-1,2,0,1),
                        ("read","voltage_V"))),seed=123,sample_count=count)


def test_repeat_seed_exact_manifest_order_and_global_rng_untouched():
    np.random.seed(42);before=np.random.get_state()
    first=sample_variations(spec());second=sample_variations(spec())
    after=np.random.get_state()
    assert all(np.array_equal(a,b) for a,b in zip(before,after))
    assert first.to_json()==second.to_json()
    assert first.values != sample_variations(replace(spec(),seed=124)).values
    assert [v.name for v in first.spec.variations]==["voltage","read"]
    assert [r["sample_index"] for r in first.to_dict()["samples"]]==list(range(20))
    reverse=replace(spec(),variations=tuple(reversed(spec().variations)))
    assert reverse.spec_hash != spec().spec_hash
    assert sample_variations(reverse).manifest_hash != first.manifest_hash


def test_restore_never_regenerates(monkeypatch):
    first=sample_variations(spec())
    def forbidden(*args,**kwargs): raise AssertionError("unexpected regeneration")
    monkeypatch.setattr(np.random,"PCG64",forbidden)
    restored=SampleManifest.from_json(first.to_json())
    assert restored.values==first.values
    assert restored.manifest_hash==first.manifest_hash
    with pytest.raises(FrozenInstanceError): restored.values=()
    data=first.to_dict();data["samples"][0]["values"][0]=999
    assert first.values[0][0] != 999


@pytest.mark.parametrize("field,value", [("seed",True),("seed",1.5),("seed",-1),
    ("seed",2**128),("sample_count",0),("sample_count",False),
    ("max_draws_per_value",0),("max_draws_per_value",1.5)])
def test_invalid_spec_numbers(field,value):
    with pytest.raises((ValueError,TypeError)): replace(spec(),**{field:value})


def test_spec_duplicates_and_defensive_snapshot():
    for values in [(),(variation(),variation()),(variation(),variation("other")),("x",)]:
        with pytest.raises(ValueError): SamplingSpec(values,0,1)
    values=[variation()];s=SamplingSpec(values,0,1);values.clear()
    assert len(s.variations)==1


def test_explicit_exhaustion_not_clipped_or_dropped():
    s=SamplingSpec((variation("tail",TruncatedNormalVariation(100,101,0,1)),),123,4,3)
    with pytest.raises(SamplingError) as result: sample_variations(s)
    assert (result.value.sample_index,result.value.variation_name,result.value.attempts)==(0,"tail",3)


def test_distribution_moments_bounds_and_no_endpoint_pileup():
    manifest=sample_variations(spec(20000));values=np.array(manifest.values)
    assert np.all(values >= -1) and np.all(values <= 2)
    assert not np.any(values == -1) and not np.any(values == 2)
    assert abs(values[:,0].mean()-0.5)<0.03
    phi=lambda x: math.exp(-x*x/2)/math.sqrt(2*math.pi)
    cdf=lambda x: (1+math.erf(x/math.sqrt(2)))/2
    expected=(phi(-1)-phi(2))/(cdf(2)-cdf(-1))
    assert abs(values[:,1].mean()-expected)<0.03
    assert abs(np.corrcoef(values.T)[0,1])<0.03


@pytest.mark.parametrize("change", ["sample","count","index","algorithm","schema",
    "hash","runtime","extra","duplicate","nan","bool_schema"])
def test_manifest_rejects_tampering_and_invalid_schema(change):
    data=sample_variations(spec()).to_dict()
    if change=="sample": data["samples"][0]["values"][0]+=0.1
    elif change=="count": data["samples"].pop()
    elif change=="index": data["samples"][0]["sample_index"]=2
    elif change=="algorithm": data["spec"]["algorithm"]="unknown"
    elif change=="schema": data["schema_version"]=2
    elif change=="bool_schema": data["schema_version"]=True
    elif change=="hash": data["manifest_hash"]="0"*64
    elif change=="runtime": data["runtime"]["numpy"]="unknown"
    elif change=="extra": data["extra"]=1
    elif change=="nan": data["samples"][0]["values"][0]=math.nan
    text=json.dumps(data)
    if change=="duplicate": text=text.replace('"schema_version": 1','"schema_version": 1, "schema_version": 1',1)
    with pytest.raises(ValueError): SampleManifest.from_json(text)


def test_wide_uniform_avoids_width_overflow():
    s=SamplingSpec((variation(law=UniformVariation(-1e308,1e308)),),12,100)
    assert all(math.isfinite(r[0]) for r in sample_variations(s).values)


def test_interrupt_propagates(monkeypatch):
    def stop(*args): raise KeyboardInterrupt
    monkeypatch.setattr(np.random,"PCG64",stop)
    with pytest.raises(KeyboardInterrupt): sample_variations(spec())


def test_runtime_and_algorithm_are_part_of_identity():
    first=sample_variations(spec())
    assert first.to_dict()["spec"]["precision"]=="float64"
    assert first.to_dict()["spec"]["dependence"]=="independent"
    runtime=tuple((key,"other" if key=="numpy" else value) for key,value in first.runtime)
    assert replace(first,runtime=runtime).manifest_hash != first.manifest_hash
