# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Controlled action sensitivity; prescribed inputs, not calibrated device design."""
from __future__ import annotations
import argparse
from decimal import Decimal, localcontext
import itertools
import json
import math
from pathlib import Path
from ncmemsim.barrier_contracts import (
    BarrierProvenance, BarrierSegment, BarrierProfile, BarrierEvaluationSpec,
    barrier_energy_eV_to_J,
)
from ncmemsim.barrier_evaluation import evaluate_barrier_profile
from ncmemsim.constants import ELECTRON_MASS_KG, HBAR_J_S

BASE = dict(length_m=2e-9, potential_eV=.4, mass_m0=.2, incident_eV=.1)
AXES = dict(length_m=(1e-9, 2e-9, 4e-9), potential_eV=(.2, .4, .8),
            mass_m0=(.1, .2, .4), incident_eV=(0., .1, .3, .4, .5))


def request(parameters, parts=1):
    if type(parts) is not int or parts < 1:
        raise ValueError('positive integer parts required')
    p = parameters
    provenance = BarrierProvenance('assumed', 'S5 synthetic rectangular controls',
        'prescribed inputs, no measurements', 'isolated electron action sensitivity',
        'no interface matching, voltage law, supply statistics or device qualification')
    energy = barrier_energy_eV_to_J(p['potential_eV'])
    segments = [BarrierSegment(str(i), p['length_m']/parts, energy, energy,
                               p['mass_m0'], provenance) for i in range(parts)]
    profile = BarrierProfile('s5-control', segments,
        barrier_energy_eV_to_J(p['incident_eV']), 'common synthetic energy zero',
        'left boundary', 'left to right', 'along_positive_axis', 'left', 'right',
        'rectangular barrier control', 'same-energy action only; no current model')
    return BarrierEvaluationSpec(profile, 1e-12, 1e-10, 'S1 prospective exponent tolerances')


def reference(specification):
    """100-digit rectangular expression using the actual declared SI inputs."""
    profile = specification.to_dict()['profile']
    with localcontext() as context:
        context.prec = 100
        d = Decimal
        value = sum((d(row['length_m'])*(2*d(ELECTRON_MASS_KG)*
            d(row['effective_mass_m0'])*max(d(row['start_potential_energy_J'])-
            d(profile['incident_energy_J']), d(0))).sqrt()
            for row in profile['segments']), d(0))*2/d(HBAR_J_S)
        result = float(value)
    return result if math.isfinite(result) else None


def point(label, parameters, parts=1):
    spec = request(parameters, parts)
    result = evaluate_barrier_profile(spec).to_dict()
    expected = reference(spec)
    actual = result['summary']['wkb_exponent']
    error = None if actual is None or expected is None else abs(actual-expected)
    limit = None if expected is None else 1e-12+1e-10*abs(expected)
    return dict(label=label, parameters=dict(parameters), subdivision_count=parts,
        result=result, reference_exponent=expected, absolute_error=error,
        acceptance_limit=limit, comparison='unavailable' if error is None else
        ('matched' if error <= limit else 'mismatched'))


def build_reference():
    baseline = point('baseline', BASE)
    sweeps = {axis: [point(axis+'-'+str(i), dict(BASE, **{axis: value}))
                    for i, value in enumerate(values)] for axis, values in AXES.items()}
    # A factorial thickness/height design exposes joint effects without ranking
    # candidates by a device objective which this action model cannot establish.
    design = [point('design-'+str(i), dict(BASE, length_m=length, potential_eV=height))
              for i, (length, height) in enumerate(itertools.product(
                  AXES['length_m'], AXES['potential_eV']))]
    controls = [point('underflow', dict(BASE, potential_eV=1e7)),
                point('numeric_failure', dict(BASE, length_m=1e308, mass_m0=1e308))]
    refinement = [point('split-'+str(n), BASE, n) for n in (1, 2, 7, 16, 64)]
    rows = [baseline]+[row for group in sweeps.values() for row in group]+design+controls+refinement
    counts = dict(attempted=len(rows), completed=sum(row['result']['summary']['status']=='completed' for row in rows),
        failed=sum(row['result']['summary']['status']=='failed' for row in rows),
        matched=sum(row['comparison']=='matched' for row in rows),
        mismatched=sum(row['comparison']=='mismatched' for row in rows),
        unavailable=sum(row['comparison']=='unavailable' for row in rows))
    return dict(schema_version='phase-s5-barrier-sensitivity-v1', baseline=baseline,
        sweeps=sweeps, design=design, controls=controls, subdivision_controls=refinement,
        counts=counts, evidence_kind='synthetic_isolated_action_sensitivity',
        experimental_qualification=False, model_uncertainty_estimated=False,
        numerical_policy=dict(exponent_atol=1e-12, exponent_rtol=1e-10),
        limits=['No material distribution or confidence interval is inferred.',
                'Subdivision tests numerical invariance of the same rectangular profile.',
                'Parameter sensitivity is not numerical error or experimental uncertainty.',
                'No current, retention lifetime, yield or optimal device is inferred.',
                'No S4 attachment is made; thickness variation would require a matching device geometry.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    text = json.dumps(build_reference(), indent=2, allow_nan=False)+'\n'
    if args.output is None:
        print(text, end='')
    else:
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(text)


if __name__ == '__main__':
    main()
