from dataclasses import replace
import json
import math
import numpy as np
import pytest
from ncmemsim import DeviceBuilder
from ncmemsim.dtco import (BindingScope, ParameterBinding, UniformVariation,
    VariationDefinition, VariationKind, VariationProvenance, SamplingSpec,
    SampleManifest, sample_variations, propagate_samples, PropagationResult,
    SamplePointResult)
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read
from ncmemsim.simulator import Simulator
from ncmemsim.hashing import canonical_hash
import ncmemsim.dtco.propagation as propagation


def device(): return DeviceBuilder.v2(n_fgs=1,name="h3-reference")


def definition(name,path,scope,unit,lower,upper):
    return VariationDefinition(name,ParameterBinding(scope,path),UniformVariation(lower,upper),
        unit,VariationKind.PARAMETER_ESTIMATION,VariationProvenance("Assumed","Test"))


def manifest(count=4,operating=True):
    variations=[definition("temperature",("temperature_K",),BindingScope.DEVICE,"K",295,305)]
    if operating:
        variations.append(definition("duration",("program","time_s"),BindingScope.OPERATING,"s",1e-7,2e-7))
    return sample_variations(SamplingSpec(tuple(variations),123,count))


def evaluate(candidate,protocol,point):
    return {"temperature":candidate.temperature_K,"duration":None if protocol is None else protocol.programming_time_s,
            "index":point.index}


def run(m=None,callback=evaluate,**kwargs):
    return propagate_samples(m or manifest(),device(),callback,evaluation_id="h3-test-v1",
                             base_protocol=ProgramPulseReadProtocol(5,1e-7),**kwargs)


def test_exact_order_restored_values_and_reproducibility(monkeypatch):
    m=SampleManifest.from_json(manifest().to_json())
    def forbidden(*args): raise AssertionError("resampling")
    monkeypatch.setattr(np.random,"PCG64",forbidden)
    first=run(m);second=run(m)
    assert first.to_json()==second.to_json()
    assert first.success_count==4 and first.failure_count==0
    for i,result in enumerate(first.points):
        assert result.point.index==i
        assert result.point.manifest_hash==m.manifest_hash
        assert tuple(result.point.assignments.values())==m.values[i]
        assert result.output=={"temperature":m.values[i][0],"duration":m.values[i][1],"index":i}


def test_isolation_from_mutating_callback_and_shared_outputs():
    nominal=device(); protocol=ProgramPulseReadProtocol(5,1e-7)
    before=canonical_hash(nominal.to_dict()); output={"nested":[0]}; seen=[]
    def mutate(candidate,p,point):
        assert candidate.metadata.get("mutated") is None
        assert p.program_voltage_V==5
        seen.append(candidate)
        candidate.metadata["mutated"]=True
        object.__setattr__(p,"program_voltage_V",99)
        output["nested"][0]=point.index
        # Even a callback closure changing the caller's baseline cannot alter the frozen study copy.
        nominal.temperature_K=999
        return output
    result=propagate_samples(manifest(),nominal,mutate,evaluation_id="mutation-v1",base_protocol=protocol)
    assert len({id(c) for c in seen})==4
    assert protocol.program_voltage_V==5
    assert before != canonical_hash(nominal.to_dict())  # explicit closure mutation only
    assert result.to_dict()["study"]["nominal"]["device"]["device"]["temperature_K"]==300
    assert [p.output["nested"][0] for p in result.points]==list(range(4))
    result.points[0].output["nested"][0]=999
    assert result.points[0].output["nested"][0]==0


def test_device_only_with_and_without_protocol():
    m=manifest(operating=False)
    result=propagate_samples(m,device(),evaluate,evaluation_id="device-only")
    assert all(p.output["duration"] is None for p in result.points)
    assert run(m).success_count==4


@pytest.mark.parametrize("kind", ["evaluation","serialization","application"])
def test_failures_keep_every_index_continue_and_have_correct_stage(kind,monkeypatch):
    if kind=="application":
        original=propagation.apply_device_bindings
        calls=[]
        def fail_second(*args):
            calls.append(1)
            if len(calls)==2: raise ValueError("candidate validation failed")
            return original(*args)
        monkeypatch.setattr(propagation,"apply_device_bindings",fail_second)
    def callback(candidate,protocol,point):
        if point.index==1:
            if kind=="evaluation": raise RuntimeError("numerical failure")
            if kind=="serialization": return {"bad":math.nan}
        return evaluate(candidate,protocol,point)
    result=run(callback=callback)
    assert result.success_count==3 and result.failure_count==1
    assert [p.point.index for p in result.points]==list(range(4))
    failed=result.points[1]
    assert failed.status=="failed" and failed.failure_stage==kind and failed.output is None
    assert failed.error_type and failed.error_message
    assert result.points[2].status=="success"


@pytest.mark.parametrize("value", [None, [], {"bad":np.array([1])}, {"bad":math.inf}, {1:"bad"}])
def test_nonjson_outputs_are_serialization_failures(value):
    result=run(callback=lambda *args:value)
    assert result.failure_count==4
    assert all(p.failure_stage=="serialization" for p in result.points)


@pytest.mark.parametrize("exception", [KeyboardInterrupt,SystemExit])
def test_interrupts_propagate(exception):
    def stop(*args): raise exception
    with pytest.raises(exception): run(callback=stop)


