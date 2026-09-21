from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
import math

import numpy as np
import pytest

from examples import phase_j5_advanced_transport_validation as reference
from ncmemsim import DeviceBuilder
from ncmemsim.transport import (
    ImageForceBarrierSpec,
    TransportIdentifiabilityStatus,
    TransportSensitivityEntry,
    TransportSensitivityParameter,
    TransportSensitivityResult,
    TrapAssistedTransportSpec,
    analyze_tat_local_sensitivity,
)


@pytest.fixture(scope="module")
def bundle():
    return reference.build_validation_bundle()


def test_controlled_electrical_accounting_is_finite_and_conservative(bundle):
    result = bundle["electrical"]
    assert result["schema_version"] == "j5-controlled-electrical-v1"
    assert result["direct_flux_abs_m2_s"] > 0.0
    assert result["tat_flux_abs_m2_s"] > 0.0
    assert result["total_flux_abs_m2_s"] == pytest.approx(
        result["direct_flux_abs_m2_s"] + result["tat_flux_abs_m2_s"]
    )
    assert result["tat_total_rate_Hz"] > 0.0
    assert result["conservation_residual_m2_s"] == pytest.approx(0.0, abs=1.0)
    assert len(result["tat_configuration_hash"]) == 64
    assert len(result["correction_configuration_hash"]) == 64
    json.dumps(result, sort_keys=True, allow_nan=False)


def test_local_sensitivity_identifies_exact_multiplicative_and_confounded_terms(bundle):
    raw = bundle["electrical"]["sensitivity"]
    entries = {item["parameter"]: item for item in raw["entries"]}
    assert set(entries) == {item.value for item in TransportSensitivityParameter}
    attempt = entries[TransportSensitivityParameter.ATTEMPT_FREQUENCY_HZ.value]
    assert attempt["normalized_log_secant"] == pytest.approx(1.0, abs=1.0e-12)
    density = entries[TransportSensitivityParameter.DENSITY_M3.value]
    cross = entries[TransportSensitivityParameter.CAPTURE_CROSS_SECTION_M2.value]
    assert density["normalized_log_secant"] == pytest.approx(
        cross["normalized_log_secant"], rel=1.0e-12
    )
    assert density["identifiability_status"] == "structurally_confounded"
    assert density["confounded_group"] == cross["confounded_group"]
    assert "global sensitivity" in raw["limitations"][0]
    assert "manufacturing-yield" in raw["limitations"][-1]


def test_sensitivity_result_is_immutable_hashed_and_repeatable(bundle):
    device, _, _, engine, link_id, specification, correction = reference.build_context()
    link = next(item for item in engine.build_network(device).links if item.link_id == link_id)
    result = analyze_tat_local_sensitivity(
        specification,
        correction,
        link_length_m=link.length_m,
        electric_field_V_m=bundle["electrical"]["electric_field_V_m"],
        effective_mass_m0=link.effective_mass_m0,
    )
    assert isinstance(result, TransportSensitivityResult)
    assert result.result_hash == bundle["electrical"]["sensitivity_result_hash"]
    with pytest.raises(FrozenInstanceError):
        result.relative_step = 0.2


def test_sensitivity_rejects_ambiguous_or_invalid_contexts():
    specification = reference.build_trap_specification()
    correction = reference.build_barrier_correction()
    kwargs = dict(link_length_m=1.0e-9, electric_field_V_m=1.0e8, effective_mass_m0=0.5)
    with pytest.raises(ValueError, match="one enabled trap species"):
        analyze_tat_local_sensitivity(TrapAssistedTransportSpec(), correction, **kwargs)
    with pytest.raises(ValueError, match="one enabled trap species"):
        analyze_tat_local_sensitivity(
            TrapAssistedTransportSpec(
                True,
                (
                    specification.species[0],
                    replace(specification.species[0], name="second-synthetic-species"),
                ),
            ),
            correction,
            **kwargs,
        )
    with pytest.raises(ValueError, match="strictly between"):
        analyze_tat_local_sensitivity(
            specification, correction, relative_step=1.0, **kwargs
        )


def test_disabled_correction_omits_its_parameter():
    result = analyze_tat_local_sensitivity(
        reference.build_trap_specification(),
        ImageForceBarrierSpec(),
        link_length_m=1.0e-9,
        electric_field_V_m=1.0e8,
        effective_mass_m0=0.5,
    )
    assert len(result.entries) == 4
    assert TransportSensitivityParameter.IMAGE_FORCE_RELATIVE_PERMITTIVITY not in {
        item.parameter for item in result.entries
    }


