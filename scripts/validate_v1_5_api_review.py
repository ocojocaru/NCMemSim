# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Review additive spectral contracts and retained history; not release approval."""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.validate_api_contract import build_inventory
from scripts.validate_v1_4_api_review import build_review as thermal_review, _json, _version
from scripts.validate_v1_3_api_review import build_review as model_review
from scripts.validate_v1_4_release_identity import validate_identity as published_identity
from scripts.validate_v1_2_release_identity import HISTORICAL_JSON_SHA256,_semantic_json_digest,_citation_field
from scripts.validate_stable_api_proposal import build_proposal

MODULES=('ncmemsim.spectral_sources','ncmemsim.spectral_absorption','ncmemsim.spectral_stack',
         'ncmemsim.spectral_context','ncmemsim.spectral_reporting')
SNAPSHOTS=('README.md','CHANGELOG.md','CITATION.cff','ncmemsim/_version.py','docs/index.md',
    'docs/roadmap.md','docs/temperature_properties.md','docs/v1_4_release_checklist.md',
    '.github/workflows/ci.yml','.github/workflows/docs.yml')
DEVELOPMENT_VERSION='1.5.0.dev0'


def _text_hash(path):return hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()


def build_review(root):
    modules={m['module']:m for m in build_inventory(root)['modules']};surface=[]
    for name in MODULES:
        module=importlib.import_module(name);exports=list(module.__all__)
        if len(exports)!=len(set(exports)) or any(not hasattr(module,x) for x in exports):
            raise ValueError('invalid spectral exports: '+name)
        surface.append({'module':name,'exports':exports,'source_contract':modules[name],
            'source_sha256':_text_hash(root/(name.replace('.','/')+'.py'))})
    return {'schema_version':'spectral-v1_5-api-review-v1','status':'reviewed_candidate_not_release_approval',
        'baseline_release':'v1.4.0','baseline_release_commit':'67e8791a6ec5c3a76fc8f92bcba4da614900f4f5',
        'baseline_citation_commit':'7bf9096de2148201ab301376ce1baac786a06e08',
        'implementation_source_commit':'23cf78cd8088658c9eb95a56f46fa30d04c83b14',
        'candidate_version':'1.5.0','development_version':DEVELOPMENT_VERSION,
        'retained_stable_path_count':297,'stable_ensemble_exports':sorted(importlib.import_module('ncmemsim.ensemble').__all__),
        'additive_module_qualified_surface':surface,
        'retained_thermal_review_sha256':_semantic_json_digest(root/'docs/v1_4_api_review.json'),
        'retained_model_review_sha256':_semantic_json_digest(root/'docs/v1_3_api_review.json'),
        'broadband_audit_sha256':_semantic_json_digest(root/'docs/broadband_optics_audit.json'),
        'spectral_archive_sha256':_semantic_json_digest(root/'tests/fixtures/archives/v1_5_0_dev/spectral_report.json'),
        'published_v1_4_snapshot_sha256':{name:_text_hash(root/'tests/fixtures/releases/v1_4_0'/name) for name in SNAPSHOTS},
        'scientific_status':'conditional-unqualified-simulation',
        'scientific_limits':['normal-incidence single-pass Beer-Lambert; no reflection/interference/scattering',
            'source support/grid and constant capture are explicit; measured inputs do not qualify a device',
            'stored states/alpha observations authoritative; static projections rebuilt without optical/workflow/RNG replay',
            'synthetic numerical references do not establish calibration, manufacturing yield or universal grids'],
        'release_policy':'exact final commit regression/docs/distribution and Python 3.11-3.13 CI; publication remains pending'}


def validate(root):
    if _json(root/'docs/api_inventory.json')!=build_inventory(root):raise ValueError('source API inventory drift')
    stored=_json(root/'docs/v1_5_api_review.json')
    if stored!=build_review(root):raise ValueError('v1.5 API/source/provenance/archive review changed')
    if len(stored['stable_ensemble_exports'])!=59:raise ValueError('stable ensemble exports changed')
    if _json(root/'docs/v1_4_api_review.json')!=thermal_review(root):raise ValueError('retained thermal contracts changed')
    if _json(root/'docs/v1_3_api_review.json')!=model_review(root):raise ValueError('retained MODEL contracts changed')
    for name,digest in HISTORICAL_JSON_SHA256.items():
        if _semantic_json_digest(root/name)!=digest:raise ValueError('historical snapshot changed: '+name)
    entries=list(_json(root/'docs/stable_api_proposal.json')['entries'])
    for release in ('v1_1','v1_2'):entries+=_json(root/('docs/'+release+'_api_review.json'))['proposed_stable_additions']
    entries.sort(key=lambda x:x['import_path'])
    if len(entries)!=297 or build_proposal(root,[x['import_path'] for x in entries])['entries']!=entries:
        raise ValueError('retained stable API changed')
    published_identity(root/'tests/fixtures/releases/v1_4_0')
    version=_version(root)
    if version not in (DEVELOPMENT_VERSION,'1.5.0'):raise ValueError('unsupported v1.5 identity')
    citation=(root/'CITATION.cff').read_text(encoding='utf-8')
    if version==DEVELOPMENT_VERSION and citation!=(root/'tests/fixtures/releases/v1_4_0/CITATION.cff').read_text(encoding='utf-8'):
        raise ValueError('development citation must retain published v1.4 DOI/identity')
    if version=='1.5.0':
        from scripts.validate_v1_5_release_identity import validate_identity
        validate_identity(root)
    else:
        markers={'README.md':('**Development version:** `1.5.0.dev0`','**Current stable release:** `1.4.0`'),
            'docs/broadband_optics.md':('N7 preparation is implemented','release approval remains pending'),
            'docs/roadmap.md':('N7 preparation is implemented','release approval remains pending'),
            'docs/v1_5_release_checklist.md':('release approval remains pending','Python 3.11, 3.12 and 3.13','N7 is not complete')}
        for name,required in markers.items():
            text=(root/name).read_text(encoding='utf-8')
            if any(x not in text for x in required):raise ValueError('inconsistent preparation declaration: '+name)
    from ncmemsim.spectral_reporting import SpectralReport
    archive=_json(root/'tests/fixtures/archives/v1_5_0_dev/spectral_report.json')
    if SpectralReport.from_dict(archive).to_dict()!=archive:raise ValueError('spectral archive roundtrip failed')
    return {'status':'candidate_contracts_pass_not_release_approval','package_version':version,
        'citation_version':version if version=='1.5.0' else '1.4.0','latest_published_stable':'1.4.0','retained_stable_paths':297,
        'stable_ensemble_exports':59,'reviewed_modules':5,'spectral_exports':sum(len(x['exports']) for x in stored['additive_module_qualified_surface'])}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-review',action='store_true');args=parser.parse_args()
    if args.write_review:(ROOT/'docs/v1_5_api_review.json').write_text(json.dumps(build_review(ROOT),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(validate(ROOT),indent=2))
