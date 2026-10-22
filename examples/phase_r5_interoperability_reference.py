# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Synthetic R5 exchange/comparison controls; no real TCAD or experimental evidence."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
from ncmemsim.interoperability import InteroperabilitySource, InteroperabilityDataset, ObservableMapping
from ncmemsim.interoperability_comparison import InteroperabilityComparison, compare_interoperability_data


def build_reference_comparisons():
    """Return owned controls plus the exact synthetic upstream JSON texts/digests."""
    metadata = {
        'geometry_materials': {'layers': 'synthetic planar profile, no device solver',
                              'contacts': 'two synthetic terminals'},
        'contacts_bias': {'contact_voltages': 'fixed synthetic control, 0 V reference'},
        'temperature_K': 300., 'history': {'sweep_direction': 'stored row order',
                                         'prior_operations': 'none; synthetic profile'},
        'initial_state': {'description': 'synthetic linear charge-density profile'},
        'time_conditions': {'description': 'static control; no transient simulation'},
        'frequency_conditions': {'description': 'synthetic small-signal control at 1 kHz'},
        'area_m2': 2e-12,
        'coordinates': {'origin': 'x=0 m at first reference row',
                        'axis_direction': 'positive x into reference stack',
                        'layer_order': 'single synthetic layer'},
        'potential_reference': {'description': 'synthetic zero at reference terminal'},
        'energy_reference': {'description': 'not used in these synthetic charge controls'},
        'electron_charge_sign': 'negative',
        'applicability': {'scope': 'software comparison controls only',
                          'limitations': 'no PDE solver, TCAD export or experimental qualification'},
        'optical_conditions': None}
    upstream = {}

    def dataset(label, xs, ys, *, candidate=False, missing=None, exclude=None, capacitance=False):
        meta = copy.deepcopy(metadata)
        if candidate:
            meta['coordinates']['axis_direction'] = 'negative source x into reference stack'
        if missing:
            meta[missing] = None
        quantity = 'small_signal_capacitance' if capacitance else ('total_charge' if candidate else 'charge_per_area')
        unit = 'F' if capacitance else ('C' if candidate else 'C/m^2')
        columns = [dict(name='x', quantity='position', unit='nm' if candidate else 'm', values=xs),
                   dict(name='signal', quantity=quantity, unit=unit, values=ys)]
        # These are genuine bytes of an explicitly synthetic upstream JSON document.
        text = json.dumps(dict(metadata=meta, columns=columns), sort_keys=True,
                          separators=(',', ':'), allow_nan=False)
        digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
        upstream[digest] = text
        source = InteroperabilitySource(label, digest, 'synthetic-r5-generator', '1',
            {'law': 'prescribed ordered arrays; no physical solver or fitting'},
            'NCMemSim R5 synthetic comparison control')
        data = InteroperabilityDataset(label, source, meta, columns, [] if exclude is None else exclude)
        # Exercise strict JSON interchange on every source dataset, not an ad-hoc parser.
        return InteroperabilityDataset.from_json(data.to_json())

    def comparison(label, *, ys=None, missing=None, xs=None, ref_exclude=None,
                   cand_exclude=None, target_missing=None, capacitance=False, atol=1e-14):
        left = dataset(label+'-reference', [0., 1e-9, 2e-9], [0., 1., 2.],
                       exclude=ref_exclude, capacitance=capacitance)
        right = dataset(label+'-candidate', [0., -1., -2.] if xs is None else xs,
                        ([0., 1., 2.] if capacitance else [0., 2e-12, 4e-12]) if ys is None else ys,
                        candidate=True, missing=missing, exclude=cand_exclude, capacitance=capacitance)
        quantity = 'small_signal_capacitance' if capacitance else 'charge_per_area'
        unit = 'F' if capacitance else 'C/m^2'
        maps = {}
        for side, data in [('reference',left), ('candidate',right)]:
            maps[side+'_axis'] = ObservableMapping(data.contract_hash, 'x', 'position', 'm',
                -1 if side=='candidate' else 1, 0., 'none',
                'Explicit source-axis direction to common positive x; nm to m where declared')
            maps[side+'_values'] = ObservableMapping(data.contract_hash, 'signal', quantity, unit,
                1, 0., 'divide_by_area' if side=='candidate' and not capacitance else 'none',
                'Synthetic total charge divided by declared source area, or explicit identity')
        target = copy.deepcopy(metadata)
        if target_missing:
            target[target_missing] = None
        return InteroperabilityComparison(left, right, maps, target,
            {'reference': 'Synthetic reference conditions are declared in the common target convention.',
             'candidate': 'Synthetic conditions match by construction; explicit x reversal and area conversion.'},
            axis_atol=1e-24, axis_rtol=1e-14, atol=atol, rtol=1e-14)

    excluded = [{'index':1, 'reason':'deliberately excluded synthetic row; retained in originals'}]
    cases = {
        'unit_axis_area_match': comparison('unit-axis-area'),
        'negative_value_mismatch': comparison('negative', ys=[0., 2e-12, 6e-12]),
        'missing_area': comparison('missing-area', missing='area_m2'),
        'missing_frequency': comparison('missing-frequency', missing='frequency_conditions', capacitance=True),
        'ordered_grid_mismatch': comparison('grid', xs=[0., -2., -1.]),
        'different_exclusion_masks': comparison('different-mask', ref_exclude=excluded),
        'matched_retained_subset': comparison('shared-mask', ref_exclude=excluded, cand_exclude=excluded),
        'missing_common_coordinates': comparison('target-missing', target_missing='coordinates'),
        'within_declared_tolerance': comparison('tolerance', ys=[0., 2e-12, 4.0000000002e-12], atol=2e-10)}
    return cases, upstream


def run_reference():
    cases, upstream = build_reference_comparisons()
    results = {name: compare_interoperability_data(InteroperabilityComparison.from_json(case.to_json()))
               for name, case in cases.items()}
    expected = {'unit_axis_area_match':'matched', 'negative_value_mismatch':'mismatched',
        'missing_area':'unavailable', 'missing_frequency':'unavailable',
        'ordered_grid_mismatch':'unavailable', 'different_exclusion_masks':'unavailable',
        'matched_retained_subset':'matched', 'missing_common_coordinates':'unavailable',
        'within_declared_tolerance':'matched'}
    if {name:result['status'] for name,result in results.items()} != expected:
        raise ValueError('synthetic reference control outcome changed')
    return dict(evidence_kind='synthetic_software_controls', upstream_sources=upstream,
        results=results, expected_statuses=expected,
        external_agreement=False, experimental_qualification=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='new JSON evidence file; never overwrite')
    args = parser.parse_args()
    evidence = run_reference()
    if args.output is not None:
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(evidence, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({name:result['status'] for name,result in evidence['results'].items()}, indent=2))
