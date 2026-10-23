# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""R7 v1.9 preparation: retained published surface, additive API and strict frozen report."""
from __future__ import annotations
import argparse
import importlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.validate_api_contract import build_inventory
from scripts.validate_v1_8_api_review import validate as validate_published
from scripts.validate_v1_4_api_review import _version
from ncmemsim.performance_contracts import _hash, _unique, _reject
from ncmemsim.performance_reporting import PerformanceInteroperabilityReport

MODULES=tuple('ncmemsim.'+name for name in ('performance_contracts','performance_execution',
    'performance_workloads','interoperability','interoperability_comparison','performance_reporting'))
ARCHIVE='tests/fixtures/archives/v1_9_preparation/performance_report.json'
SURFACE='docs/v1_8_published_surface.json'
SURFACE_SHA256='196a6a216740382dbbd8f06df4429187db703dcb03813603ab7662063b1d4790'
ARCHIVE_SHA256='75fbc26f082f99602c63df5bf2466c0d14575b305483a92ba71060db3948ea28'
CAPTURE_COMMIT='e2af7e7cad2147755c71743e0b20c403b79fc081'
EXPECTED_STATUSES={'unit_axis_area_match':'matched','negative_value_mismatch':'mismatched',
    'missing_area':'unavailable','missing_frequency':'unavailable','ordered_grid_mismatch':'unavailable',
    'different_exclusion_masks':'unavailable','matched_retained_subset':'matched',
    'missing_common_coordinates':'unavailable','within_declared_tolerance':'matched'}


def _json(path):
    return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=_unique,parse_constant=_reject)


def _text_hash(path):
    import hashlib
    return hashlib.sha256(path.read_text(encoding='utf-8').replace('\r\n','\n').encode('utf-8')).hexdigest()


def _surface(module):
    return {key:module[key] for key in ('module','explicit_exports','public_source_definitions')} | {
        'public_package_import_aliases':{key:value for key,value in module['package_import_aliases'].items()
                                         if not key.startswith('_')}}


def _retained_surface(root, inventory):
    baseline=_json(root/SURFACE)
    if _hash(baseline)!=SURFACE_SHA256:
        raise ValueError('published source-surface baseline drift')
    for item in baseline['modules']:
        current=inventory.get(item['module'])
        if current is None or _hash(_surface(current))!=item['surface_sha256']:
            raise ValueError('published v1.8 public surface changed: '+item['module'])
    return baseline


def _archive(root):
    raw=_json(root/ARCHIVE)
    if _hash(raw)!=ARCHIVE_SHA256:
        raise ValueError('frozen R7 preparation report drift')
    report=PerformanceInteroperabilityReport.from_dict(raw)
    if report.contract_hash!=ARCHIVE_SHA256:
        raise ValueError('frozen report reconstruction drift')
    if len(raw['campaigns'])!=5 or len(raw['comparisons'])!=9:
        raise ValueError('incomplete R7 archive family coverage')
    observed=raw['campaigns'][0]['archive']
    env=observed['campaign']['environment']
    if observed['evidence_kind']!='observed_campaign' or env['source_commit']!=CAPTURE_COMMIT or env['source_dirty']:
        raise ValueError('original clean observed source identity must remain unchanged')
    if env['source_package_version']!='1.8.0' or not observed['campaign']['summary']['complete']:
        raise ValueError('original observation/version incomplete')
    if any(row['archive']['evidence_kind']!='synthetic_control' for row in raw['campaigns'][1:]):
        raise ValueError('synthetic records must not be promoted to observations')
    statuses={row['label']:row['result']['status'] for row in raw['comparisons']}
    if statuses!=EXPECTED_STATUSES or raw['summary']['experimental_qualification'] or raw['summary']['speedup_accepted']:
        raise ValueError('negative/unavailable/synthetic scope changed')
    return report


