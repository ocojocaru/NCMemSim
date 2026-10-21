# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Published Q7 API/archive and scientific-scope consistency review."""
from __future__ import annotations
import argparse
import importlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.validate_api_contract import build_inventory
from scripts.validate_v1_7_api_review import validate_retained as retained_review
from scripts.validate_v1_5_api_review import _text_hash
from scripts.validate_v1_4_api_review import _json, _version
from scripts.validate_v1_2_release_identity import _semantic_json_digest

MODULES=tuple('ncmemsim.'+name for name in (
    'multilevel_contracts','multilevel_execution','multilevel_analysis','multilevel_updates',
    'multilevel_optical','multilevel_retention','multilevel_ensemble','multilevel_reporting'))
ARCHIVE='tests/fixtures/archives/v1_8_preparation/multilevel_report.json'
SNAPSHOTS=('README.md', 'CHANGELOG.md', 'CITATION.cff', 'ncmemsim/_version.py', 'docs/index.md', 'docs/roadmap.md', 'docs/archival_citation.md', 'docs/independent_calibration.md', 'docs/v1_7_release_checklist.md', '.github/workflows/ci.yml', '.github/workflows/docs.yml')


def build_review(root):
    inventory={item['module']:item for item in build_inventory(root)['modules']}
    surface=[]
    for name in MODULES:
        module=importlib.import_module(name)
        exports=list(module.__all__)
        if len(exports)!=len(set(exports)) or any(not hasattr(module,item) for item in exports):
            raise ValueError('invalid v1.8 exports: '+name)
        surface.append({'module':name,'exports':exports,'source_contract':inventory[name],
                        'source_sha256':_text_hash(root/(name.replace('.','/')+'.py'))})
    return {'schema_version':'multilevel-v1_8-final-candidate-api-review-v1',
        'status':'published_contracts_review',
        'target_release':'1.8.0','published_baseline':'1.7.0','package_identity_at_review':'1.8.0',
        'candidate_date':'2026-10-20','implementation_source_commit':'ef3db539489f523241a2aada4183deb3a29158c5',
        'approved_scope':'Q1-Q6 electrical/matched optical multilevel diagnostics, bounded retention/ensemble adapters and strict reports',
        'retained_v1_7_review_sha256':_semantic_json_digest(root/'docs/v1_7_api_review.json'),
        'published_v1_7_snapshot_sha256':{name:_text_hash(root/'tests/fixtures/releases/v1_7_0'/name) for name in SNAPSHOTS},
        'frozen_report_sha256':_semantic_json_digest(root/ARCHIVE),
        'archive_scope':'compact synthetic preparation snapshot from package 1.7.0; not a published or dev-version 1.8 archive',
        'additive_module_qualified_surface':surface,
        'scientific_limits':[
            'No new admitted independent measured dataset or calibrated parameter; P4B/P5B/P6B remain deferred.',
            'Signed delta-VFB and fixed-reference weight proxies are not conductance, circuit MAC or application accuracy.',
            'Q4 uses one fixed spectrum and explicit dark controls; optical budgets are not total programming energy.',
            'Q5 retention accepts Q3 electrical preparations and independent dark delays; no lifetime or endurance claim.',
            'Q5 ensemble bindings are FG electrically_active_fraction and nc_volume_fraction; no nominal weight-reference rebinding.',
            'No cycle noise, read noise, universal capacity or manufacturing yield inferred from synthetic diagnostics.',
            'Report cases can share trajectories; case counts are not independent statistical sample counts.',
            'Hashes and static projections verify consistency, not authenticity or replayed trajectories.'],
        'release_policy':'full regression, docs and separately installed wheel/sdist; exact-commit Python 3.11-3.13 matrix; candidate/PR/main/tag checks and release publication passed; Zenodo DOI 10.5281/zenodo.23510004 verified; P4B/P5B/P6B remain deferred'}


def validate(root):
    if _json(root/'docs/api_inventory.json')!=build_inventory(root):
        raise ValueError('API inventory drift')
    if _json(root/'docs/v1_8_api_review.json')!=build_review(root):
        raise ValueError('v1.8 review/source/archive drift')
    from scripts.validate_v1_8_release_identity import validate_identity
    validate_identity(root)
    previous=retained_review(root)
    if previous['retained_stable_paths']!=297 or previous['stable_ensemble_exports']!=59:
        raise ValueError('retained published surface mismatch')
    from ncmemsim.multilevel_reporting import MultilevelReport
    raw=_json(root/ARCHIVE)
    report=MultilevelReport.from_dict(raw)
    if report.to_dict()!=raw or set(c.kind for c in report.cases)!={
        'electrical','separation','updates','paired_updates','optical','matched_optical','retention','ensemble'}:
        raise ValueError('incomplete frozen report family coverage')
    statuses=[item['status'] for item in report.summary['cases']]
    if 'failed' not in statuses or 'not_assessable' not in statuses or report.summary['experimental_qualification']:
        raise ValueError('negative/undefined archive evidence must remain unqualified')
    markers={
        'docs/v1_8_release_checklist.md':('Published identity: `1.8.0`','Latest published stable: `1.8.0`','P4B/P5B/P6B','Python 3.11, 3.12 and 3.13'),
        'docs/roadmap.md':('Q7 is complete','experimental qualification remains deferred')}
    for name,words in markers.items():
        if any(word not in (root/name).read_text(encoding='utf-8') for word in words):
            raise ValueError('Q7 scope/checklist marker missing: '+name)
    return {'status':'published_contracts_consistency_pass','target_release':'1.8.0',
        'package_version':_version(root),'retained_stable_paths':297,'stable_ensemble_exports':59,
        'reviewed_modules':len(MODULES),'additive_exports':sum(len(importlib.import_module(m).__all__) for m in MODULES),
        'archive_case_count':len(report.cases),'report_hash':report.contract_hash,'experimental_qualification':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-review',action='store_true')
    args=parser.parse_args()
    if args.write_review:
        (ROOT/'docs/v1_8_api_review.json').write_text(json.dumps(build_review(ROOT),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(validate(ROOT),indent=2))
