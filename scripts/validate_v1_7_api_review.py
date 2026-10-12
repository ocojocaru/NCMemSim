# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""P7 pre-identity API/archive review; not release approval or calibration."""
import argparse,importlib,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.validate_api_contract import build_inventory
from scripts.validate_v1_6_api_review import validate as retained_review
from scripts.validate_v1_5_api_review import _text_hash
from scripts.validate_v1_4_api_review import _json,_version
from scripts.validate_v1_2_release_identity import _semantic_json_digest
from scripts.validate_independent_data_review import validate as data_review

MODULES=('ncmemsim.independent_data','ncmemsim.independent_optical_fit',
 'ncmemsim.independent_optical_validation','ncmemsim.device_photo_experiment',
 'ncmemsim.om2_sweep','ncmemsim.om2_numerics','ncmemsim.om2_reporting')
ARCHIVE='tests/fixtures/archives/v1_7_preparation/om2_report.json'


def build_review(root):
    inventory={m['module']:m for m in build_inventory(root)['modules']}
    surface=[]
    for name in MODULES:
        module=importlib.import_module(name);exports=list(module.__all__)
        if len(exports)!=len(set(exports)) or any(not hasattr(module,x) for x in exports):
            raise ValueError('invalid v1.7 exports: '+name)
        surface.append({'module':name,'exports':exports,'source_contract':inventory[name],
            'source_sha256':_text_hash(root/(name.replace('.','/')+'.py'))})
    return {'schema_version':'independent-infrastructure-v1_7-api-review-v1',
        'status':'pre_identity_review_not_release_approval','target_release':'1.7.0',
        'published_baseline':'1.6.0','package_identity_at_review':'1.6.0',
        'implementation_source_commit':'9d672ff36a7b64e416be11349c2385198587b617',
        'approved_release_scope':'calibration infrastructure and synthetic numerical diagnostics; experimental P4B/P5B/P6B deferred',
        'retained_structural_review_sha256':_semantic_json_digest(root/'docs/v1_6_api_review.json'),
        'independent_data_review_sha256':_semantic_json_digest(root/'docs/independent_data_review.json'),
        'frozen_report_sha256':_semantic_json_digest(root/ARCHIVE),
        'archive_scope':'P6A preparation snapshot from package 1.6.0, not a published or dev-version 1.7 archive',
        'additive_module_qualified_surface':surface,
        'scientific_limits':['zero new admitted independent measured datasets and zero calibrated parameters',
            'PDF-only acquisition gaps and experimental P4B/P5B/P6B remain open',
            'existing physics unchanged; substrate photogeneration and measured C-V/LCR mapping unresolved',
            'synthetic fitting/holdout/OM-2 checks are numerical evidence, not measured validation',
            'hashes/projections verify consistency, not authenticity or replayed trajectories'],
        'release_policy':'full regression/docs/installed wheel-sdist, Python 3.11-3.13 exact-commit CI; candidate identity and publication pending'}


def validate(root):
    if _json(root/'docs/api_inventory.json')!=build_inventory(root):raise ValueError('API inventory drift')
    if _json(root/'docs/v1_7_api_review.json')!=build_review(root):raise ValueError('v1.7 review/source/archive drift')
    if _version(root)!='1.6.0':raise ValueError('pre-identity gate retains published package identity')
    previous=retained_review(root);data=data_review(root)
    if previous['retained_stable_paths']!=297 or data['admitted_independent_datasets']!=0 or data['new_calibrated_parameters']!=0:
        raise ValueError('retained or experimental scope mismatch')
    from ncmemsim.om2_reporting import OM2NumericalReport
    report=OM2NumericalReport.from_dict(_json(root/ARCHIVE))
    if report.study.summary['experimental_qualification'] or report.study.summary['parameters_fitted']:
        raise ValueError('frozen numerical evidence cannot claim calibration')
    for name,markers in {
        'docs/v1_7_release_checklist.md':('P7 is not complete','pre-identity','P4B/P5B/P6B','Python 3.11, 3.12 and 3.13'),
        'docs/roadmap.md':('P7 pre-identity review','experimental qualification remains deferred')}.items():
        if any(x not in (root/name).read_text(encoding='utf-8') for x in markers):raise ValueError('P7 scope marker missing: '+name)
    return {'status':'pre_identity_review_pass_not_release_approval','target_release':'1.7.0',
        'package_version':_version(root),'retained_stable_paths':297,'stable_ensemble_exports':59,
        'reviewed_modules':len(MODULES),'additive_exports':sum(len(importlib.import_module(m).__all__) for m in MODULES),
        'experimental_qualification':False,'report_hash':report.contract_hash}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-review',action='store_true');args=parser.parse_args()
    if args.write_review:
        (ROOT/'docs/v1_7_api_review.json').write_text(json.dumps(build_review(ROOT),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(validate(ROOT),indent=2))
