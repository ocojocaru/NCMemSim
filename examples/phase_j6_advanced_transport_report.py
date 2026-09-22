"""Runnable J6 normal advanced-transport reporting reference.

All numerical values are synthetic software-verification inputs. The example
demonstrates deterministic mechanism-resolved reporting and provenance export;
it is not an experimental calibration, fabricated-device prediction, or
manufacturing-yield estimate.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np

from ncmemsim import DeviceBuilder, DeviceState, PhysicsModel
from ncmemsim.fieldsolver import FieldSolver1D
from ncmemsim.transport import (
    AdvancedTransportEngine, AdvancedTransportReport, AdvancedTransportSpec,
    ImageForceBarrierSpec, TATLinkAttachment, TransportConfig, TransportEngine,
    TrapAssistedTransportSpec, TrapParameterStatus, TrapSpecies,
    build_advanced_transport_report, write_advanced_transport_report,
)

REFERENCE_SCOPE = (
    "Synthetic J6 normal reporting reference; software-verification evidence "
    "only, with no experimental calibration, fabricated-device prediction, "
    "or manufacturing-yield claim."
)

def build_reference_context():
    device = DeviceBuilder.v2(
        n_fgs=2, inter_fg_sio2_nm=1.0,
        name="j6-normal-advanced-transport-report",
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
        name="j6-synthetic-electron-trap",
        energy_depth_J=0.18 * 1.602176634e-19,
        position_fraction=0.5,
        density_m3=8.0e22,
        capture_cross_section_m2=2.0e-20,
        attempt_frequency_Hz=2.0e11,
        parameter_status=TrapParameterStatus.ASSUMED,
        source="synthetic J6 normal reporting parameter set",
        applicability="controlled compact-model reporting reference only",
    )
    correction = ImageForceBarrierSpec(
        enabled=True,
        relative_permittivity=3.9,
        parameter_status=TrapParameterStatus.ASSUMED,
        source="synthetic SiO2-like J6 reporting value",
        applicability="symmetric two-interface compact reporting reference only",
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
    return result, specification, link_id, gate_voltage_V

def build_reference_report() -> AdvancedTransportReport:
    result, specification, link_id, gate_voltage_V = build_reference_context()
    return build_advanced_transport_report(
        result,
        specification,
        name="J6 normal advanced transport reporting reference",
        metadata={
            "reference_kind": "normal",
            "scope": REFERENCE_SCOPE,
            "attached_link_id": link_id,
            "gate_voltage_V": gate_voltage_V,
        },
    )

def write_reference_report(output_dir: str | Path):
    return write_advanced_transport_report(build_reference_report(), output_dir)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_dir", nargs="?",
        default="j6-normal-advanced-transport-report",
    )
    args = parser.parse_args()
    report = build_reference_report()
    targets = write_advanced_transport_report(report, args.output_dir)
    print("J6 normal advanced transport report PASS")
    print("Report hash:", report.report_hash)
    print("Failed mechanisms:", report.to_dict()["summary"]["failed_contribution_count"])
    print("Artifacts:", ", ".join(str(path) for path in targets))

if __name__ == "__main__":
    main()