def build_review(root):
    root=Path(root);inventory={m['module']:m for m in build_inventory(root)['modules']}
    baseline=_retained_surface(root,inventory);report=_archive(root)
    surface=[]
    for name in MODULES:
        module=importlib.import_module(name);exports=list(module.__all__)
        if len(exports)!=len(set(exports)) or any(not hasattr(module,value) for value in exports):
            raise ValueError('invalid additive API export: '+name)
        if exports!=inventory[name]['explicit_exports']:
            raise ValueError('runtime/source exports disagree: '+name)
        surface.append(dict(module=name,exports=exports,source_contract=inventory[name],
                            source_sha256=_text_hash(root/(name.replace('.','/')+'.py'))))
    package={p.relative_to(root/'ncmemsim').as_posix():_text_hash(p)
             for p in sorted((root/'ncmemsim').rglob('*.py'))}
    return dict(schema_version='phase-r-v1.9-preparation-api-review-v1',status='preparation_review',
        target_release='1.9.0',published_baseline='1.8.0',package_identity_at_review=_version(root),
        review_date='2026-10-23',implementation_source_commit=CAPTURE_COMMIT,
        version_rationale='Minor additive release: six new module-qualified APIs; 140 published module surfaces unchanged; R3 private optimization preserves signatures, defaults and archives. No major-version contract break.',
        retained_v1_8_review_sha256=_hash(_json(root/'docs/v1_8_api_review.json')),
        retained_published_surface_sha256=SURFACE_SHA256,retained_published_module_count=len(baseline['modules']),
        reviewed_package_sha256=_hash(package),additive_module_qualified_surface=surface,
        preparation_archive=dict(path=ARCHIVE,report_hash=report.contract_hash,
            observed_source_commit=CAPTURE_COMMIT,observed_source_dirty=False,source_package_version='1.8.0',
            campaign_count=5,comparison_count=9,
            scope='One actual bounded fresh-process timing campaign, four explicitly synthetic campaign controls, nine R5 synthetic comparison cases; original identities and negative/unavailable outcomes retained.'),
        reviewed_ci_evidence=dict(source_commit=CAPTURE_COMMIT,ci_run=39772236419,documentation_run=39772236453,
            conclusion='success',test_python_versions=['3.11','3.12','3.13'],
            distribution_python_versions=['3.11','3.12','3.13'],
            serial_baselines='Ubuntu/Windows x Python 3.11/3.13, current R6 checkout',
            paired_comparison='Historical R3 commit 8c63a0a against R2 commit 6034231; not current-tree speedup evidence'),
        scientific_limits=[
            'No real TCAD export, proprietary adapter or full co-simulation is admitted.',
            'Synthetic comparisons and declared applicability do not establish external agreement.',
            'No new independent measured data or fitted physical coefficients; P4B/P5B/P6B remain deferred.',
            'R3 speedups concern reviewed same-host archive operations only, not a universal solver speedup.',
            'Timing, native RSS, host and workload scopes remain separate; no pooled performance claim.',
            'Static archive checks verify consistency, not authenticity or replayed dynamics.'],
        release_policy='Preparation only: exact new-commit CI, final identity review, PR/main/tag checks, release publication and Zenodo archival remain pending. No v1.9 DOI is invented.')


def validate(root):
    root=Path(root)
    if _json(root/'docs/api_inventory.json')!=build_inventory(root):
        raise ValueError('source API inventory drift')
    if _json(root/'docs/v1_9_api_review.json')!=build_review(root):
        raise ValueError('v1.9 preparation source/API/archive drift')
    if _version(root)!='1.8.0':
        raise ValueError('preparation retains published 1.8.0 identity; final candidate is a separate gate')
    previous=validate_published(root)
    if (previous['retained_stable_paths'],previous['stable_ensemble_exports'],previous['additive_exports'])!=(297,59,34):
        raise ValueError('published contract retention mismatch')
    markers={'docs/v1_9_release_checklist.md':('Target release: `1.9.0`','Preparation identity: `1.8.0`',
                'P4B/P5B/P6B','Python 3.11, 3.12 and 3.13','not a final release candidate'),
             'docs/roadmap.md':('R7 preparation','v1.9.0','experimental qualification remains deferred')}
    for path,words in markers.items():
        if any(word not in (root/path).read_text(encoding='utf-8') for word in words):
            raise ValueError('R7 scope/checklist marker missing: '+path)
    return dict(status='r7_preparation_consistency_pass',target_release='1.9.0',package_version=_version(root),
        retained_published_modules=140,retained_stable_paths=297,stable_ensemble_exports=59,
        reviewed_modules=len(MODULES),additive_exports=sum(len(importlib.import_module(name).__all__) for name in MODULES),
        report_hash=ARCHIVE_SHA256,campaign_count=5,comparison_count=9,experimental_qualification=False,
        exact_new_commit_ci='pending after push',final_candidate='pending')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-review',action='store_true')
    args=parser.parse_args()
    if args.write_review:
        (ROOT/'docs/v1_9_api_review.json').write_text(json.dumps(build_review(ROOT),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(validate(ROOT),indent=2))
