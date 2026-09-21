"""Controlled J5 electrical, retention, sensitivity and DTCO reference.

The data and parameter intervals in this example are synthetic.  Results are
software-verification evidence for the opt-in transport path; they are not an
experimental calibration, a device prediction or a manufacturing-yield claim.
"""
from __future__ import annotations

import json
import math

import numpy as np

from ncmemsim import DeviceBuilder, DeviceState, PhysicsModel, RetentionConfig, Simulator
from ncmemsim._version import __version__
from ncmemsim.dtco import (
    BindingScope,
    ConstraintOperator,
    DesignVariable,
    DesignVariableRole,
    ExperimentSpec,
    MetricAnalysisSpec,
    MetricConstraint,
    MetricDefinition,
    ObjectiveDirection,
    ParameterBinding,
    SampleAnalysisSpec,
    SamplingSpec,
    UniformVariation,
    VariationDefinition,
    VariationKind,
    VariationProvenance,
    analyze_samples,
    analyze_sweep,
    propagate_samples,
    run_cartesian_sweep,
    sample_variations,
)
from ncmemsim.fieldsolver import FieldSolver1D
from ncmemsim.materials.provenance import ParameterProvenance, ParameterStatus
from ncmemsim.transport import (
    AdvancedTransportEngine,
    AdvancedTransportSpec,
    ImageForceBarrierSpec,
    TATLinkAttachment,
    TransportConfig,
    TransportEngine,
    TransportMechanism,
    TrapAssistedTransportSpec,
    TrapParameterStatus,
    TrapSpecies,
    analyze_tat_local_sensitivity,
)


SYNTHETIC_SCOPE = (
    "Synthetic software-verification reference; no experimental calibration, "
    "global sensitivity, fabricated-device prediction or manufacturing-yield claim."
)
THICKNESS_BINDING = ParameterBinding(
    BindingScope.DEVICE,
    ("layers", "inter_fg1_sio2", "thickness_nm"),
)


def build_trap_specification() -> TrapAssistedTransportSpec:
    """Return the single assumed species used by every J5 reference path."""
    return TrapAssistedTransportSpec(
        enabled=True,
        species=(
            TrapSpecies(
                name="j5-synthetic-electron-trap",
                energy_depth_J=0.18 * 1.602176634e-19,
                position_fraction=0.5,
                density_m3=8.0e22,
                capture_cross_section_m2=2.0e-20,
                attempt_frequency_Hz=2.0e11,
                parameter_status=TrapParameterStatus.ASSUMED,
                source="synthetic J5 validation parameter set",
                applicability="controlled numerical response only",
            ),
        ),
    )


def build_barrier_correction() -> ImageForceBarrierSpec:
    """Return the explicitly enabled assumed image-force correction."""
    return ImageForceBarrierSpec(
        enabled=True,
        relative_permittivity=3.9,
        parameter_status=TrapParameterStatus.ASSUMED,
        source="synthetic SiO2-like J5 validation value",
        applicability="controlled numerical response only",
    )


def build_context(device=None):
    """Build isolated device, state, physics and opt-in composite engine."""
    candidate = device or DeviceBuilder.v2(
        n_fgs=2,
        inter_fg_sio2_nm=1.0,
        name="j5-advanced-transport-validation",
    )
    physics = PhysicsModel.default()
    baseline = TransportEngine(
        physics.tunneling,
        TransportConfig(
            attempt_frequency_Hz=1.0e13,
            default_barrier_eV=0.25,
            max_transfer_fraction_per_step=0.05,
        ),
    )
    link_id = next(
        item.link_id
        for item in baseline.build_network(candidate).links
        if item.kind == "inter_fg"
    )
    specification = build_trap_specification()
    correction = build_barrier_correction()
    engine = AdvancedTransportEngine(
        baseline,
        AdvancedTransportSpec(
            (TATLinkAttachment(link_id, specification, correction),)
        ),
    )
    physics.transport = engine
    state = DeviceState.empty_for_device(candidate)
    state.floating_gates[0].P0[:] = 0.0
    state.floating_gates[0].P1[:] = 1.0
    state.floating_gates[0].P2[:] = 0.0
    return candidate, physics, state, engine, link_id, specification, correction


def _total_sheet_electrons(device, physics, state) -> float:
    total = 0.0
    for floating_gate, floating_state in zip(
        device.floating_gates(), state.floating_gates
    ):
        grid, dx = physics.occupancy.grid(floating_gate)
        sites = float(
            np.sum(physics.occupancy.density_profile(floating_gate, grid)) * dx
        )
        total += 2.0 * floating_state.mean_normalized_occupation * sites
    return total


