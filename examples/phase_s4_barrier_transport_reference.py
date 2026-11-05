# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Synthetic opt-in direct replacements at current snapshots; no new material law."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from ncmemsim import DeviceBuilder, DeviceState, PhysicsModel
from ncmemsim.fieldsolver import FieldSolver1D
from ncmemsim.barrier_contracts import BarrierProvenance, BarrierSegment, BarrierProfile, BarrierEvaluationSpec
from ncmemsim.barrier_transport import BarrierLinkAttachment, BarrierTransportSpec, BarrierTransportEngine
from ncmemsim.transport import TransportEngine, TransportConfig


def make_plan(context, mode='active'):
    """Explicit assumed snapshot profiles, not a field-to-barrier constitutive law."""
    if mode == 'disabled': return BarrierTransportSpec(context.contract_hash)
    snapshot = context.snapshot
    physical = {row['name']: row['thickness_nm']*1e-9 for row in snapshot['device']['layers']}
    provenance = BarrierProvenance('assumed', 'synthetic S4 control provider',
        'prescribed profile at each captured snapshot, no measurement',
        'direct inter-FG replacement with unchanged heuristic supply factors',
        'fixed synthetic energies; no calibrated field response or interface matching')
    attachments = []
    for index, link in enumerate(row for row in snapshot['network']['links'] if row['kind']=='inter_fg'):
        fail = mode == 'partial_failure' and index == 0
        if fail: start, end, mass = 1e308, 1e308, 1e308
        elif mode == 'underflow': start, end, mass = 1e-12, 1e-12, .2
        else: start, end, mass = 4e-20, 3e-20, .2
        segments = [BarrierSegment(name, physical[name], start, end, mass, provenance)
                    for name in link['dielectric_layers']]
        profile = BarrierProfile('snapshot-profile-'+link['link_id'], segments, 0.,
            'synthetic common electron energy zero', link['left_node_id'],
            'network_left_to_right', 'along_positive_axis', link['left_node_id'],
            link['right_node_id'], 'prescribed synthetic per-snapshot barrier',
            'same incident energy for both directions; not a device current model')
        request = BarrierEvaluationSpec(profile, 1e-12, 1e-10, 'S4 synthetic integration controls')
        attachments.append(BarrierLinkAttachment(link['link_id'], request, link['dielectric_layers']))
    return BarrierTransportSpec(context.contract_hash, attachments, enabled=True)


def setup():
    device = DeviceBuilder.v2(3, inter_fg_sio2_nm=1.)
    physics = PhysicsModel.default()
    baseline = TransportEngine(physics.tunneling, TransportConfig(
        attempt_frequency_Hz=1e13, default_barrier_eV=.25, max_transfer_fraction_per_step=.5))
    state = DeviceState.empty_for_device(device)
    for index, weight in enumerate((1., .6, .1)):
        state.floating_gates[index].P0[:] = 1.-weight
        state.floating_gates[index].P1[:] = weight
        state.floating_gates[index].P2[:] = 0.
    field = FieldSolver1D().solve(device, 0., np.zeros(3))
    return device, physics, baseline, state, field


def electron_sheet(device, occupancy, state):
    return sum(2.*row.mean_normalized_occupation*TransportEngine._sheet_site_density(occupancy, fg)
               for fg, row in zip(device.floating_gates(), state.floating_gates))


def build_reference():
    cases = {}
    for mode in ('disabled', 'active', 'partial_failure', 'underflow'):
        device, physics, baseline, state, field = setup()
        engine = BarrierTransportEngine(baseline,
            provider=lambda context, mode=mode: make_plan(context, mode),
            provider_id='synthetic-s4-'+mode)
        before = electron_sheet(device, physics.occupancy, state)
        updated, result = engine.step(device, state, field, physics.occupancy, 1e-6)
        updated.validate(device)
        after = electron_sheet(device, physics.occupancy, updated)
        cases[mode] = dict(result=result.to_dict(), before_electron_sheet_m2=before,
            after_electron_sheet_m2=after, conservation_error_m2=after-before,
            final_mean_occupations=updated.mean_normalized_occupations.tolist())
    return dict(schema_version='phase-s4-barrier-transport-reference-v1',
        evidence_kind='synthetic_fixed_profile_integration_controls', cases=cases,
        profile_law='Prescribed synthetic energies, rebound to each current context; not inferred from device bias.',
        material_parameters_admitted=False, experimental_qualification=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(); text = json.dumps(build_reference(), indent=2, allow_nan=False)+'\n'
    if args.output is None: print(text, end='')
    else:
        with args.output.open('x', encoding='utf-8', newline='\n') as stream: stream.write(text)


if __name__ == '__main__': main()
