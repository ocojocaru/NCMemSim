# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""S7 preparation: retained v1.9 sources, additive S APIs and frozen S6 archive."""
from __future__ import annotations
import argparse
import importlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from scripts.validate_api_contract import build_inventory
from scripts import validate_v1_9_api_review as published
from scripts.validate_v1_4_api_review import _version
from ncmemsim.performance_contracts import _hash, _unique, _reject
from ncmemsim.barrier_reporting import BarrierStudyReport

MODULES=tuple('ncmemsim.'+name for name in (
    'barrier_contracts','barrier_evaluation','barrier_transport','barrier_reporting'))
ARCHIVE='tests/fixtures/archives/v1_10_preparation/barrier_report.json'
ARCHIVE_SHA256='f7e101d5158f8188e00aa5c0c37a0c1c02424175bc8e91e7be6c93dbe4c7fa7d'
CAPTURE_COMMIT='8264b7e69ff1985716c226c466640b57c2ed96ac'
REVIEW='docs/v1_10_api_review.json'
EXPECTED_SUMMARY=dict(attempted_count=33,completed_count=32,failed_count=1,
    matched_count=30,mismatched_count=1,unavailable_count=2,transmission_underflow_count=1,
    experimental_qualification=False,model_uncertainty_estimated=False)


def _json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=_unique,parse_constant=_reject)


def _archive(root):
    raw=_json(Path(root)/ARCHIVE)
    if _hash(raw)!=ARCHIVE_SHA256:
        raise ValueError('frozen S6 preparation archive drift')
    report=BarrierStudyReport.from_dict(raw)
    if report.contract_hash!=ARCHIVE_SHA256 or raw['summary']!=EXPECTED_SUMMARY:
        raise ValueError('frozen S6 outcomes changed')
    return report


def build_review(root):
    root=Path(root)
    # This independent gate pins all 146 original sources and the published
    # v1.9 surface digest. Regenerating the S review cannot bless old-source drift.
    if _json(root/'docs/v1_9_api_review.json')!=published.build_review(root):
        raise ValueError('retained v1.9 review drift')
    report=_archive(root)
    inventory={m['module']:m for m in build_inventory(root)['modules']}
    surface=[]
    for name in MODULES:
        module=importlib.import_module(name); exports=list(module.__all__)
        if exports!=inventory[name]['explicit_exports'] or len(exports)!=len(set(exports)):
            raise ValueError('S additive runtime/source export mismatch')
        if any(not hasattr(module,item) for item in exports):
            raise ValueError('S additive missing runtime export')
        surface.append(dict(module=name,exports=exports,source_contract=inventory[name],
            source_sha256=published._text_hash(root/inventory[name]['source'])))
    if sum(len(row['exports']) for row in surface)!=16:
        raise ValueError('unreviewed S export count')
    return dict(schema_version='phase-s-v1.10-preparation-api-review-v1',
        status='preparation_only',target_release='1.10.0',published_baseline='1.9.0',
        package_identity_at_review=_version(root),review_date='2026-11-04',
        implementation_source_commit=CAPTURE_COMMIT,
        version_rationale='Minor additive release: four module-qualified APIs with 16 exports; all 146 published v1.9 module sources/defaults retained. No major-version contract break.',
        retained_v1_9_review_sha256=_hash(_json(root/'docs/v1_9_api_review.json')),
        retained_v1_9_surface_sha256=published.PUBLISHED_V19_SURFACE_SHA256,
        retained_published_module_count=146,
        additive_module_qualified_surface=surface,
        preparation_archive=dict(path=ARCHIVE,report_hash=report.contract_hash,
            capture_source_commit=CAPTURE_COMMIT,capture_source_dirty=False,
            capture_package_version='1.9.0',evidence_kind='synthetic_isolated_action_controls',
            summary=EXPECTED_SUMMARY),
        scientific_limits=[
            'Piecewise-linear electron action only; no coherent interface matching, resonances or current supply model.',
            'S4 replaces direct inter-FG transmission only on explicit snapshot/geometry-bound attachments.',
            'No substrate injection replacement, TAT/image-force composition or automatic field-to-barrier law.',
            'S6 archives isolated action diagnostics, not S4 simulator/provider histories.',
            'S3 negative/unavailable reference evidence remains retained; no universal legacy-kernel equivalence.',
            'No new admitted experimental data, physical uncertainty, yield or lifetime; P4B/P5B/P6B deferred.'],
        publication=dict(final_candidate=False,exact_preparation_commit_ci='pending user commit/push',
            pr_main_tag_release='not performed',version_doi=None))


def validate(root):
    root=Path(root)
    if _json(root/'docs/api_inventory.json')!=build_inventory(root):
        raise ValueError('API inventory drift')
    if _json(root/REVIEW)!=build_review(root):
        raise ValueError('v1.10 preparation review/source drift')
    if _version(root)!='1.9.0':
        raise ValueError('preparation must retain published 1.9.0 identity')
    checklist=(root/'docs/v1_10_release_checklist.md').read_text(encoding='utf-8')
    for marker in ('Target release: `1.10.0`','Preparation identity: `1.9.0`',
                   'Python 3.11, 3.12 and 3.13','P4B/P5B/P6B','not a final candidate'):
        if marker not in checklist: raise ValueError('S7 checklist marker missing')
    return dict(status='s7_preparation_consistency_pass',target_release='1.10.0',
        package_version='1.9.0',retained_published_modules=146,reviewed_modules=4,
        additive_exports=16,report_hash=ARCHIVE_SHA256,archive_summary=EXPECTED_SUMMARY,
        final_candidate=False,remote_exact_commit_ci='pending user commit/push')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-review',action='store_true'); args=parser.parse_args()
    if args.write_review:
        (ROOT/REVIEW).write_text(json.dumps(build_review(ROOT),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(validate(ROOT),indent=2))
