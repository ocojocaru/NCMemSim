"""Exact proposed imports/constructors remain explicit and pending approval."""
from pathlib import Path
import json,subprocess,sys
import pytest
from scripts.validate_stable_api_proposal import build_proposal,render
from scripts.validate_release_readiness import validate
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def proposal():return build_proposal(ROOT)

def test_selected_surface_and_class_constructor_coverage(proposal):
 assert len(proposal['entries'])==198
 assert proposal==json.loads((ROOT/'docs/stable_api_proposal.json').read_text(encoding='utf-8'))
 paths={e['import_path'] for e in proposal['entries']}
 inventory=json.loads((ROOT/'docs/api_inventory.json').read_text(encoding='utf-8'))
 assert set(inventory['documented_imports'])<=paths
 assert {'ncmemsim.transport.base','ncmemsim.transport.engine','ncmemsim.__version__'}<=paths
 classes=[e for e in proposal['entries'] if e['kind']=='class']
 assert classes and all(e['runtime_call_signature'] is not None for e in classes)
 fit=next(e for e in proposal['entries'] if e['import_path']=='ncmemsim.fitting.FitParameter')
 assert fit['source_contract']['constructor'] is None
 assert 'initial_value' in fit['runtime_call_signature'] and 'lower_bound' in fit['runtime_call_signature']
 assert (ROOT/'docs/stable_api_proposal.md').read_text(encoding='utf-8')==render(proposal)

def test_root_alias_target_and_result_identity_are_distinct(proposal):
 root=next(e for e in proposal['entries'] if e['import_path']=='ncmemsim.SweepResult')
 assert root['definition_path']=='ncmemsim.simulator.SweepResult'
 assert 'voltages_V' in root['runtime_call_signature']
 module=next(e for e in proposal['entries'] if e['import_path']=='ncmemsim.transport.base')
 assert module['kind']=='module' and module['runtime_call_signature'] is None

def test_proposal_does_not_mark_approval_or_final_checks_passed(proposal):
 assert proposal['status']=='proposal_pending_approval'
 data=validate(ROOT)
 assert data['ready_for_candidate'] is False
 assert all(g['state']!='approved' for g in data['gates'])
 assert all(c['state']=='not_run' for c in data['final_candidate_checks'])

def test_runtime_signature_drift_is_observed(proposal,monkeypatch):
 import ncmemsim.fitting as fitting
 def changed(parameter_set,callback,*,new_default=True):pass
 monkeypatch.setattr(fitting,'FitParameter',changed)
 assert build_proposal(ROOT)!=proposal

def test_direct_read_only_script_matches_without_optional_scipy():
 subprocess.run([sys.executable,str(ROOT/'scripts/validate_stable_api_proposal.py')],cwd=ROOT.parent,check=True)
 code='import sys; from pathlib import Path; from scripts.validate_stable_api_proposal import build_proposal; build_proposal(Path.cwd()); assert "scipy" not in sys.modules'
 subprocess.run([sys.executable,'-c',code],cwd=ROOT,check=True)
