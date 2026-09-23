"""Read-only v1.0 readiness structure/evidence check, not a release approval."""
from pathlib import Path
import ast,json,re,sys

def _compatible_development_version(version,baseline):
    current=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:\.dev\d+)?',version)
    released=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)',baseline)
    return bool(current and released and current.group(1)==released.group(1)
                and tuple(map(int,current.groups()[:3]))>=tuple(map(int,released.groups())))

def validate(root):
    data=json.loads((root/'docs/release_readiness.json').read_text(encoding='utf-8'))
    if set(data)!={'schema_version','name','preparation_version','review_baseline_commit','gates','final_candidate_checks','ready_for_candidate'} or type(data['schema_version']) is not int or data['schema_version']!=1:
        raise ValueError('unsupported readiness schema')
    if not re.fullmatch('[0-9a-f]{40}',data['review_baseline_commit']):
        raise ValueError('invalid review baseline commit')
    tree=ast.parse((root/'ncmemsim/_version.py').read_text(encoding='utf-8'))
    version=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets))
    if version!=data['preparation_version'] and not _compatible_development_version(version,data['preparation_version']):
        raise ValueError('readiness release baseline is incompatible with current package version')
    seen=set()
    for section,states in (('gates',{'pending','reviewed_pending_approval','approved'}),('final_candidate_checks',{'not_run','failed','passed'})):
        if not isinstance(data[section],list) or not data[section]:raise ValueError('empty readiness section')
        for item in data[section]:
            fields={'id','state','evidence'}|({'required_decision'} if section=='gates' else set())
            if set(item)!=fields or not isinstance(item['id'],str) or not item['id'] or item['id'] in seen:raise ValueError('invalid/duplicate gate')
            seen.add(item['id'])
            if item['state'] not in states or not isinstance(item['evidence'],list):raise ValueError('invalid readiness state/evidence')
            if section=='gates' and (not isinstance(item['required_decision'],str) or not item['required_decision'].strip()):raise ValueError('missing decision')
            if (section=='gates' or item['state']=='passed') and not item['evidence']:raise ValueError('missing evidence')
            for name in item['evidence']:
                if not isinstance(name,str):raise ValueError('invalid evidence path')
                path=(root/name).resolve()
                if not path.is_relative_to(root.resolve()) or not path.is_file():raise ValueError('missing/outside evidence: '+name)
    required_gates={'api_surface','result_semantics','archive_read_policy','scientific_defaults','distribution_contract','scientific_scope','archival_citation'}
    required_checks={'full_local_regression','strict_documentation_audit','clean_installed_distributions','supported_runtime_ci','remote_documentation'}
    if {g['id'] for g in data['gates']}!=required_gates or {c['id'] for c in data['final_candidate_checks']}!=required_checks:raise ValueError('required gates changed; review validation policy')
    ready=all(g['state']=='approved' for g in data['gates']) and all(c['state']=='passed' for c in data['final_candidate_checks'])
    if type(data['ready_for_candidate']) is not bool or data['ready_for_candidate']!=ready:raise ValueError('inconsistent ready_for_candidate')
    return data

def main():
    root=Path(__file__).resolve().parents[1]
    try:data=validate(root)
    except (ValueError,KeyError,TypeError,StopIteration,OSError) as exc:
        print('Readiness structure FAIL:',exc,file=sys.stderr);return 1
    print('Readiness structure/evidence PASS; ready_for_candidate='+str(data['ready_for_candidate']).lower())
    for item in data['gates']+data['final_candidate_checks']:print(item['id']+': '+item['state'])
    print('This check does not execute release gates, verify CI logs, approve APIs or authenticate scientific/DOI claims.')
    return 0

if __name__=='__main__':raise SystemExit(main())
