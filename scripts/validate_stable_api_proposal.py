"""Compare the proposed stable surface; approval is a separate maintainer decision."""
from pathlib import Path
import importlib,inspect,json,sys

def build_proposal(root):
    from scripts.validate_api_contract import build_inventory
    inventory=json.loads((root/'docs/api_inventory.json').read_text(encoding='utf-8'))
    if build_inventory(root)!=inventory:raise ValueError('Source API inventory drift; review before stable proposal validation.')
    modules={m['module']:m for m in inventory['modules']}
    paths=set(inventory['documented_imports'])
    for name in ('ncmemsim','ncmemsim.transport'):
        paths.update(name+'.'+item for item in modules[name]['explicit_exports'])
    def resolve(path):
        if path in modules:return path,{'kind':'module','module':path}
        module,name=path.rsplit('.',1);record=modules[module]
        if name in record['package_import_aliases']:
            target=record['package_import_aliases'][name]
            if target==path:raise ValueError('self-referential alias')
            return resolve(target)
        for definition in record['public_source_definitions']:
            if definition['name']==name:return path,definition
        for assignment in record['public_assignments']:
            if name==assignment['name']:return path,{'kind':'declared_value','source_assignment':assignment}
        raise ValueError('unresolved declared API: '+path)
    entries=[]
    for path in sorted(paths):
        target,contract=resolve(path)
        if path in modules:obj=importlib.import_module(path)
        else:
            module,name=path.rsplit('.',1);obj=getattr(importlib.import_module(module),name)
        runtime_signature=None
        if inspect.isclass(obj) or inspect.isfunction(obj):
            runtime_signature=str(inspect.signature(obj))
            if ' at 0x' in runtime_signature:raise ValueError('nonportable default signature: '+path)
        entries.append({'import_path':path,'definition_path':target,'kind':contract['kind'],
            'runtime_call_signature':runtime_signature,'source_contract':contract})
    return {'schema_version':1,'status':'proposal_pending_approval','preparation_version':'0.14.0',
        'source_baseline_commit':'6409e42087992f5dfde966cd6e320d3964b264b1',
        'selection_policy':'All existing documented imports plus explicit root-package exports and legacy transport exports; other aliases/helpers are not implicitly selected.',
        'entries':entries}

def render(data):
    lines=['# Proposed stable v1.0 API surface','',
        'Status: proposal_pending_approval. Preparation version remains 0.14.0.',
        'This list is a proposed contract, not a declaration that v1.0 is released.',
        '',data['selection_policy'],'',
        'Exact signatures, declared fields and public methods are in [stable_api_proposal.json](stable_api_proposal.json).',
        'Class call signatures include generated dataclass constructors; source records identify declared methods and fields.',
        'Inherited/incidental methods are not automatically guaranteed. Module selection guarantees its named import path, not every attribute.',
        'Version strings are runtime identity, not a promise to retain the literal version number.',
        '', '| Import path | Definition / alias target | Kind |', '|---|---|---|']
    lines += ['| '+e['import_path']+' | '+e['definition_path']+' | '+e['kind']+' |' for e in data['entries']]
    lines += ['', '## Proposed maintenance contract','',
        'Retain these paths, accepted existing parameter names/order/kinds/defaults and declared result fields in compatible releases.',
        'Existing positional arguments remain supported where the recorded callable signature permits them; new examples should prefer keywords.',
        'For explicit source methods, receiver parameters are source evidence, not caller arguments.',
        'Constructor signatures record actual current call shape; generated/inherited implementation details are not separately frozen.',
        'Numerical behavior, applicability and ownership are governed by the reviewed result/default manuals, not by signatures alone.',
        'Protocol/enum signatures describe Python mechanics; they do not imply that abstract protocols are intended as concrete engines.',
        'Deprecation/removal follows [compatibility policy](api_compatibility.md). New optional APIs may be added without invalidating old calls.',
        '', '## Proposed limitations to retain','',
        'Accept current empty-sweep shape and input aliasing, shallow nested state/context ownership, writable arrays in legacy frozen containers,',
        'None/NaN/zero conventions, strict current-schema archive readers and the legacy manifest hash/copy scope as documented.',
        'Do not silently harden or reinterpret those behaviors in this preparation. Any later incompatible change needs a migration/major-version decision.',
        'See [core results](api_results.md), [analysis results](api_analysis_results.md), [archives](api_archives.md),',
        '[defaults](scientific_defaults.md), and [distribution](distribution_contracts.md).',
        '', '## Proposed scientific release scope','',
        'A stable compact-model simulation/fitting/DTCO software release with explicit applicability and provisional parameters.',
        'Synthetic workflows remain synthetic FITTED evidence. Numerical success, covariance and qualification eligibility do not imply independent experimental validation.',
        'No new physics, all-device predictive validity, manufactured yield or experimental calibration is promised by stable software status.',
        'Literature/model/parameter attribution retains its specific scope. New measured claims require their own dataset/provenance and validation evidence.',
        'Out-of-model effects remain outside the contract unless explicitly introduced and tested.',
        '', '## Approval still required','',
        'Review the exact list and the limitations/scientific scope above. Reject or revise individual entries before freezing; do not expand it merely to match every importable name.',
        'The readiness matrix remains pending approval; this proposal changes no gate to approved and records no final checks as passed.',
        'Archival/DOI planning and full final-candidate tests/build/CI/documentation remain separate requirements.',
        'Run python scripts/validate_stable_api_proposal.py to compare the retained proposal against current source/runtime declarations.',
        'This command detects drift; it does not regenerate the baseline, grant approval or test numerical behavior.']
    return '\n'.join(lines)+'\n'

def main():
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root))
    actual=build_proposal(root)
    expected=json.loads((root/'docs/stable_api_proposal.json').read_text(encoding='utf-8'))
    if actual!=expected:raise SystemExit('Stable API proposal differs: review source/signature/scope changes explicitly.')
    if (root/'docs/stable_api_proposal.md').read_text(encoding='utf-8')!=render(actual):raise SystemExit('Stable API proposal Markdown differs from JSON.')
    print('Stable API proposal drift check PASS: '+str(len(actual['entries']))+' exact import paths; pending approval.')

if __name__=='__main__':main()
