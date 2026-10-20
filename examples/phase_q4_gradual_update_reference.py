# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Synthetic Q4 electrical updates and matched fixed-spectrum optical pulse train."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ncmemsim import DeviceBuilder, DeviceState
from ncmemsim.materials import make_ge
from ncmemsim.temperature_context import ThermalContext
from ncmemsim.multilevel_contracts import (PulseSequenceEvidence, ElectricalPulseStep,
    DarkReadoutPolicy, ElectricalPulseSequence, ElectricalSequenceExperiment, WeightReferenceMapping, _load)
from ncmemsim.multilevel_execution import run_electrical_sequence
from ncmemsim.multilevel_optical import (OpticalSequenceExperiment, MatchedOpticalSequenceResult,
    OpticalSequenceResult, run_matched_optical_sequence)
from ncmemsim.multilevel_updates import (GradualUpdateAnalysis, PairedUpdateAnalysis,
    analyze_gradual_updates, analyze_paired_updates)
from ncmemsim.spectral_sources import SpectralEvidence, DiscreteLineSpectrum
from ncmemsim.spectral_absorption import SpectralAbsorptionProfile
from ncmemsim.spectral_stack import SpectralStackLayer
from ncmemsim.spectral_context import build_spectral_simulation_context


def build(n_fgs=1, internal_dt_s=1e-9, *, enabled=True, capture=.1):
    device = DeviceBuilder.v2(n_fgs=n_fgs, nc_material=make_ge(), nc_volume_fraction=.2,
                              active_fraction=.1, fg_thickness_nm=6)
    for fg in device.floating_gates():
        fg.grid_points = 3
    context = ThermalContext.from_nominal(device).resolve()
    evidence = PulseSequenceEvidence('Q4 synthetic reference', 'example code', 'synthetic',
        'Assumed fixed reference [-0.1,0] V, 1 microvolt excursion criterion; no measured conductance or noise.')
    read = DarkReadoutPolicy('common-dark-0V', 0., evidence)
    reference = WeightReferenceMapping('assumed fixed proxy', context.context_hash, read.contract_hash,
        -.1, 0., .01, 'assumed -0.1 V endpoint', 'assumed zero V endpoint',
        'this fixed model context and dark read only; no measured calibration', evidence)
    def experiment(name, voltage, occupied=False):
        steps = tuple(ElectricalPulseStep(f'{name}-{k}', 'program' if voltage > 0 else 'erase',
                      voltage, 1e-7, internal_dt_s) for k in range(4))
        sequence = ElectricalPulseSequence(name, steps, read, evidence)
        state = DeviceState.empty_for_device(device)
        if occupied:
            for gate in state.floating_gates:
                gate.P0[:] = .8
                gate.P1[:] = .2
        return ElectricalSequenceExperiment.from_state(name, context, sequence, state, reference)
    loading, unloading = experiment('loading', 6.), experiment('unloading', -6., True)
    se = SpectralEvidence('Q4 assumed source and passive profiles', 'example code', 'ASSUMED',
        'SI irradiance and wavelength in nm', (), 'discrete 1550 nm line', 'unknown',
        'Synthetic bulk-Ge absorption; transparent passive layers, no reflection/interference or measured source.')
    source = DiscreteLineSpectrum((1550.,), (1e6,), se, enabled)
    passive = tuple(SpectralStackLayer(SpectralAbsorptionProfile(layer.name, source.wavelength_nm, (0.,),
        layer.thickness_nm*1e-9, 1500., 1600., se), 'passive', 'assumed_transparent')
        for layer in context.device.layers if layer.role != 'floating_gate')
    spectral = build_spectral_simulation_context(context, source, direction='gate_to_substrate',
        passive_layers=passive, wavelength_min_nm=1500., wavelength_max_nm=1600., evidence=se)
    optical = OpticalSequenceExperiment(loading, spectral, tuple(s.step_id for s in loading.sequence.steps),
                                        capture, (1., 1., 0., 0.), 1e-8)
    return loading, unloading, optical, reference


def run_reference():
    loading, unloading, optical, reference = build()
    first = analyze_gradual_updates(run_electrical_sequence(loading), reference,
        expected_direction='decreasing', minimum_excursion_V=1e-6)
    second = analyze_gradual_updates(run_electrical_sequence(unloading), reference,
        expected_direction='increasing', minimum_excursion_V=1e-6)
    matched = run_matched_optical_sequence(optical)
    light = analyze_gradual_updates(OpticalSequenceResult.from_dict(matched.to_dict()['light']), reference,
        expected_direction='decreasing', minimum_excursion_V=1e-6)
    return {'electrical_loading': first.to_dict(), 'electrical_unloading': second.to_dict(),
            'paired_updates': analyze_paired_updates(first, second).to_dict(),
            'matched_optical': matched.to_dict(), 'optical_updates': light.to_dict()}


def restore(raw):
    if set(raw) != {'electrical_loading', 'electrical_unloading', 'paired_updates', 'matched_optical', 'optical_updates'}:
        raise ValueError('unsupported reference example fields')
    restored = {k: GradualUpdateAnalysis.from_dict(raw[k]).to_dict() for k in
                ('electrical_loading', 'electrical_unloading', 'optical_updates')}
    restored['paired_updates'] = PairedUpdateAnalysis.from_dict(raw['paired_updates']).to_dict()
    restored['matched_optical'] = MatchedOpticalSequenceResult.from_dict(raw['matched_optical']).to_dict()
    pair = restored['paired_updates']
    if pair['first'] != restored['electrical_loading'] or pair['second'] != restored['electrical_unloading']:
        raise ValueError('example paired branch mismatch')
    if restored['optical_updates']['source'] != restored['matched_optical']['light']:
        raise ValueError('example optical source mismatch')
    if restored['electrical_loading']['source'] != restored['matched_optical']['dark']:
        raise ValueError('example dark control source mismatch')
    return restored


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--input', type=Path)
    args = parser.parse_args()
    result = restore(_load(args.input.read_text(encoding='utf-8'))) if args.input else run_reference()
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({key: value['summary'] for key, value in result.items()}, allow_nan=False))
