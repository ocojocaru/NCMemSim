# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Scientific limits, reproducibility and solver evidence for the L3 reference."""
from copy import deepcopy
import json

import pytest

from examples import phase_l3_tat_density_variability as reference
from ncmemsim.ensemble.model_execution import ModelExecutionResult
from ncmemsim.ensemble.model_sampling import generate_model_sample_manifest
from ncmemsim.hashing import canonical_hash


@pytest.fixture(scope="module")
def evidence():
    return reference.run_reference()


def test_fixed_scope_and_existing_j5_trap_numbers():
    from examples.phase_j5_advanced_transport_validation import build_trap_specification, build_barrier_correction
    device, spec = reference.build_reference()
    attachment = spec.study.model_context.advanced_transport.attachments[0]
    assert attachment.specification == build_trap_specification()
    assert attachment.barrier_correction == build_barrier_correction()
    assert device.number_of_fgs() == 2
    assert spec.rng.seed == 2029
    assert spec.sample_count == 16
    assert spec.study.variables[0].distribution.to_dict() == {
        "family": "log_normal", "median": 8e22, "geometric_standard_deviation": 1.25}


def test_complete_repeat_is_reproducible(evidence):
    repeated = reference.run_reference()
    assert repeated["reference_hash"] == evidence["reference_hash"]
    assert repeated == evidence


def test_full_execution_and_nested_archive_integrity(evidence):
    for key, expected in (("execution", 16), ("zero_variation", 1), ("disabled_tat", 16)):
        result = ModelExecutionResult.from_dict(evidence[key])
        assert result.success_count == expected
        assert result.failure_count == 0
        assert ModelExecutionResult.from_json(result.to_json()).result_hash == result.result_hash
    assert evidence["reference_hash"] == canonical_hash({k: v for k, v in evidence.items() if k != "reference_hash"})


def test_zero_variation_matches_independent_nominal(evidence):
    assert evidence["zero_variation"]["points"][0]["output"] == evidence["nominal"]


def test_density_sensitive_tat_with_fixed_direct_contribution(evidence):
    outputs = [p["output"] for p in evidence["execution"]["points"]]
    ordered = sorted(outputs, key=lambda o: o["density_m3"])
    assert all(b["initial_tat_rate_Hz"] > a["initial_tat_rate_Hz"] for a, b in zip(ordered, ordered[1:]))
    assert all(o["initial_direct_rate_Hz"] == evidence["nominal"]["initial_direct_rate_Hz"] for o in outputs)
    assert all(o["initial_tat_status"] == "evaluated" for o in outputs)
    for output in outputs:
        density_ratio = output["density_m3"] / evidence["nominal"]["density_m3"]
        rate_ratio = output["initial_tat_rate_Hz"] / evidence["nominal"]["initial_tat_rate_Hz"]
        assert rate_ratio == pytest.approx(density_ratio, rel=1e-5)
        assert output["initial_total_rate_Hz"] == pytest.approx(
            output["initial_tat_rate_Hz"] + output["initial_direct_rate_Hz"], rel=1e-15)


def test_disabled_controls_pair_samples_and_retain_direct_only(evidence):
    enabled = evidence["execution"]
    disabled = evidence["disabled_tat"]
    assert [s["values"] for s in enabled["manifest"]["samples"]] == [s["values"] for s in disabled["manifest"]["samples"]]
    occupations = []
    for point in disabled["points"]:
        output = point["output"]
        assert output["initial_tat_rate_Hz"] == 0
        assert output["initial_tat_status"] == "disabled"
        assert output["initial_total_rate_Hz"] == output["initial_direct_rate_Hz"]
        assert output["initial_direct_rate_Hz"] == evidence["nominal"]["initial_direct_rate_Hz"]
        occupations.append(output["final_mean_occupation_by_fg"])
    assert all(x == occupations[0] for x in occupations)


def test_timestep_refinement_has_predeclared_acceptance_and_unclamped_selected_grid(evidence):
    assert evidence["acceptance"]["occupation_atol"] == 1e-3
    assert evidence["acceptance"]["reference_steps"] == 16
    assert [a["case"] for a in evidence["timestep_audit"]] == ["nominal", "sample_min", "sample_max"]
    for audit in evidence["timestep_audit"]:
        errors = audit["max_abs_occupation_delta_vs_finest"]
        assert errors[-1] == 0
        assert errors[0] > errors[1] > errors[2] > errors[3]
        assert audit["selected_delta"] <= 1e-3
        chosen = next(o for o in audit["outputs"] if o["steps"] == 16)
        assert chosen["dt_s"] == 2.5e-15
        assert chosen["clamped_steps"] == 0
        for output in audit["outputs"]:
            assert output["max_relative_conservation_error"] <= 1e-12
            assert all(0 <= x <= 1 for x in output["final_mean_occupation_by_fg"])
            assert sum(output["final_mean_occupation_by_fg"]) == pytest.approx(0.5, abs=1e-12)


def test_numerical_precision_limits_are_explicit(evidence):
    explanation = evidence["interpretation"]
    assert explanation["primary_observable"] == "initial_tat_rate_Hz"
    assert explanation["occupation_variation_smaller_than_grid_delta"] is True
    assert explanation["dynamic_population_precision_claim"] is False
    assert explanation["FG2_sample_occupation_span"] < explanation["max_selected_timestep_delta"]
    assert any("16 samples" in text for text in evidence["limits"])
    assert any("confounded" in text for text in evidence["limits"])


def test_reference_rejects_workflow_failure_instead_of_omitting_samples(monkeypatch):
    def fail(*args):
        raise ArithmeticError("deliberate failure")
    monkeypatch.setattr(reference, "evaluate_reference", fail)
    with pytest.raises(ArithmeticError, match="every sample"):
        reference.run_reference()


def test_writer_preserves_full_evidence_and_never_overwrites(tmp_path, evidence):
    destination = tmp_path / "reference"
    reference.write_reference(destination, evidence)
    loaded = json.loads((destination / "reference.json").read_text())
    assert loaded == evidence
    with pytest.raises(FileExistsError):
        reference.write_reference(destination, evidence)
    assert json.loads((destination / "reference.json").read_text()) == evidence


def test_writer_rejects_bad_identity_before_creating_target(tmp_path, evidence):
    altered = deepcopy(evidence)
    altered["nominal"]["density_m3"] *= 2
    destination = tmp_path / "invalid"
    with pytest.raises(ValueError, match="hash mismatch"):
        reference.write_reference(destination, altered)
    assert not destination.exists()


@pytest.mark.parametrize("steps", [True, 0, -1, 1.5])
def test_invalid_numerical_grid_rejected(steps):
    with pytest.raises(ValueError):
        reference.workflow_settings(steps)


def test_reference_does_not_mutate_nominal_inputs():
    device, spec = reference.build_reference(sample_count=1)
    before = deepcopy(device.to_dict())
    context = deepcopy(spec.study.model_context.to_dict())
    reference._nominal(device, spec)
    assert device.to_dict() == before
    assert spec.study.model_context.to_dict() == context
    manifest = generate_model_sample_manifest(spec)
    assert manifest.samples[0].values[0] > 0