def evaluate_electrical_candidate(device, *, gate_voltage_V: float = 4.0) -> dict:
    """Evaluate one fresh synthetic electrical context as finite JSON data."""
    candidate, physics, state, engine, link_id, specification, correction = (
        build_context(device)
    )
    profile = FieldSolver1D().solve(
        candidate,
        gate_voltage_V,
        np.zeros(candidate.number_of_fgs()),
    )
    result = engine.evaluate(candidate, state, profile, physics.occupancy)
    link = next(item for item in result.links if item.link_id == link_id)
    direct = link.contribution(TransportMechanism.DIRECT_TUNNELLING)
    tat = link.contribution(TransportMechanism.TRAP_ASSISTED)
    network_link = next(
        item for item in engine.build_network(candidate).links if item.link_id == link_id
    )
    sensitivity = analyze_tat_local_sensitivity(
        specification,
        correction,
        link_length_m=network_link.length_m,
        electric_field_V_m=link.field_V_m,
        effective_mass_m0=network_link.effective_mass_m0,
        relative_step=0.10,
    )
    residual = float(np.sum(result.net_electron_flux_by_fg_m2_s))
    return {
        "schema_version": "j5-controlled-electrical-v1",
        "scope": SYNTHETIC_SCOPE,
        "link_id": link_id,
        "gate_voltage_V": float(gate_voltage_V),
        "link_length_m": float(network_link.length_m),
        "electric_field_V_m": float(link.field_V_m),
        "direct_flux_abs_m2_s": abs(float(direct.net_electron_flux_m2_s)),
        "tat_flux_abs_m2_s": abs(float(tat.net_electron_flux_m2_s)),
        "total_flux_abs_m2_s": abs(float(link.total_net_electron_flux_m2_s)),
        "tat_total_rate_Hz": float(tat.evaluation.total_rate_Hz),
        "conservation_residual_m2_s": residual,
        "tat_configuration_hash": specification.configuration_hash,
        "correction_configuration_hash": correction.configuration_hash,
        "sensitivity": sensitivity.to_dict(),
        "sensitivity_result_hash": sensitivity.result_hash,
    }


def build_retention_reference() -> dict:
    """Run a short, deterministic two-FG redistribution reference."""
    device, physics, state, _, link_id, _, _ = build_context()
    before = _total_sheet_electrons(device, physics, state)
    result = Simulator(device, physics).simulate_retention(
        state,
        RetentionConfig(
            gate_voltage_V=0.0,
            total_time_s=4.0e-10,
            initial_dt_s=1.0e-10,
            maximum_dt_s=1.0e-10,
            growth_factor=2.0,
            output_points=5,
            stop_at_quasi_equilibrium=False,
        ),
    )
    after = _total_sheet_electrons(device, physics, result.final_state)
    return {
        "schema_version": "j5-controlled-retention-v1",
        "scope": SYNTHETIC_SCOPE,
        "link_id": link_id,
        "time_s": result.time_s.tolist(),
        "mean_occupation_by_fg": result.mean_occupation_by_fg.tolist(),
        "total_charge_retention_fraction": result.total_charge_retention_fraction.tolist(),
        "charge_loss_fraction": result.charge_loss_fraction.tolist(),
        "inter_fg_flux_by_link_m2_s": result.inter_fg_flux_by_link_m2_s.tolist(),
        "electron_sheet_total_initial_m2": before,
        "electron_sheet_total_final_m2": after,
        "electron_conservation_residual_m2": after - before,
    }


def _evaluate_for_space(candidate, candidate_protocol, point) -> dict:
    del candidate_protocol, point
    return evaluate_electrical_candidate(candidate)


def _metric_spec(name: str) -> MetricAnalysisSpec:
    return MetricAnalysisSpec(
        name=name,
        metrics=(
            MetricDefinition(
                "tat_flux",
                ("tat_flux_abs_m2_s",),
                "m^-2 s^-1",
                ObjectiveDirection.MINIMIZE,
            ),
            MetricDefinition(
                "total_flux",
                ("total_flux_abs_m2_s",),
                "m^-2 s^-1",
            ),
            MetricDefinition(
                "conservation_residual",
                ("conservation_residual_m2_s",),
                "m^-2 s^-1",
            ),
        ),
        constraints=(
            MetricConstraint(
                "conservation_upper",
                "conservation_residual",
                ConstraintOperator.LE,
                1.0,
                "m^-2 s^-1",
            ),
            MetricConstraint(
                "conservation_lower",
                "conservation_residual",
                ConstraintOperator.GE,
                -1.0,
                "m^-2 s^-1",
            ),
        ),
    )