def test_entry_contract_enforces_units_and_confounding_group():
    with pytest.raises(ValueError, match="unit"):
        TransportSensitivityEntry(
            TransportSensitivityParameter.DENSITY_M3,
            "m^3",
            1.0,
            2.0,
            3.0,
            1.0,
            2.0,
            3.0,
            1.0,
            TransportIdentifiabilityStatus.STRUCTURALLY_CONFOUNDED,
            "group",
        )
    with pytest.raises(ValueError, match="require a group"):
        TransportSensitivityEntry(
            TransportSensitivityParameter.DENSITY_M3,
            "m^-3",
            1.0,
            2.0,
            3.0,
            1.0,
            2.0,
            3.0,
            1.0,
            TransportIdentifiabilityStatus.STRUCTURALLY_CONFOUNDED,
        )


def test_retention_reference_preserves_input_charge_and_bounds(bundle):
    result = bundle["retention"]
    time = np.asarray(result["time_s"])
    occupation = np.asarray(result["mean_occupation_by_fg"])
    assert time.shape == (5,)
    assert np.all(np.diff(time) > 0.0)
    assert occupation.shape == (5, 2)
    assert np.all((0.0 <= occupation) & (occupation <= 1.0))
    np.testing.assert_allclose(
        np.sum(occupation, axis=1),
        np.sum(occupation[0]),
        rtol=1.0e-13,
        atol=1.0e-13,
    )
    assert result["electron_conservation_residual_m2"] == pytest.approx(
        0.0, abs=8.0
    )
    np.testing.assert_allclose(
        result["total_charge_retention_fraction"], 1.0, rtol=1.0e-13, atol=1.0e-13
    )


def test_dtco_reference_executes_every_enumerated_point(bundle):
    sweep = bundle["dtco"]["sweep"]
    analysis = bundle["dtco"]["analysis"]
    assert [point["point"]["assignments"][0]["value"] for point in sweep["points"]] == [
        0.9,
        1.0,
        1.1,
    ]
    assert all(point["status"] == "success" for point in sweep["points"])
    assert analysis["feasible_count"] == 3
    assert analysis["failure_count"] == 0
    assert len(bundle["dtco"]["sweep_result_hash"]) == 64
    assert len(bundle["dtco"]["analysis_result_hash"]) == 64


def test_robust_reference_is_descriptive_and_keeps_all_samples(bundle):
    robust = bundle["robust_dtco"]
    analysis = robust["analysis"]
    assert analysis["counts"] == {
        "total": 4,
        "assessed": 4,
        "feasible": 4,
        "infeasible": 0,
        "failed": 0,
        "propagation_failed": 0,
        "extraction_failed": 0,
    }
    assert robust["interpretation"] == "descriptive sample statistics; no yield estimate"
    provenance = robust["manifest"]["spec"]["variations"][0]["provenance"]
    assert "not a manufacturing distribution" in provenance["notes"]
    assert all(item["denominator"] == 4 for item in analysis["metric_statistics"])
    assert all(item["sample_indices"] == [0, 1, 2, 3] for item in analysis["metric_statistics"])


def test_complete_bundle_is_finite_and_repeated_execution_is_stable(bundle):
    encoded = json.dumps(bundle, sort_keys=True, allow_nan=False)
    repeated = reference.build_validation_bundle()
    assert repeated["electrical"]["sensitivity_result_hash"] == bundle["electrical"]["sensitivity_result_hash"]
    assert repeated["dtco"]["analysis_result_hash"] == bundle["dtco"]["analysis_result_hash"]
    assert repeated["robust_dtco"]["analysis_result_hash"] == bundle["robust_dtco"]["analysis_result_hash"]
    assert "experimental calibration" in encoded
    assert "no yield estimate" in encoded


def test_public_exports_and_reference_scope_do_not_extend_stable_v1_surface():
    import ncmemsim.transport as transport
    from scripts.validate_dtco_distribution import SOURCE_REQUIRED

    for name in (
        "TransportSensitivityParameter",
        "TransportIdentifiabilityStatus",
        "TransportSensitivityEntry",
        "TransportSensitivityResult",
        "analyze_tat_local_sensitivity",
    ):
        assert getattr(transport, name) is not None
    assert "examples/phase_j5_advanced_transport_validation.py" in SOURCE_REQUIRED
    assert reference.SYNTHETIC_SCOPE.lower().count("manufacturing-yield") == 1


def test_electrical_candidate_does_not_mutate_device_definition():
    device = DeviceBuilder.v2(
        n_fgs=2,
        inter_fg_sio2_nm=1.0,
        name="j5-advanced-transport-validation",
    )
    before = device.to_dict()
    result = reference.evaluate_electrical_candidate(device)
    assert device.to_dict() == before
    assert math.isfinite(result["total_flux_abs_m2_s"])
