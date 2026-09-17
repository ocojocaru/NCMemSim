from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from itertools import islice
import json
import math

import pytest

from ncmemsim import DeviceBuilder, Simulator
from ncmemsim.dtco import (
    BindingScope, DesignVariable, DesignVariableRole, ExperimentSpec,
    ParameterBinding, SweepPoint, SweepPointResult, SweepResult,
    iter_cartesian_points, run_cartesian_sweep,
)
from ncmemsim.electro_optical_program_protocol import ElectroOpticalProgramPulseReadProtocol
from ncmemsim.optics import LightSource
from ncmemsim.photo import PhotoTransitionWeights
from ncmemsim.program_protocol import ProgramPulseReadProtocol, run_program_pulse_read


def axis(name="temperature", values=(325.0, 300.0), *, scope=BindingScope.DEVICE,
         path=("temperature_K",), unit="K"):
    return DesignVariable(name, ParameterBinding(scope, path), values,
                          DesignVariableRole.MODEL, unit)


def study(*variables, protocol=None):
    device = DeviceBuilder.v2(n_fgs=1)
    spec = ExperimentSpec.from_device(
        name="g2-study", device=device, variables=variables or (axis(),),
        operating_protocol=protocol,
    )
    return device, spec


def run(spec, device, evaluator=None, **kwargs):
    return run_cartesian_sweep(
        spec, device, evaluator or (lambda d, p, point: {"temperature": d.temperature_K}),
        evaluation_id="test-v1", **kwargs,
    )


def test_cartesian_order_and_assignment_identity():
    device, spec = study(
        axis(),
        axis("diameter", (6.0, 4.0), path=("layers", "FG1", "nc_diameter_nm"), unit="nm"),
    )
    points = list(iter_cartesian_points(spec))
    assert [p.values_by_name for p in points] == [
        (("temperature", 325.0), ("diameter", 6.0)),
        (("temperature", 325.0), ("diameter", 4.0)),
        (("temperature", 300.0), ("diameter", 6.0)),
        (("temperature", 300.0), ("diameter", 4.0)),
    ]
    assert [p.index for p in points] == list(range(spec.design_point_count))
    assert len({p.point_hash for p in points}) == 4
    assert points == list(iter_cartesian_points(spec))
    assignment = points[0].assignments
    assignment["temperature"] = 1
    assert points[0].assignments["temperature"] == 325.0
    with pytest.raises(FrozenInstanceError):
        points[0].index = 10


def test_enumeration_is_lazy_and_supports_declarative_model_categories():
    axes = tuple(axis(f"x{i}", tuple(range(100)), scope=BindingScope.MODEL,
                      path=(f"x{i}",), unit="1") for i in range(8))
    _, spec = study(*axes)
    assert spec.design_point_count == 10**16
    assert [p.index for p in islice(iter_cartesian_points(spec), 3)] == [0, 1, 2]
    _, categories = study(axis(values=("high power", "low power"), scope=BindingScope.MODEL,
                               path=("category",), unit=None))
    assert [p.assignments["temperature"] for p in iter_cartesian_points(categories)] == [
        "high power", "low power",
    ]


def test_definition_and_result_hashes_are_repeatable_and_configuration_sensitive():
    device, spec = study()
    a = run(spec, device, evaluation_parameters={"solver": {"dt": 0.001}})
    b = run(spec, device, evaluation_parameters={"solver": {"dt": 0.001}})
    assert a.to_json() == b.to_json()
    assert a.result_hash == b.result_hash
    assert a.sweep_hash == b.sweep_hash
    c = run(spec, device, evaluation_parameters={"solver": {"dt": 0.002}})
    assert c.sweep_hash != a.sweep_hash
    changed = run(spec, device, lambda *args: {"different": True},
                  evaluation_parameters={"solver": {"dt": 0.001}})
    assert changed.sweep_hash == a.sweep_hash
    assert changed.result_hash != a.result_hash
    other_id = run_cartesian_sweep(spec, device, lambda *args: {}, evaluation_id="test-v2",
                                  evaluation_parameters={"solver": {"dt": 0.001}})
    assert other_id.sweep_hash != a.sweep_hash
    _, reordered = study(axis(values=(300.0, 325.0)))
    assert next(iter_cartesian_points(spec)).point_hash != next(
        iter_cartesian_points(reordered)
    ).point_hash


def test_callback_mutation_does_not_leak_and_outputs_are_snapshots():
    device, spec = study()
    original = device.to_dict()
    shared = {"nested": [1]}
    candidates = []
    def evaluate(candidate, protocol, point):
        candidates.append(candidate)
        assert candidate.get_layer("FG1").nc_diameter_nm == device.get_layer("FG1").nc_diameter_nm
        candidate.get_layer("FG1").nc_diameter_nm = 99
        return shared
    result = run(spec, device, evaluate)
    shared["nested"].append(2)
    exported = result.to_dict()
    exported["points"][0]["output"]["nested"].append(3)
    assert result.points[0].output == {"nested": [1]}
    assert candidates[0] is not candidates[1]
    assert device.to_dict() == original
    assert result.success_count == 2
    assert result.failure_count == 0