def build_dtco_reference() -> tuple:
    """Run three enumerated oxide-thickness points without optimization claims."""
    device = DeviceBuilder.v2(
        n_fgs=2,
        inter_fg_sio2_nm=1.0,
        name="j5-advanced-transport-validation",
    )
    variable = DesignVariable(
        "inter_fg_oxide_thickness",
        THICKNESS_BINDING,
        (0.9, 1.0, 1.1),
        DesignVariableRole.GEOMETRY,
        "nm",
        ParameterProvenance(
            source="synthetic J5 enumerated software-verification values",
            status=ParameterStatus.ASSUMED,
            notes="not a fabrication distribution",
        ),
    )
    experiment = ExperimentSpec.from_device(
        name="j5-controlled-advanced-transport-space",
        device=device,
        variables=(variable,),
        description=SYNTHETIC_SCOPE,
    )
    sweep = run_cartesian_sweep(
        experiment,
        device,
        _evaluate_for_space,
        evaluation_id="j5-controlled-advanced-transport-evaluator-v1",
        evaluation_parameters={
            "ncmemsim_version": __version__,
            "gate_voltage_V": 4.0,
            "initial_state": "fg1-single-electron-state-full-fg2-empty",
            "scope": SYNTHETIC_SCOPE,
        },
    )
    return sweep, analyze_sweep(sweep, _metric_spec("j5-dtco-response-metrics"))


def build_robust_reference() -> tuple:
    """Run four descriptive samples from an assumed validation interval."""
    device = DeviceBuilder.v2(
        n_fgs=2,
        inter_fg_sio2_nm=1.0,
        name="j5-advanced-transport-validation",
    )
    variation = VariationDefinition(
        "inter_fg_oxide_thickness",
        THICKNESS_BINDING,
        UniformVariation(0.9, 1.1),
        "nm",
        VariationKind.PARAMETER_ESTIMATION,
        VariationProvenance(
            source="assumed J5 numerical validation interval",
            applicability="descriptive software-verification samples only",
            notes="not inferred data and not a manufacturing distribution",
        ),
    )
    manifest = sample_variations(
        SamplingSpec((variation,), seed=1105, sample_count=4, max_draws_per_value=1000)
    )
    propagation = propagate_samples(
        manifest,
        device,
        _evaluate_for_space,
        evaluation_id="j5-controlled-advanced-transport-sample-evaluator-v1",
        evaluation_parameters={
            "ncmemsim_version": __version__,
            "gate_voltage_V": 4.0,
            "initial_state": "fg1-single-electron-state-full-fg2-empty",
            "scope": SYNTHETIC_SCOPE,
            "claim_policy": "descriptive sample statistics; no yield estimate",
        },
    )
    analysis = analyze_samples(
        propagation,
        SampleAnalysisSpec(
            _metric_spec("j5-descriptive-sample-response-metrics"),
            quantiles=(0.0, 0.5, 1.0),
        ),
    )
    return manifest, propagation, analysis


def build_validation_bundle() -> dict:
    """Build the complete finite J5 reference without writing files."""
    electrical = evaluate_electrical_candidate(
        DeviceBuilder.v2(
            n_fgs=2,
            inter_fg_sio2_nm=1.0,
            name="j5-advanced-transport-validation",
        )
    )
    retention = build_retention_reference()
    sweep, sweep_analysis = build_dtco_reference()
    manifest, propagation, sample_analysis = build_robust_reference()
    bundle = {
        "schema_version": "j5-advanced-transport-validation-v1",
        "scope": SYNTHETIC_SCOPE,
        "electrical": electrical,
        "retention": retention,
        "dtco": {
            "sweep": sweep.to_dict(),
            "analysis": sweep_analysis.to_dict(),
            "sweep_result_hash": sweep.result_hash,
            "analysis_result_hash": sweep_analysis.result_hash,
        },
        "robust_dtco": {
            "interpretation": "descriptive sample statistics; no yield estimate",
            "manifest": manifest.to_dict(),
            "propagation": propagation.to_dict(),
            "analysis": sample_analysis.to_dict(),
            "manifest_hash": manifest.manifest_hash,
            "propagation_result_hash": propagation.result_hash,
            "analysis_result_hash": sample_analysis.result_hash,
        },
    }
    json.dumps(bundle, sort_keys=True, allow_nan=False)
    return bundle


def main() -> None:
    bundle = build_validation_bundle()
    print("J5 advanced transport controlled validation PASS")
    print("Scope:", bundle["scope"])
    print("DTCO points:", len(bundle["dtco"]["sweep"]["points"]))
    print("Descriptive samples:", bundle["robust_dtco"]["analysis"]["counts"]["total"])
    print("Sensitivity hash:", bundle["electrical"]["sensitivity_result_hash"])


if __name__ == "__main__":
    main()
