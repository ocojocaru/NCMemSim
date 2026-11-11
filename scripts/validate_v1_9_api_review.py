# Copyright 2026 Ovidiu Cojocaru
# SPDX-License-Identifier: Apache-2.0
"""R7 final v1.9 candidate: retained published surface, additive API and strict frozen report."""
from __future__ import annotations
import argparse
import importlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.validate_api_contract import build_inventory
from scripts.validate_v1_8_api_review import validate_retained as validate_published, PUBLISHED_V18_SNAPSHOTS
from scripts.validate_v1_4_api_review import _version
from ncmemsim.performance_contracts import _hash, _unique, _reject
from ncmemsim.performance_reporting import PerformanceInteroperabilityReport

MODULES=tuple('ncmemsim.'+name for name in ('performance_contracts','performance_execution',
    'performance_workloads','interoperability','interoperability_comparison','performance_reporting'))
ARCHIVE='tests/fixtures/archives/v1_9_preparation/performance_report.json'
SURFACE='docs/v1_8_published_surface.json'
SURFACE_SHA256='196a6a216740382dbbd8f06df4429187db703dcb03813603ab7662063b1d4790'
ARCHIVE_SHA256='75fbc26f082f99602c63df5bf2466c0d14575b305483a92ba71060db3948ea28'
PUBLISHED_V19_SURFACE_SHA256='18cc3bbfba2a5ac7e0c510e053dfb20feb48551871778645bd47d22dc73a291e'
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
    # Freeze the original 146 published sources; new module-qualified APIs are
    # reviewed separately and cannot silently bless changes to a published source.
    published=_json(root/'docs/v1_9_published_surface.json')
    if _hash(published)!=PUBLISHED_V19_SURFACE_SHA256:
        raise ValueError('published v1.9 source/surface baseline drift')
    original_paths=set()
    for item in published['modules']:
        name=item['module'];path=item['path']
        current=inventory.get(name)
        if current is None or _hash(_surface(current))!=item['surface_sha256']:
            raise ValueError('published v1.9 public surface changed: '+name)
        if _text_hash(root/path)!=item['source_sha256']:
            raise ValueError('published v1.9 source changed without separate review: '+name)
        original_paths.add(path.removeprefix('ncmemsim/'))
    package={p.relative_to(root/'ncmemsim').as_posix():_text_hash(p)
             for p in sorted((root/'ncmemsim').rglob('*.py'))
             if p.relative_to(root/'ncmemsim').as_posix() in original_paths}
    return dict(schema_version='phase-r-v1.9-final-candidate-api-review-v1',status='published_release_review',
        target_release='1.9.0',published_baseline='1.8.0',package_identity_at_review=_version(root),
        review_date='2026-10-23',implementation_source_commit='cc15fef20281ab0d4f305eecfd2b13f08e984a27',
        candidate_date='2026-10-23',publication_date='2026-10-26',
        version_doi='10.5281/zenodo.23664613',release_commit='af16961c832aaa3c8009450534f59cfbbc7893ea',
        publication_evidence=dict(main_ci=40300701850,documentation=40300701878,tag_ci=40313404859,release=40313404817,zenodo_record=23664613),
        published_v1_8_snapshot_sha256={name:_text_hash(root/'tests/fixtures/releases/v1_8_0'/name) for name in PUBLISHED_V18_SNAPSHOTS},
        preparation_ci_evidence=dict(source_commit='cc15fef20281ab0d4f305eecfd2b13f08e984a27',
            ci_run=39953158541,documentation_run=39953158477,conclusion='success'),
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
        release_policy='Published v1.9.0: candidate/PR/main/tag CI and Release passed; confirmed version DOI is separate from Concept DOI. Metadata follow-up requires its own CI after push.')


def validate(root):
    root=Path(root)
    if _json(root/'docs/api_inventory.json')!=build_inventory(root):
        raise ValueError('source API inventory drift')
    if _json(root/'docs/v1_9_api_review.json')!=build_review(root):
        raise ValueError('v1.9 preparation source/API/archive drift')
    from scripts.validate_v1_9_release_identity import validate_identity
    validate_identity(root)
    previous=validate_published(root)
    if (previous['retained_stable_paths'],previous['stable_ensemble_exports'],previous['additive_exports'])!=(297,59,34):
        raise ValueError('published contract retention mismatch')
    markers={'docs/v1_9_release_checklist.md':('Target release: `1.9.0`','Published identity: `1.9.0`',
                'P4B/P5B/P6B','Python 3.11, 3.12 and 3.13','R7 is complete'),
             'docs/roadmap.md':('R7 is complete','v1.9.0','experimental qualification remains deferred')}
    for path,words in markers.items():
        if any(word not in (root/path).read_text(encoding='utf-8') for word in words):
            raise ValueError('R7 scope/checklist marker missing: '+path)
    return dict(status='r7_final_candidate_consistency_pass',target_release='1.9.0',package_version=_version(root),
        retained_published_modules=140,retained_stable_paths=297,stable_ensemble_exports=59,
        reviewed_modules=len(MODULES),additive_exports=sum(len(importlib.import_module(name).__all__) for name in MODULES),
        report_hash=ARCHIVE_SHA256,campaign_count=5,comparison_count=9,experimental_qualification=False,
        exact_new_commit_ci='pending metadata follow-up push',final_candidate='published')




