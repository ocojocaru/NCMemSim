# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""Review structural candidate contracts and retained history; not publication approval."""
from __future__ import annotations
import argparse
import importlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.validate_api_contract import build_inventory
from scripts.validate_v1_5_api_review import _text_hash, validate as spectral_review
from scripts.validate_v1_4_api_review import _json, _version
from scripts.validate_v1_2_release_identity import _semantic_json_digest, _citation_field
from scripts.validate_structural_parameters import validate as structural_parameters

MODULES=('ncmemsim.materials.structural','ncmemsim.materials.structural_strain',
    'ncmemsim.materials.structural_confinement','ncmemsim.structural_optical_context','ncmemsim.structural_reporting')
SNAPSHOTS=('README.md','CHANGELOG.md','CITATION.cff','ncmemsim/_version.py','docs/index.md',
    'docs/roadmap.md','docs/broadband_optics.md','docs/v1_5_release_checklist.md',
    '.github/workflows/ci.yml','.github/workflows/docs.yml')


def build_review(root):
    inventory={m['module']:m for m in build_inventory(root)['modules']};surface=[]
    for name in MODULES:
        module=importlib.import_module(name);exports=list(module.__all__)
        if len(exports)!=len(set(exports)) or any(not hasattr(module,x) for x in exports):raise ValueError('invalid structural exports: '+name)
        surface.append({'module':name,'exports':exports,'source_contract':inventory[name],
            'source_sha256':_text_hash(root/(name.replace('.','/')+'.py'))})
    return {'schema_version':'structural-v1_6-api-review-v1','status':'reviewed_candidate_not_release_approval',
        'baseline_release':'v1.5.0','baseline_release_commit':'53d7c0b9bfa2be5e75aa3a6813c8e33be068843d',
        'baseline_citation_commit':'46965a3d7ed86fd64223b587db71500f4a7e7e44',
        'implementation_source_commit':'13b05572567d5124079372f295b39dc6547595e8',
        'development_version':'1.6.0.dev0','candidate_version':'1.6.0',
        'retained_stable_path_count':297,'retained_spectral_review_sha256':_semantic_json_digest(root/'docs/v1_5_api_review.json'),
        'structural_audit_sha256':_semantic_json_digest(root/'docs/strain_confinement_audit.json'),
        'parameter_review_sha256':_semantic_json_digest(root/'docs/structural_parameters_review.json'),
        'structural_archive_sha256':_semantic_json_digest(root/'tests/fixtures/archives/v1_6_0_dev/structural_report.json'),
        'published_v1_5_snapshot_sha256':{name:_text_hash(root/'tests/fixtures/releases/v1_5_0'/name) for name in SNAPSHOTS},
        'additive_module_qualified_surface':surface,
        'scientific_status':'conditional-unqualified-simulation',
        'scientific_limits':['Ge Gamma/L optical transition shifts only; no automatic transport-band-offset correction',
            'hydrostatic strain-induced shift; spherical infinite-barrier EMA kinetic confinement only',
            'synthetic masses/coefficient/domain and additive policy ASSUMED; zero qualified material presets',
            'complete stored observations; rebuild projections without optical/solver/RNG replay; consistency is not authenticity'],
        'release_policy':'full regression/docs/installed wheel-sdist; Python 3.11-3.13 exact-commit CI; publication and actual v1.6 DOI pending'}


def retained_review(root):
    """Overlay only published identity declarations onto current retained source contracts."""
    with tempfile.TemporaryDirectory(prefix='ncmemsim-v15-review-') as temporary:
        target=Path(temporary)
        for folder in ('docs','ncmemsim','tests/fixtures'):shutil.copytree(root/folder,target/folder)
        for name in ('README.md','CHANGELOG.md','CITATION.cff'):shutil.copyfile(root/name,target/name)
        for name in SNAPSHOTS:
            destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(root/'tests/fixtures/releases/v1_5_0'/name,destination)
        return spectral_review(target)


def validate(root):
    if _json(root/'docs/api_inventory.json')!=build_inventory(root):raise ValueError('source API inventory drift')
    stored=_json(root/'docs/v1_6_api_review.json')
    if stored!=build_review(root):raise ValueError('v1.6 source/API/archive review drift')
    previous=retained_review(root)
    if previous['retained_stable_paths']!=297 or previous['stable_ensemble_exports']!=59:raise ValueError('retained stable contracts changed')
    structural_parameters(root)
    if _version(root)!='1.6.0.dev0':raise ValueError('O7 preparation identity must be 1.6.0.dev0')
    citation=(root/'CITATION.cff').read_text(encoding='utf-8')
    if citation!=(root/'tests/fixtures/releases/v1_5_0/CITATION.cff').read_text(encoding='utf-8'):raise ValueError('development citation must retain published v1.5 identity/DOI')
    markers={'README.md':('**Development version:** `1.6.0.dev0`','**Current stable release:** `1.5.0`'),
        'docs/strain_confinement.md':('O7 preparation is implemented','release approval remains pending'),
        'docs/roadmap.md':('O7 preparation is implemented','release approval remains pending'),
        'docs/v1_6_release_checklist.md':('O7 is not complete','release approval remains pending','Python 3.11, 3.12 and 3.13')}
    for name,values in markers.items():
        if any(v not in (root/name).read_text(encoding='utf-8') for v in values):raise ValueError('candidate declaration mismatch: '+name)
    from ncmemsim.structural_reporting import StructuralReport
    raw=_json(root/'tests/fixtures/archives/v1_6_0_dev/structural_report.json')
    if StructuralReport.from_dict(raw).to_dict()!=raw:raise ValueError('structural archive mismatch')
    return {'status':'candidate_contracts_pass_not_release_approval','package_version':_version(root),
        'citation_version':_citation_field(citation,'version'),'latest_published_stable':'1.5.0',
        'retained_stable_paths':297,'stable_ensemble_exports':59,'reviewed_modules':len(MODULES),
        'structural_exports':sum(len(m['exports']) for m in stored['additive_module_qualified_surface'])}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-review',action='store_true');args=parser.parse_args()
    if args.write_review:(ROOT/'docs/v1_6_api_review.json').write_text(json.dumps(build_review(ROOT),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(validate(ROOT),indent=2))
