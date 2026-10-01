# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Review additive Phase L API contracts; candidate validation is not release approval."""
from __future__ import annotations
import argparse
import importlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ncmemsim._version import __version__
from scripts.validate_api_contract import build_inventory
from scripts.validate_v1_2_release_identity import HISTORICAL_JSON_SHA256, _semantic_json_digest, _citation_field

MODULES=tuple('ncmemsim.ensemble.'+name for name in (
    'model_contracts','model_sampling','model_execution','model_analysis','model_dtco','model_reporting'))


def build_review(root: Path) -> dict:
    inventory=build_inventory(root)
    reviewed=[]
    for name in MODULES:
        module=importlib.import_module(name)
        record=next(m for m in inventory['modules'] if m['module']==name)
        for symbol in module.__all__:
            if not hasattr(module,symbol):raise ValueError('missing MODEL API: '+name+'.'+symbol)
        reviewed.append(record)
    return {'schema_version':'model-v1_3-api-review-v1','status':'reviewed_candidate_not_release_approval',
        'baseline_release':'v1.2.0','baseline_commit':'b9d2ff77136217af5b3b5a4b5a4780af5d75d6d5',
        'implementation_source_commit':'830319ef41ae90c52e50b96f1115196120a80249','candidate_version':'1.3.0','development_version':'1.3.0.dev0',
        'stable_ensemble_exports':sorted(importlib.import_module('ncmemsim.ensemble').__all__),
        'additive_module_qualified_surface':reviewed,
        'compatibility_policy':'Phase K exports and archive schemas preserved; MODEL API is explicit and additive',
        'release_gates':'Final exact commit: full tests, strict docs, clean distributions, Python 3.11-3.13 CI, citation/version/tag alignment'}


def validate(root: Path) -> dict:
    stored=json.loads((root/'docs/v1_3_api_review.json').read_text(encoding='utf-8'))
    if stored!=build_review(root):raise ValueError('v1.3 source API differs from reviewed contracts')
    if len(stored['stable_ensemble_exports'])!=59:raise ValueError('stable ensemble exports changed')
    for name,digest in HISTORICAL_JSON_SHA256.items():
        if _semantic_json_digest(root/name)!=digest:raise ValueError('historical evidence changed: '+name)
    citation=(root/'CITATION.cff').read_text(encoding='utf-8')
    if __version__=='1.3.0.dev0':
        if _citation_field(citation,'version')!='1.2.0':raise ValueError('development citation must retain published stable identity')
    elif __version__=='1.3.0':
        if _citation_field(citation,'version')!='1.3.0':raise ValueError('final release citation must match version')
        if '**Current stable release:** `1.3.0`' not in (root/'README.md').read_text(encoding='utf-8'):
            raise ValueError('final README identity must match release')
    else:raise ValueError('unexpected v1.3 candidate package identity')
    return {'status':'candidate_contracts_pass_not_release_approval','package_version':__version__,
            'reviewed_modules':len(MODULES),'stable_ensemble_exports':59}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-review',action='store_true')
    args=parser.parse_args()
    if args.write_review:
        (ROOT/'docs/v1_3_api_review.json').write_text(json.dumps(build_review(ROOT),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(validate(ROOT),indent=2))
