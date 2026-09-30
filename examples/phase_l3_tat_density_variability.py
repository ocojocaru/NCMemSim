"""Synthetic TAT-density reference using the Phase L stored execution path.

Fixed-field inter-FG redistribution is a numerical reference, not a retention
prediction or a calibrated defect/process population. Run from the repository:
python examples/phase_l3_tat_density_variability.py --output results/l3-density
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
import math
from pathlib import Path

import numpy as np

from ncmemsim import DeviceBuilder, DeviceState, PhysicsModel
from ncmemsim.ensemble import ConstantDistribution, LogNormalDistribution, PhysicalDomain, RNGSpec
from ncmemsim.ensemble.model_contracts import (
    ModelVariabilitySpec, TransportModelContext, TrapDensityVariable, trap_density_binding,
)
from ncmemsim.ensemble.model_sampling import ModelSamplingSpec, generate_model_sample_manifest
from ncmemsim.ensemble.model_execution import execute_model_sample_manifest
from ncmemsim.fieldsolver import FieldSolver1D
from ncmemsim.hashing import canonical_hash
from ncmemsim.materials.provenance import ParameterProvenance, ParameterStatus
from ncmemsim.transport import (
    AdvancedTransportEngine, AdvancedTransportSpec, ImageForceBarrierSpec, MechanismEvaluationStatus,
    TATLinkAttachment, TransportConfig, TransportEngine, TransportMechanism,
    TrapAssistedTransportSpec, TrapParameterStatus, TrapSpecies,
)


NOMINAL_DENSITY_M3 = 8e22
SEED = 2029
SAMPLE_COUNT = 16
GEOMETRIC_SD = 1.25
TOTAL_TIME_S = 4e-14
REFERENCE_STEPS = 16
AUDIT_STEPS = (4, 8, 16, 32)
OCCUPATION_ATOL = 1e-3
CONSERVATION_RTOL = 1e-12
LINK_ID = "FG1<->FG2"
SPECIES_NAME = "j5-synthetic-electron-trap"
SCOPE = "Synthetic assumed density population; fixed-field closed inter-FG redistribution; no experimental calibration or manufacturing yield."


def build_reference(*, constant=False, enabled=True, sample_count=SAMPLE_COUNT):
    """Reuse J5 geometry and trap/image-force numbers with explicit L3 ownership."""
    device = DeviceBuilder.v2(n_fgs=2, inter_fg_sio2_nm=1, name="l3-tat-density-reference")
    species = TrapSpecies(SPECIES_NAME, 0.18 * 1.602176634e-19, 0.5, NOMINAL_DENSITY_M3,
                          2e-20, 2e11, TrapParameterStatus.ASSUMED,
                          "synthetic J5 validation parameter set", "controlled numerical response only")
    correction = ImageForceBarrierSpec(True, 3.9, TrapParameterStatus.ASSUMED,
                                       "synthetic SiO2-like J5 validation value", "controlled numerical response only")
    context = TransportModelContext(AdvancedTransportSpec((TATLinkAttachment(
        LINK_ID, TrapAssistedTransportSpec(enabled, (species,)), correction),)))
    variable = TrapDensityVariable("trap_density", trap_density_binding(LINK_ID, SPECIES_NAME),
        ConstantDistribution(NOMINAL_DENSITY_M3) if constant else LogNormalDistribution(NOMINAL_DENSITY_M3, GEOMETRIC_SD),
        PhysicalDomain(lower=0), ParameterProvenance(
            "L3 constant nominal control" if constant else "explicit L3 lognormal assumption; not measured", ParameterStatus.ASSUMED),
        "controlled density-only comparison with fixed capture cross section", NOMINAL_DENSITY_M3)
    study = ModelVariabilitySpec.from_device(name="l3-density", device=device, model_context=context, variables=(variable,))
    return device, ModelSamplingSpec(study, RNGSpec(SEED), sample_count)


def workflow_settings(steps=REFERENCE_STEPS):
    """Record all configurable inputs used by this reference evaluator."""
    if type(steps) is not int or steps < 1:
        raise ValueError("steps must be a positive integer")
    physics = PhysicsModel.default()
    return {"scope": SCOPE, "gate_voltage_V": 4.0, "total_time_s": TOTAL_TIME_S, "steps": steps,
        "time_grid": "uniform exact endpoint via total_time/steps",
        "field_policy": "FieldSolver1D fixed from zero supplied sheet charges; no self-consistent refresh",
        "initial_state": "FG1 P1=1,P0=P2=0; FG2 P0=1,P1=P2=0",
        "tunneling_config": asdict(physics.tunneling.config), "occupancy_config": asdict(physics.occupancy.config),
        "transport_config": asdict(TransportConfig(attempt_frequency_Hz=1e13, default_barrier_eV=0.25,
                                                    max_transfer_fraction_per_step=0.05)),
        "mechanism_failure_policy": "raise to workflow failure; preserve Phase L failure accounting",
        "conservation_rtol": CONSERVATION_RTOL, "interpretation": "no substrate injection or emission kinetics"}


def _electrons(device, physics, state):
    return math.fsum(2 * float(s.mean_normalized_occupation) *
        float(np.sum(physics.occupancy.density_profile(fg, physics.occupancy.grid(fg)[0])) * physics.occupancy.grid(fg)[1])
        for fg, s in zip(device.floating_gates(), state.floating_gates, strict=True))


def _evaluate_context(device, model_context, settings):
    """Evaluate explicit device/transport inputs, exposing every mechanism."""
    from ncmemsim.tunneling import TunnelingConfig
    from ncmemsim.kinetics import KineticsConfig
    physics = PhysicsModel.default()
    physics.tunneling.config = TunnelingConfig(**settings["tunneling_config"])
    physics.occupancy.config = KineticsConfig(**settings["occupancy_config"])
    baseline = TransportEngine(physics.tunneling, TransportConfig(**settings["transport_config"]))
    engine = AdvancedTransportEngine(baseline, model_context.advanced_transport)
    profile = FieldSolver1D().solve(device, settings["gate_voltage_V"], np.zeros(device.number_of_fgs()))
    state = DeviceState.empty_for_device(device)
    state.floating_gates[0].P0[:] = 0
    state.floating_gates[0].P1[:] = 1
    state.floating_gates[0].P2[:] = 0
    initial = _electrons(device, physics, state)
    dt = settings["total_time_s"] / settings["steps"]
    first = None
    clamped_steps = 0
    max_conservation_error = 0.0
    for _ in range(settings["steps"]):
        evolved, result = engine.step(device, state, profile, physics.occupancy, dt)
        if any(c.status is MechanismEvaluationStatus.FAILED for link in result.links for c in link.contributions):
            raise ArithmeticError("optional transport mechanism failed")
        link = next(item for item in result.links if item.link_id == LINK_ID)
        if first is None:
            first = link
        sites = np.array([baseline._sheet_site_density(physics.occupancy, fg) for fg in device.floating_gates()])
        if np.any(np.abs(result.net_electron_flux_by_fg_m2_s * dt) >
                  baseline.config.max_transfer_fraction_per_step * 2 * sites):
            clamped_steps += 1
        state = evolved
        max_conservation_error = max(max_conservation_error, abs(_electrons(device, physics, state) - initial) / initial)
    if max_conservation_error > settings["conservation_rtol"]:
        raise ArithmeticError("closed redistribution violates electron-conservation tolerance")
    direct = first.contribution(TransportMechanism.DIRECT_TUNNELLING)
    tat = first.contribution(TransportMechanism.TRAP_ASSISTED)
    return {"schema_version": "l3-density-observables-v1", "density_m3": model_context.resolve_density(
                trap_density_binding(LINK_ID, SPECIES_NAME)),
        "initial_direct_rate_Hz": direct.forward_rate_Hz,
        "initial_tat_rate_Hz": tat.forward_rate_Hz,
        "initial_tat_status": tat.status.value,
        "initial_total_rate_Hz": first.forward_rate_Hz,
        "initial_direct_flux_m2_s": direct.net_electron_flux_m2_s,
        "initial_tat_flux_m2_s": tat.net_electron_flux_m2_s,
        "final_mean_occupation_by_fg": state.mean_normalized_occupations.tolist(),
        "initial_electron_sheet_m2": initial, "final_electron_sheet_m2": _electrons(device, physics, state),
        "max_relative_conservation_error": max_conservation_error, "clamped_steps": clamped_steps,
        "steps": settings["steps"], "dt_s": dt}


def evaluate_reference(realization, settings):
    """Wire the actual realized model into the controlled transport solver."""
    return _evaluate_context(realization.device, realization.model_context, settings)


def _nominal(device, spec, *, density=NOMINAL_DENSITY_M3, steps=REFERENCE_STEPS):
    attachment = spec.study.model_context.advanced_transport.attachments[0]
    trap = replace(attachment.specification.species[0], density_m3=density)
    context = TransportModelContext(AdvancedTransportSpec((replace(attachment,
        specification=replace(attachment.specification, species=(trap,))),)))
    # Independent nominal construction, without applying an ensemble sample.
    return _evaluate_context(device, context, workflow_settings(steps))


def run_reference():
    """Preserve executions and audit nominal/sample-extreme timestep response."""
    device, spec = build_reference()
    manifest = generate_model_sample_manifest(spec)
    execution = execute_model_sample_manifest(manifest, device, evaluate_reference,
        evaluation_id="l3-fixed-field-density-reference-v1", workflow_context=workflow_settings())
    if execution.failure_count:
        raise ArithmeticError("reference requires successful real solver execution for every sample")
    nominal = _nominal(device, spec)
    zero_device, zero_spec = build_reference(constant=True, sample_count=1)
    zero = execute_model_sample_manifest(generate_model_sample_manifest(zero_spec), zero_device, evaluate_reference,
        evaluation_id="l3-fixed-field-density-reference-v1", workflow_context=workflow_settings())
    if zero.failure_count or zero.points[0].to_dict()["output"] != nominal:
        raise AssertionError("zero variation does not reproduce independent nominal")
    off_device, off_spec = build_reference(enabled=False)
    off = execute_model_sample_manifest(generate_model_sample_manifest(off_spec), off_device, evaluate_reference,
        evaluation_id="l3-fixed-field-density-reference-v1", workflow_context=workflow_settings())
    if off.failure_count:
        raise AssertionError("disabled-TAT reference failed")
    densities = [s.values[0] for s in manifest.samples]
    if densities != [s.values[0] for s in off.manifest.samples]:
        raise AssertionError("enabled/disabled controls are not sample-paired")
    audit = []
    for label, density in (("nominal", NOMINAL_DENSITY_M3), ("sample_min", min(densities)), ("sample_max", max(densities))):
        outputs = [_nominal(device, spec, density=density, steps=n) for n in AUDIT_STEPS]
        finest = np.array(outputs[-1]["final_mean_occupation_by_fg"])
        errors = [float(np.max(np.abs(np.array(o["final_mean_occupation_by_fg"]) - finest))) for o in outputs]
        chosen_error = errors[AUDIT_STEPS.index(REFERENCE_STEPS)]
        if chosen_error > OCCUPATION_ATOL or outputs[AUDIT_STEPS.index(REFERENCE_STEPS)]["clamped_steps"]:
            raise AssertionError("selected timestep fails refinement/transfer-cap audit")
        audit.append({"case": label, "density_m3": density, "outputs": outputs,
                      "max_abs_occupation_delta_vs_finest": errors, "selected_delta": chosen_error})
    for point in execution.points:
        output = point.to_dict()["output"]
        if output["initial_direct_rate_Hz"] != nominal["initial_direct_rate_Hz"]:
            raise AssertionError("density variation changed the direct baseline")
        if output["clamped_steps"]:
            raise AssertionError("reference timestep activated the transfer cap")
    for point in off.points:
        output = point.to_dict()["output"]
        if output["initial_tat_rate_Hz"] != 0 or output["initial_direct_rate_Hz"] != nominal["initial_direct_rate_Hz"]:
            raise AssertionError("disabled TAT did not preserve the direct baseline")
    occupations = [p.to_dict()["output"]["final_mean_occupation_by_fg"][1] for p in execution.points]
    dynamics_span = max(occupations) - min(occupations)
    grid_delta = max(a["selected_delta"] for a in audit)
    evidence = {"schema_version": "l3-density-reference-v1", "scope": SCOPE,
        "nominal": nominal, "execution": execution.to_dict(), "zero_variation": zero.to_dict(),
        "disabled_tat": off.to_dict(), "timestep_audit": audit,
        "acceptance": {"occupation_atol": OCCUPATION_ATOL, "conservation_rtol": CONSERVATION_RTOL,
                       "reference_steps": REFERENCE_STEPS, "finest_steps": AUDIT_STEPS[-1]},
        "units": {"density": "m^-3", "rate": "Hz", "flux": "m^-2 s^-1", "occupation": "1", "time": "s"},
        "interpretation": {"primary_observable": "initial_tat_rate_Hz",
            "FG2_sample_occupation_span": dynamics_span, "max_selected_timestep_delta": grid_delta,
            "occupation_variation_smaller_than_grid_delta": dynamics_span < grid_delta,
            "dynamic_population_precision_claim": False},
        "limits": ["lognormal distribution is assumed, not measured", "16 samples do not establish tail convergence",
                   "density and capture cross section are confounded; cross section is fixed",
                   "fixed-field closed redistribution is not full retention or a self-consistent device trajectory",
                   "finite timestep comparison is not an exact-solution error bound", "statistics integration remains L4"]}
    return {**evidence, "reference_hash": canonical_hash(evidence)}


def write_reference(destination, evidence):
    """Write one reference evidence file without overwriting existing targets."""
    payload = {k: v for k, v in evidence.items() if k != "reference_hash"}
    if evidence.get("reference_hash") != canonical_hash(payload):
        raise ValueError("reference hash mismatch")
    serialized = json.dumps(evidence, indent=2, allow_nan=False)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "reference.json").write_text(serialized + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    evidence = run_reference()
    if args.output:
        write_reference(args.output, evidence)
    print(json.dumps({"reference_hash": evidence["reference_hash"],
        "samples": evidence["execution"]["success_count"],
        "nominal": evidence["nominal"],
        "selected_timestep_errors": [a["selected_delta"] for a in evidence["timestep_audit"]]}, indent=2))


if __name__ == "__main__":
    main()
