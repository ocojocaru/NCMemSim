# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Restore an M6 thermal report from stored M5 DTCO evidence, without replay."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ncmemsim.hashing import canonical_hash
from ncmemsim.temperature_context import _dump, _load, _keys
from ncmemsim.thermal_reporting import (ThermalReportStudy, build_thermal_report,
    write_thermal_report, load_thermal_report_bundle)


def report_from_reference(evidence):
    _keys(evidence,('schema_version','scope','experiment','deterministic','model_pareto',
        'paired_density_values','timestep_audit','limits','reference_hash'))
    if evidence['schema_version']!='m5-thermal-dtco-reference-v1':raise ValueError('unsupported M5 source')
    if evidence['reference_hash']!=canonical_hash({k:v for k,v in evidence.items() if k!='reference_hash'}):
        raise ValueError('M5 source integrity mismatch')
    studies=(ThermalReportStudy('deterministic thermal DTCO','deterministic_dtco',_dump(evidence['deterministic'])),
        ThermalReportStudy('paired thermal MODEL DTCO','model_dtco',_dump({'experiment':evidence['experiment'],'pareto':evidence['model_pareto']})))
    deterministic=studies[0].to_dict()['source']['source_analysis']['source_sweep']['experiment']
    if _dump(deterministic)!=_dump(evidence['experiment']):raise ValueError('experiment/source mismatch')
    return build_thermal_report('M6 conditional thermal DTCO',studies,
        limitations=(evidence['scope'],*evidence['limits'],
            'Restoration checks input/analysis consistency; observations are stored evidence, not replayed physics or authenticated measurements.'),
        evidence={'reference_hash':evidence['reference_hash'],'paired_density_values':evidence['paired_density_values'],
            'timestep_audit':evidence['timestep_audit'],'audit_semantics':'declared stored numerical audit; no transport replay'})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=report_from_reference(_load(args.input.read_text(encoding='utf-8')))
    write_thermal_report(report,args.output)
    restored=load_thermal_report_bundle(args.output)
    print(restored.report_hash)