@pytest.mark.parametrize("case", ["missing_protocol","missing_layer","invalid_id","parameters","invalid_device"])
def test_setup_errors_before_evaluation(case):
    calls=[];m=manifest();nominal=device();p=ProgramPulseReadProtocol(5,1e-7)
    kwargs={"evaluation_id":"setup","base_protocol":p}
    if case=="missing_protocol": kwargs["base_protocol"]=None
    elif case=="missing_layer":
        v=definition("layer",("layers","missing","thickness_nm"),BindingScope.DEVICE,"nm",1,2)
        m=sample_variations(SamplingSpec((v,),123,2))
    elif case=="invalid_id": kwargs["evaluation_id"]=" invalid "
    elif case=="parameters": kwargs["evaluation_parameters"]={"invalid":math.nan}
    elif case=="invalid_device": nominal.temperature_K=-1
    with pytest.raises((ValueError,TypeError)):
        propagate_samples(m,nominal,lambda *args:calls.append(1),**kwargs)
    assert not calls


def test_definition_and_output_identity_and_parameter_snapshot():
    params={"settings":[1]};first=run(evaluation_parameters=params);params["settings"].append(2)
    assert first.to_dict()["study"]["evaluation"]["parameters"]=={"settings":[1]}
    second=run(callback=lambda *args:{"different":True},evaluation_parameters={"settings":[1]})
    assert first.study_hash==second.study_hash and first.result_hash!=second.result_hash
    assert first.study_hash!=run(evaluation_parameters={"settings":[2]}).study_hash
    nominal=device();nominal.temperature_K=310.0
    changed=propagate_samples(manifest(),nominal,evaluate,evaluation_id="h3-test-v1",
        evaluation_parameters={"settings":[1]},base_protocol=ProgramPulseReadProtocol(5,1e-7))
    assert first.nominal_hash!=changed.nominal_hash
    assert first.study_hash!=changed.study_hash


def test_material_definition_affects_nominal_identity():
    from copy import deepcopy
    nominal=device(); changed=deepcopy(nominal)
    fg=changed.floating_gates()[0]
    # Device.to_dict omits complete material definitions; provenance must still change identity.
    object.__setattr__(fg.nc_material,"phi_barrier_prog_eV",fg.nc_material.phi_barrier_prog_eV+0.1)
    assert nominal.to_dict()==changed.to_dict()
    a=propagate_samples(manifest(),nominal,evaluate,evaluation_id="material",base_protocol=ProgramPulseReadProtocol(5,1e-7))
    b=propagate_samples(manifest(),changed,evaluate,evaluation_id="material",base_protocol=ProgramPulseReadProtocol(5,1e-7))
    assert a.nominal_hash!=b.nominal_hash


def test_result_rejects_missing_reordered_or_wrong_manifest_points():
    result=run()
    with pytest.raises(ValueError): replace(result,points=result.points[:-1])
    with pytest.raises(ValueError): replace(result,points=tuple(reversed(result.points)))
    point=replace(result.points[0].point,manifest_hash="0"*64)
    wrong=replace(result.points[0],point=point)
    with pytest.raises(ValueError): replace(result,points=(wrong,*result.points[1:]))


def test_real_program_read_fresh_simulator_per_candidate():
    m=manifest(2)
    def physics(candidate,protocol,point):
        pulse=run_program_pulse_read(Simulator(candidate),protocol)
        return {"delta_vfb_V":pulse.delta_vfb_V,"protocol":protocol.to_dict()}
    result=run(m,physics)
    assert result.success_count==2
    assert all(math.isfinite(p.output["delta_vfb_V"]) for p in result.points)


def test_combined_candidates_must_pass_device_validation(monkeypatch):
    nominal=device(); diameter=nominal.floating_gates()[0].nc_diameter_nm
    original=type(nominal).validate
    def validate(candidate):
        original(candidate)
        if candidate.temperature_K > 300 and candidate.floating_gates()[0].nc_diameter_nm > diameter:
            raise ValueError("joint physical validation failed")
    monkeypatch.setattr(type(nominal),"validate",validate)
    variations=(definition("temperature",("temperature_K",),BindingScope.DEVICE,"K",295,305),
        definition("diameter",("layers","FG1","nc_diameter_nm"),BindingScope.DEVICE,"nm",diameter-1,diameter+1))
    s=SamplingSpec(variations,123,3)
    reference=sample_variations(s)
    m=SampleManifest(s,((305.0,diameter+0.5),(295.0,diameter+0.5),(305.0,diameter-0.5)),reference.runtime)
    result=propagate_samples(m,nominal,evaluate,evaluation_id="joint-validation-test")
    assert result.points[0].failure_stage=="application"
    assert result.success_count==2 and result.failure_count==1


def test_caller_baseline_is_unchanged_by_candidate_mutation():
    nominal=device(); protocol=ProgramPulseReadProtocol(5,1e-7)
    before=canonical_hash(nominal.to_dict()); protocol_before=protocol.to_dict()
    def mutate(candidate,p,point):
        candidate.temperature_K=999.0
        candidate.layers.clear()
        object.__setattr__(p,"program_voltage_V",99)
        return {"ok":True}
    result=propagate_samples(manifest(),nominal,mutate,evaluation_id="isolated",base_protocol=protocol)
    assert result.success_count==4
    assert canonical_hash(nominal.to_dict())==before
    assert protocol.to_dict()==protocol_before
