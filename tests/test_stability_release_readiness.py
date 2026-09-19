"""Readiness tooling cannot silently omit gates or mark pending work ready."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from scripts.validate_release_readiness import validate
ROOT=Path(__file__).resolve().parents[1]

def fixture_root(tmp_path):
 data=json.loads((ROOT/'docs/release_readiness.json').read_text(encoding='utf-8'))
 (tmp_path/'docs').mkdir();(tmp_path/'ncmemsim').mkdir()
 (tmp_path/'ncmemsim/_version.py').write_text("__version__='0.14.0'\n",encoding='utf-8')
 for gate in data['gates']:
  for name in gate['evidence']:
   path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('declared local evidence',encoding='utf-8')
 return data

def save(root,data):(root/'docs/release_readiness.json').write_text(json.dumps(data),encoding='utf-8')

def test_current_matrix_records_contract_approval_without_candidate_readiness():
 data=validate(ROOT)
 assert data['ready_for_candidate'] is False
 states={c['id']:c['state'] for c in data['final_candidate_checks']}
 assert states['full_local_regression'] in {'not_run','passed'}
 assert states['strict_documentation_audit'] in {'not_run','passed'}
 assert states['clean_installed_distributions']=='not_run'
 assert states['supported_runtime_ci'] in {'not_run','passed'}
 assert states['remote_documentation'] in {'not_run','passed'}
 gate_states={g['id']:g['state'] for g in data['gates']}
 assert all(state=='approved' for state in gate_states.values())

@pytest.mark.parametrize('fault',['omit_gate','omit_check','duplicate','missing_evidence','outside_evidence','unsupported_schema','version','premature_ready','passed_without_evidence'])
def test_invalid_readiness_rejected(tmp_path,fault):
 data=fixture_root(tmp_path)
 if fault=='omit_gate':data['gates'].pop()
 elif fault=='omit_check':data['final_candidate_checks'].pop()
 elif fault=='duplicate':data['gates'].append(deepcopy(data['gates'][0]))
 elif fault=='missing_evidence':data['gates'][0]['evidence']=['missing.txt']
 elif fault=='outside_evidence':data['gates'][0]['evidence']=['../outside.txt']
 elif fault=='unsupported_schema':data['schema_version']=99
 elif fault=='version':data['preparation_version']='1.0.0'
 elif fault=='premature_ready':data['ready_for_candidate']=True
 else:data['final_candidate_checks'][0]['state']='passed'
 save(tmp_path,data)
 with pytest.raises(ValueError):validate(tmp_path)

def test_all_declared_approvals_and_checks_required_for_consistency(tmp_path):
 data=fixture_root(tmp_path)
 for gate in data['gates']:gate['state']='approved'
 for check in data['final_candidate_checks']:check['state']='passed';check['evidence']=['docs/local_evidence.txt']
 (tmp_path/'docs/local_evidence.txt').write_text('Test-only declaration, not an actual release result',encoding='utf-8')
 data['ready_for_candidate']=True;save(tmp_path,data)
 assert validate(tmp_path)['ready_for_candidate'] is True
 data['final_candidate_checks'][0]['state']='failed';save(tmp_path,data)
 with pytest.raises(ValueError):validate(tmp_path)
