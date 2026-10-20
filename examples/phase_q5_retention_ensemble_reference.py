# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Synthetic independent retention and manifest-bound FG-fraction variation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from examples.phase_q3_multilevel_reference import build_plan
from ncmemsim.multilevel_contracts import PulseSequenceEvidence, WeightReferenceMapping, _load
from ncmemsim.multilevel_analysis import run_multilevel_study
from ncmemsim.multilevel_retention import MultilevelRetentionPlan, MultilevelRetentionResult, run_multilevel_retention
from ncmemsim.multilevel_ensemble import MultilevelEnsemblePlan, MultilevelEnsembleResult, run_multilevel_ensemble
from ncmemsim.ensemble import (ConstantDistribution, UniformDistribution, EnsembleSpec, StochasticVariable,
    PhysicalDomain, SamplingSpec, RNGSpec, generate_sample_manifest)
from ncmemsim.dtco import ParameterBinding, BindingScope
from ncmemsim.materials.provenance import ParameterProvenance, ParameterStatus

EVIDENCE = PulseSequenceEvidence('Q5 synthetic study', 'example code', 'synthetic',
    'Short numerical delay probes and assumed between-device fraction distributions; no lifetime, noise or yield inference.')


def build_study():
    return build_plan(internal_dt_s=1e-8)


def build_ensemble_plan(study, *, varied=False, sample_count=2):
    device = study.levels[0].experiment.context.device
    nominal = device.floating_gates()[0].electrically_active_fraction
    distribution = UniformDistribution(.8*nominal, nominal) if varied else ConstantDistribution(nominal)
    variable = StochasticVariable('FG1 active fraction',
        ParameterBinding(BindingScope.DEVICE, ('layers', 'FG1', 'electrically_active_fraction')),
        distribution, '1', PhysicalDomain(lower=0., upper=1.),
        ParameterProvenance(source='Q5 assumed fraction distribution', status=ParameterStatus.ASSUMED),
        'fixed grid and histories; between-device active fraction assumption', nominal_value=nominal)
    spec = EnsembleSpec.from_device(name='Q5 '+('varied' if varied else 'zero variation'),
                                    device=device, variables=(variable,))
    manifest = generate_sample_manifest(SamplingSpec(spec, RNGSpec(seed=1805), sample_count))
    return MultilevelEnsemblePlan(study, manifest, (0., 1e-7, 2e-7), 0., 1e-8, EVIDENCE)


def run_reference():
    study = build_study()
    prepared = run_multilevel_study(study)
    first = study.levels[0].experiment
    reference = WeightReferenceMapping('Q5 assumed fixed window', first.context.context_hash,
        first.sequence.readout.contract_hash, -.02, 0., .001, 'assumed -20 mV', 'assumed 0 V',
        'this nominal context and common dark read only', EVIDENCE)
    retention = run_multilevel_retention(MultilevelRetentionPlan(prepared, (0., 1e-7, 2e-7), 0., 1e-8, EVIDENCE, reference))
    zero = run_multilevel_ensemble(build_ensemble_plan(study))
    varied = run_multilevel_ensemble(build_ensemble_plan(study, varied=True))
    return {'nominal_retention': retention.to_dict(), 'zero_variation': zero.to_dict(), 'varied': varied.to_dict()}


def restore(raw):
    if type(raw) is not dict or set(raw) != {'nominal_retention', 'zero_variation', 'varied'}:
        raise ValueError('unsupported Q5 reference fields')
    return {'nominal_retention': MultilevelRetentionResult.from_dict(raw['nominal_retention']).to_dict(),
            'zero_variation': MultilevelEnsembleResult.from_dict(raw['zero_variation']).to_dict(),
            'varied': MultilevelEnsembleResult.from_dict(raw['varied']).to_dict()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--input', type=Path)
    args = parser.parse_args()
    result = restore(_load(args.input.read_text(encoding='utf-8'))) if args.input else run_reference()
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({key: value['summary'] for key, value in result.items()}, allow_nan=False))