PUBLISHED_V19_SNAPSHOTS = ('README.md', 'CHANGELOG.md', 'CITATION.cff', 'ncmemsim/_version.py', 'docs/index.md', 'docs/roadmap.md', 'docs/archival_citation.md', 'docs/performance_interoperability.md', 'docs/v1_9_release_checklist.md', '.github/workflows/ci.yml', '.github/workflows/docs.yml')
PUBLISHED_V19_SNAPSHOT_SHA256 = {'README.md': '79e511062a87356089598a3c3fae9894454532a2304a7a155c80e6814c76c68f', 'CHANGELOG.md': '73a0264ffb369cdb7152ad27ecd97e52dbd84265c27143a5b12917c562ad6a75', 'CITATION.cff': '3f3ca827675e5ee9be4fa8352a60d0e5a4eb2c59d399d443a2bc18cafee8589b', 'ncmemsim/_version.py': '37e4e0cb8665d98f4468cb6437eea266c0b4647f635482ed1172d43c1f87b53e', 'docs/index.md': '9a5baf5ddbbebfc6a5c11c3e95323e49a0d0262594b29ddb241461d0482cbbc7', 'docs/roadmap.md': '2e6bd9a09a7711cd8ad95d1a80c31e237458e60ae11461440e539b6b2aa9ed58', 'docs/archival_citation.md': 'bcc973b421c341353def3026a1432e630466682f4cee96df42a1fd2b56c76219', 'docs/performance_interoperability.md': '3a5c954283a92f535fdf4ad2d47cb824f6ee12fdfe365819bfde9fae6c8002a0', 'docs/v1_9_release_checklist.md': 'f8ab695acb0ffa75e938977802d92d28c15b715b85150c0295d46c3fb0f70ef4', '.github/workflows/ci.yml': '4de241341b3f90577b93e9d5595691543eed313081220005450ba8efee12e7d9', '.github/workflows/docs.yml': '144d18803d11b5ba5d7977d0a4826246e8481e5825f25c7ef3b16a918e72658e'}


from contextlib import contextmanager as _contextmanager
@_contextmanager
def _published_view(root):
    """Current runtime with independently pinned historical identity declarations."""
    import shutil
    import tempfile
    root=Path(root)
    snapshots=root/'tests/fixtures/releases/v1_9_0'
    for name,digest in PUBLISHED_V19_SNAPSHOT_SHA256.items():
        if _text_hash(snapshots/name)!=digest:
            raise ValueError('published v1.9 identity snapshot drift: '+name)
    old=(snapshots/'ncmemsim/_version.py').read_text(encoding='utf-8')
    current=(root/'ncmemsim/_version.py').read_text(encoding='utf-8')
    if not any(
        current.replace(f'__version__ = "{version}"', '__version__ = "1.9.0"') == old
        for version in ('1.10.0', '1.11.0')
    ):
        raise ValueError('unreviewed version source change beyond candidate literal')
    with tempfile.TemporaryDirectory(prefix='ncmemsim-v19-review-') as temporary:
        target=Path(temporary)
        for folder in ('docs','ncmemsim','tests/fixtures','data'):
            if (root/folder).exists(): shutil.copytree(root/folder,target/folder)
            else: (target/folder).mkdir(parents=True,exist_ok=True)
        for name in PUBLISHED_V19_SNAPSHOTS:
            destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(snapshots/name,destination)
        yield target


def build_retained_review(root):
    with _published_view(root) as target:
        return build_review(target)


def validate_retained(root):
    with _published_view(root) as target:
        return validate(target)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--write-review',action='store_true')
    parser.add_argument('--retained',action='store_true')
    args=parser.parse_args()
    if args.write_review:
        (ROOT/'docs/v1_9_api_review.json').write_text(json.dumps(build_review(ROOT),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(validate_retained(ROOT) if args.retained else validate(ROOT),indent=2))
