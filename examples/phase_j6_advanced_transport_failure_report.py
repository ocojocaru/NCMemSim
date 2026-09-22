"""Runnable J6 deliberate-failure advanced-transport reporting reference.

The trap attempt frequency is intentionally extreme but finite so that the
optional TAT path fails only when converted to reservoir-limited flux. The
engine must isolate that failure, preserve the direct baseline, and export
sanitized failure provenance. The extreme value is not a physical claim.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np

from ncmemsim import DeviceBuilder, DeviceState, PhysicsModel
from ncmemsim.fieldsolver import FieldSolver1D
from ncmemsim.transport import (
    AdvancedTransportEngine, AdvancedTransportReport, AdvancedTransportSpec,
    ImageForceBarrierSpec, MechanismEvaluationStatus, TATLinkAttachment,
    TransportConfig, TransportEngine, TransportMechanism,
    TrapAssistedTransportSpec, TrapParameterStatus, TrapSpecies,
    build_advanced_transport_report, write_advanced_transport_report,
)

REFERENCE_SCOPE = (
    "Deliberate J6 software failure-injection reference; the extreme finite "
    "attempt frequency is not a physical parameter claim, experimental "
    "calibration, fabricated-device prediction, or manufacturing-yield input."
)

def build_reference_context():
    device = DeviceBuilder.v2(
        n_fgs=2, inter_fg_sio2_nm=1.0,
        name="j6-deliberate-failure-advanced-transport-report",
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
        link.link_id for link in baseline.build_network(device).links
        if link.kind == "inter_fg"
    )
    trap = TrapSpecies(
        name="j6-deliberate-failure-trap",
        energy_depth_J=1.0e-30,
        position_fraction=0.5,
        density_m3=8.0e22,
        capture_cross_section_m2=2.0e-20,
        attempt_frequency_Hz=1.0e308,
        parameter_status=TrapParameterStatus.ASSUMED,
        source="deliberately extreme finite J6 failure-injection parameter",
        applicability="software failure isolation and reporting only; not physical",
    )
    correction = ImageForceBarrierSpec(
        enabled=True,
        relative_permittivity=3.9,
        parameter_status=TrapParameterStatus.ASSUMED,
        source="synthetic SiO2-like J6 failure-reporting value",
        applicability="symmetric two-interface compact failure-reporting reference",
    )
    specification = AdvancedTransportSpec((
        TATLinkAttachment(
            link_id,
            TrapAssistedTransportSpec(enabled=True, species=(trap,)),
            correction,
        ),
    ))
    engine = AdvancedTransportEngine(baseline, specification)
    state = DeviceState.empty_for_device(device)
    state.floating_gates[0].P0[:] = 0.0
    state.floating_gates[0].P1[:] = 1.0
    state.floating_gates[0].P2[:] = 0.0
    gate_voltage_V = 4.0
    profile = FieldSolver1D().solve(
        device, gate_voltage_V, np.zeros(device.number_of_fgs())
    )
    result = engine.evaluate(device, state, profile, physics.occupancy)
    link = next(item for item in result.links if item.link_id == link_id)
    direct = link.contribution(TransportMechanism.DIRECT_TUNNELLING)
    tat = link.contribution(TransportMechanism.TRAP_ASSISTED)
    if tat.status is not MechanismEvaluationStatus.FAILED or tat.failure is None:
        raise RuntimeError("J6 deliberate-failure reference did not trigger the expected TAT failure")
    if (
        link.total_forward_rate_Hz != direct.forward_rate_Hz
        or link.total_backward_rate_Hz != direct.backward_rate_Hz
        or link.total_net_electron_flux_m2_s != direct.net_electron_flux_m2_s
    ):
        raise RuntimeError("direct baseline was not preserved after the optional mechanism failure")
    return result, specification, link_id, gate_voltage_V

def build_reference_report() -> AdvancedTransportReport:
    result, specification, link_id, gate_voltage_V = build_reference_context()
    return build_advanced_transport_report(
        result,
        specification,
        name="J6 deliberate-failure advanced transport reporting reference",
        metadata={
            "reference_kind": "deliberate_failure",
            "scope": REFERENCE_SCOPE,
            "attached_link_id": link_id,
            "gate_voltage_V": gate_voltage_V,
            "failure_injection": (
                "finite but deliberately extreme trap attempt frequency chosen "
                "only to exercise link-local optional-mechanism failure isolation"
            ),
        },
    )

def write_reference_report(output_dir: str | Path):
    return write_advanced_transport_report(build_reference_report(), output_dir)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_dir", nargs="?",
        default="j6-deliberate-failure-advanced-transport-report",
    )
    args = parser.parse_args()
    report = build_reference_report()
    targets = write_advanced_transport_report(report, args.output_dir)
    print("J6 deliberate-failure advanced transport report PASS")
    print("Report hash:", report.report_hash)
    print("Failed mechanisms:", report.to_dict()["summary"]["failed_contribution_count"])
    print("Artifacts:", ", ".join(str(path) for path in targets))

if __name__ == "__main__":
    main()