def test_device_binding_failure_does_not_stop_later_points():
    device, spec = study(axis(values=(-1.0, 300.0)))
    seen = []
    result = run(spec, device, lambda d, p, point: seen.append(point.index) or {})
    assert seen == [1]
    assert [p.status for p in result.points] == ["failed", "success"]
    assert result.points[0].failure_stage == "application"
    assert result.failure_count == result.success_count == 1
    assert spec.matches_device(device)


def test_evaluation_failure_is_isolated_even_after_candidate_mutation():
    device, spec = study()
    def evaluate(candidate, protocol, point):
        if point.index == 0:
            candidate.temperature_K = 1
            raise RuntimeError("deliberate failure")
        assert candidate.temperature_K == 300.0
        return {"ok": True}
    result = run(spec, device, evaluate)
    assert result.points[0].error_type == "builtins.RuntimeError"
    assert result.points[0].error_message == "deliberate failure"
    assert result.points[0].failure_stage == "evaluation"
    assert result.points[1].output == {"ok": True}


@pytest.mark.parametrize("bad", [
    None, [], {"x": math.nan}, {"x": math.inf}, {1: "bad"},
    {"x": object()}, {"x": (1, 2)}, {"x": {1, 2}},
])
def test_invalid_output_is_recorded_as_serialization_failure(bad):
    device, spec = study()
    result = run(spec, device, lambda d, p, point: bad if point.index == 0 else {})
    assert result.points[0].failure_stage == "serialization"
    assert result.points[0].output is None
    assert result.points[1].status == "success"
    json.loads(result.to_json())


@pytest.mark.parametrize("exc_type", [KeyboardInterrupt, SystemExit])
def test_process_control_exceptions_propagate(exc_type):
    device, spec = study()
    def evaluate(*args):
        raise exc_type()
    with pytest.raises(exc_type):
        run(spec, device, evaluate)


def test_mixed_operating_application_and_failure_isolation():
    protocol = ProgramPulseReadProtocol(5.0, 1e-6)
    device, spec = study(
        axis(values=(300.0,)),
        axis("time", (-1.0, 1e-6), scope=BindingScope.OPERATING,
             path=("program", "time_s"), unit="s"), protocol=protocol,
    )
    result = run(spec, device, lambda d, p, point: {
        "temperature": d.temperature_K, "time": p.programming_time_s,
    }, base_protocol=protocol)
    assert result.points[0].failure_stage == "application"
    assert result.points[1].output == {"temperature": 300.0, "time": 1e-6}
    assert protocol.programming_time_s == 1e-6


def test_optical_sweep_preserves_protocol_and_baseline():
    protocol = ElectroOpticalProgramPulseReadProtocol(
        electrical_protocol=ProgramPulseReadProtocol(5.0, 1e-6),
        light_source=LightSource.led(wavelength_nm=1300.0, power_density_W_m2=100.0),
        photo_weights=PhotoTransitionWeights(),
    )
    device, spec = study(axis("wavelength", (1300.0, 1400.0), scope=BindingScope.OPERATING,
                              path=("optical", "wavelength_nm"), unit="nm"), protocol=protocol)
    result = run(spec, device, lambda d, p, point: {
        "wavelength": p.light_source.wavelength_nm,
    }, base_protocol=protocol)
    assert [p.output["wavelength"] for p in result.points] == [1300.0, 1400.0]
    assert protocol.light_source.wavelength_nm == 1300.0


def test_setup_rejects_baseline_mismatch_before_callback():
    device, spec = study()
    device.temperature_K = 333
    called = []
    with pytest.raises(ValueError, match="base_device_hash"):
        run(spec, device, lambda *args: called.append(True) or {})
    assert not called


def test_operating_identity_required_and_checked_before_callback():
    protocol = ProgramPulseReadProtocol(5.0, 1e-6)
    device, spec = study(protocol=protocol)
    with pytest.raises(ValueError, match="operating baseline"):
        run(spec, device)
    with pytest.raises(ValueError, match="base_operating_hash"):
        run(spec, device, base_protocol=replace(protocol, program_voltage_V=6.0))
    device, spec = study()
    with pytest.raises(ValueError, match="operating identity"):
        run(spec, device, base_protocol=protocol)


@pytest.mark.parametrize("bad_id", ["", " spaced", "spaced ", None])
def test_evaluation_identity_validation(bad_id):
    device, spec = study()
    with pytest.raises(ValueError, match="evaluation_id"):
        run_cartesian_sweep(spec, device, lambda *args: {}, evaluation_id=bad_id)


