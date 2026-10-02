# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0

"""Review the additive thermal candidate; passing is not release approval."""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.validate_api_contract import build_inventory
from scripts.validate_v1_3_api_review import build_review as model_review
from scripts.validate_v1_2_release_identity import HISTORICAL_JSON_SHA256, _semantic_json_digest, _citation_field
from scripts.validate_stable_api_proposal import build_proposal

MODULES = ('ncmemsim.materials.temperature', 'ncmemsim.temperature_context',
           'ncmemsim.thermal_dtco', 'ncmemsim.thermal_reporting')
DEVELOPMENT_VERSION = '1.4.0.dev0'
STABLE_VERSION = '1.3.0'
CONCEPT_DOI = '10.5281/zenodo.23078330'
STABLE_DOI = '10.5281/zenodo.23079171'


def _json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate review field: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('nonfinite review value: ' + value)
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs, parse_constant=invalid)


def _version(root):
    tree = ast.parse((root / 'ncmemsim/_version.py').read_text(encoding='utf-8'))
    versions = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == '__version__' for t in n.targets)]
    if len(versions) != 1:
        raise ValueError('single literal package version required')
    return versions[0]


def build_review(root: Path) -> dict:
    inventory = build_inventory(root)
    modules = {m['module']: m for m in inventory['modules']}
    surface = []
    for name in MODULES:
        module = importlib.import_module(name)
        exports = list(module.__all__)
        if len(exports) != len(set(exports)) or any(not hasattr(module, s) for s in exports):
            raise ValueError('invalid thermal exports: ' + name)
        surface.append({'module': name, 'exports': exports, 'source_contract': modules[name]})
    fixtures = root / 'tests/fixtures/releases/v1_3_0'
    paths = ('README.md', 'CHANGELOG.md', 'CITATION.cff', 'ncmemsim/_version.py',
             'docs/index.md', 'docs/model_variability.md', 'docs/roadmap.md')
    return {
        'schema_version': 'thermal-v1_4-api-review-v1',
        'status': 'reviewed_candidate_not_release_approval',
        'baseline_release': 'v1.3.0',
        'baseline_release_commit': '4319cbc899191bd1cafbd79c4a7df20c1d490d10',
        'implementation_source_commit': '8f7e43894fcb3328543741a2090aeb9bc37364ba',
        'candidate_version': '1.4.0', 'development_version': DEVELOPMENT_VERSION,
        'retained_stable_path_count': 297,
        'stable_ensemble_exports': sorted(importlib.import_module('ncmemsim.ensemble').__all__),
        'additive_module_qualified_surface': surface,
        'simulator_integration_contract': modules['ncmemsim.simulator'],
        'historical_v1_3_identity_sha256': {p: hashlib.sha256((fixtures/p).read_text(encoding='utf-8').encode('utf-8')).hexdigest() for p in paths},
        'coefficient_review_hash': _semantic_json_digest(root/'docs/temperature_coefficients_review.json'),
        'temperature_audit_hash': _semantic_json_digest(root/'docs/temperature_properties_audit.json'),
        'thermal_archive_sha256': _semantic_json_digest(root/'tests/fixtures/archives/v1_4_0_dev/thermal_report.json'),
        'scientific_status': 'conditional-unqualified-simulation',
        'scientific_limits': [
            'Si Eg/ni and bulk-Ge Gamma/L/phonon profiles are opt-in, anchored and domain-limited',
            '250-350 K applicability is assumed; literature coefficients do not establish device calibration',
            'GeSn temperature coefficients, broadband propagation and temperature-dependent TAT laws are not supplied',
            'stored observations are authoritative evidence; restoration resolves inputs and rebuilds analysis without workflow/RNG replay',
            'synthetic DTCO comparisons do not establish process yield or independent experimental qualification'],
        'release_policy': 'exact final commit local/docs/distribution and Python 3.11-3.13 remote gates; publication remains pending',
    }


def validate(root: Path) -> dict:
    if _json(root/'docs/api_inventory.json') != build_inventory(root):
        raise ValueError('source API inventory drift')
    stored = _json(root/'docs/v1_4_api_review.json')
    if stored != build_review(root):
        raise ValueError('v1.4 API, provenance, scientific review or archives changed')
    if len(stored['stable_ensemble_exports']) != 59:
        raise ValueError('stable ensemble exports changed')
    if _json(root/'docs/v1_3_api_review.json') != model_review(root):
        raise ValueError('retained MODEL API contracts changed')
    for name, digest in HISTORICAL_JSON_SHA256.items():
        if _semantic_json_digest(root/name) != digest:
            raise ValueError('historical snapshot changed: ' + name)
    proposal = _json(root/'docs/stable_api_proposal.json')
    entries = list(proposal['entries'])
    for release in ('v1_1', 'v1_2'):
        entries.extend(_json(root/('docs/'+release+'_api_review.json'))['proposed_stable_additions'])
    entries.sort(key=lambda e: e['import_path'])
    if len(entries) != stored['retained_stable_path_count'] or len({e['import_path'] for e in entries}) != len(entries):
        raise ValueError('retained stable path count changed')
    if build_proposal(root, [e['import_path'] for e in entries])['entries'] != entries:
        raise ValueError('approved stable API changed')
    version = _version(root)
    if version == DEVELOPMENT_VERSION:
        citation = (root/'CITATION.cff').read_text(encoding='utf-8')
        historical = (root/'tests/fixtures/releases/v1_3_0/CITATION.cff').read_text(encoding='utf-8')
        if citation != historical or _citation_field(citation, 'version') != STABLE_VERSION or _citation_field(citation, 'doi') != STABLE_DOI or CONCEPT_DOI not in citation:
            raise ValueError('development citation must retain the published v1.3.0 identity and DOI')
        markers = {
            'README.md': ('**Development version:** `1.4.0.dev0`', '**Current stable release:** `1.3.0`'),
            'docs/temperature_properties.md': ('M7 preparation is implemented', 'release approval remains pending'),
            'docs/roadmap.md': ('M7 preparation is implemented', 'release approval remains pending'),
            'docs/v1_4_release_checklist.md': ('Status: M7 preparation implemented; release approval remains pending.', 'Python 3.11, 3.12 and 3.13', 'No tag, merge or release publication'),
        }
        for name, required in markers.items():
            text = (root/name).read_text(encoding='utf-8')
            if any(marker not in text for marker in required):
                raise ValueError('inconsistent candidate declaration: ' + name)
        citation_version = STABLE_VERSION
    elif version == '1.4.0':
        from scripts.validate_v1_4_release_identity import validate_identity
        validate_identity(root)
        citation_version = version
    else:
        raise ValueError('unsupported v1.4 candidate package version')
    return {'status': 'candidate_contracts_pass_not_release_approval', 'package_version': version,
            'citation_version': citation_version, 'latest_published_stable': STABLE_VERSION,
            'reviewed_modules': len(MODULES), 'stable_ensemble_exports': 59,
            'retained_stable_paths': len(entries)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-review', action='store_true')
    args = parser.parse_args()
    if args.write_review:
        (ROOT/'docs/v1_4_api_review.json').write_text(json.dumps(build_review(ROOT), indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps(validate(ROOT), indent=2))