@pytest.mark.parametrize("parameters", [[], {"dt": math.nan}, {1: 2}, {"object": object()}])
def test_invalid_evaluation_parameters_fail_setup(parameters):
    device, spec = study()
    with pytest.raises((TypeError, ValueError)):
        run(spec, device, evaluation_parameters=parameters)


def test_model_execution_is_deferred_but_enumeration_remains_supported():
    device, spec = study(axis(scope=BindingScope.MODEL))
    assert len(list(iter_cartesian_points(spec))) == 2
    with pytest.raises(ValueError, match="MODEL"):
        run(spec, device)


def test_result_roundtrip_and_record_validation():
    device, spec = study()
    result = run(spec, device)
    manifest = json.loads(result.to_json())
    assert manifest["success_count"] == 2
    assert manifest["failure_count"] == 0
    assert manifest["points"][0]["point_hash"] == result.points[0].point.point_hash
    with pytest.raises(ValueError, match="order"):
        SweepResult(result.experiment_json, result.evaluation_json, tuple(reversed(result.points)))
    with pytest.raises(ValueError):
        SweepPointResult(result.points[0].point, "failed", failure_stage="unknown")
    with pytest.raises(ValueError):
        SweepPointResult(result.points[0].point, "success", output_json="{}",
                         error_type="unexpected")


def test_callback_external_baseline_mutation_cannot_change_later_candidates():
    device, spec = study()
    def evaluate(candidate, protocol, point):
        if point.index == 0:
            device.get_layer("FG1").nc_diameter_nm = 99
        return {"diameter": candidate.get_layer("FG1").nc_diameter_nm}
    result = run(spec, device, evaluate)
    assert result.points[0].output == result.points[1].output


def test_real_program_pulse_evaluation_matches_independent_run():
    protocol = ProgramPulseReadProtocol(5.0, 1e-9)
    device, spec = study(axis(values=(300.0,)), protocol=protocol)
    def evaluate(candidate, candidate_protocol, point):
        result = run_program_pulse_read(Simulator(candidate), candidate_protocol)
        return {"delta_vfb_V": result.delta_vfb_V}
    result = run(spec, device, evaluate, base_protocol=protocol)
    expected = run_program_pulse_read(Simulator(device), protocol)
    assert result.success_count == 1
    assert result.points[0].output["delta_vfb_V"] == pytest.approx(expected.delta_vfb_V)


def test_all_application_failures_still_have_complete_manifest():
    device, spec = study(axis(path=("unknown",), unit="custom"))
    result = run(spec, device)
    assert result.success_count == 0
    assert result.failure_count == spec.design_point_count
    assert all(p.failure_stage == "application" for p in result.points)
    assert len(json.loads(result.to_json())["points"]) == 2


def test_result_rejects_incomplete_or_wrong_cartesian_assignments():
    device, spec = study()
    result = run(spec, device)
    with pytest.raises(ValueError, match="every declared"):
        SweepResult(result.experiment_json, result.evaluation_json, result.points[:1])
    incorrect = replace(result.points[0].point, values_by_name=(("temperature", 999),))
    wrong = replace(result.points[0], point=incorrect)
    with pytest.raises(ValueError, match="assignments"):
        SweepResult(result.experiment_json, result.evaluation_json, (wrong, result.points[1]))


def test_point_validation_and_invalid_spec():
    with pytest.raises(TypeError, match="spec"):
        next(iter_cartesian_points(None))
    with pytest.raises(ValueError):
        SweepPoint("invalid", 0, (("x", 1),))
    with pytest.raises(ValueError):
        SweepPoint("a" * 64, -1, (("x", 1),))
    with pytest.raises(ValueError):
        SweepPoint("a" * 64, 0, (("x", 1), ("x", 2)))
    with pytest.raises(TypeError):
        SweepPoint("a" * 64, 0, (("x", True),))


def test_material_composition_uses_existing_factory_without_mutating_baseline():
    from ncmemsim.materials import make_gesn
    device = DeviceBuilder.v2(n_fgs=1)
    device.get_layer("FG1").nc_material = make_gesn(0.1)
    variable = axis("tin", (0.1, 0.2),
                    path=("layers", "FG1", "nc_material", "sn_fraction"), unit="1")
    spec = ExperimentSpec.from_device(name="gesn-sweep", device=device, variables=(variable,))
    result = run(spec, device, lambda d, p, point: d.get_layer("FG1").nc_material.to_dict())
    assert result.success_count == 2
    assert result.points[1].output == make_gesn(0.2).to_dict()
    assert device.get_layer("FG1").nc_material.to_dict() == make_gesn(0.1).to_dict()


def test_evaluation_configuration_snapshot_is_not_changed_by_callback():
    device, spec = study()
    parameters = {"dt": [0.001]}
    def evaluate(*args):
        parameters["dt"].append(1)
        return {}
    result = run(spec, device, evaluate, evaluation_parameters=parameters)
    assert result.to_dict()["evaluation"]["parameters"] == {"dt": [0.001]}
