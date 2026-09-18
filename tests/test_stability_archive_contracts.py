"""Frozen published-tag archives: readers must not regenerate expected results."""
from pathlib import Path
import hashlib,json,subprocess,sys
import pytest
from ncmemsim.dtco import DTCOReport,RobustDTCOReport,SampleManifest
from ncmemsim.workflows import DatasetEvidence,WorkflowEvidence,AppliedWorkflowEvidence,WorkflowReport
from ncmemsim.hashing import canonical_hash
ROOT=Path(__file__).parent/'fixtures/archives/v0_14_0'
READERS={'dtco':DTCOReport,'robust':RobustDTCOReport,'workflow':WorkflowReport,
 'dataset_evidence':DatasetEvidence,'workflow_evidence':WorkflowEvidence,
 'applied_evidence':AppliedWorkflowEvidence,'sample_manifest':SampleManifest}

def original(name):return (ROOT/(name+'.json')).read_text(encoding='utf-8')
def signed(raw):
 key=next(k for k in ('report_hash','evidence_hash','manifest_hash') if k in raw)
 raw.pop(key);raw[key]=canonical_hash(raw)
 return json.dumps(raw,allow_nan=False)

@pytest.mark.parametrize('name',READERS)
def test_frozen_bytes_and_lossless_restore(name):
 inventory=json.loads((ROOT/'inventory.json').read_text())
 assert inventory['source_commit']=='f210f3fcf1e8d48806b0f9a94e564abc0aaabfc9'
 entry=next(e for e in inventory['files'] if e['file']==name+'.json')
 assert hashlib.sha256((ROOT/entry['file']).read_bytes()).hexdigest()==entry['sha256']
 data=json.loads(original(name));reader=READERS[name]
 restored=reader.from_json(original(name))
 assert restored.to_dict()==data
 assert reader.from_json(restored.to_json()).to_dict()==data
 detached=restored.to_dict();detached['schema_version']='changed'
 assert restored.to_dict()==data
 # JSON whitespace and key ordering do not change content identity.
 assert reader.from_json(json.dumps(data,indent=2)).to_dict()==data

@pytest.mark.parametrize('name',READERS)
@pytest.mark.parametrize('fault',['schema','extra','missing','hash','duplicate','nan','infinity'])
def test_reject_invalid_archives(name,fault):
 raw=json.loads(original(name));text=original(name)
 if fault=='duplicate':text=text.replace('{','{"schema_version":"duplicate",',1)
 elif fault in ('nan','infinity'):text=text.replace('{','{"nonfinite":'+('NaN' if fault=='nan' else 'Infinity')+',',1)
 elif fault=='hash':
  key=next(k for k in ('report_hash','evidence_hash','manifest_hash') if k in raw);raw[key]='0'*64;text=json.dumps(raw)
 else:
  if fault=='schema':raw['schema_version']='unsupported-future-v99'
  elif fault=='extra':raw['unknown_future_field']=True
  else:raw.pop('schema_version')
  text=signed(raw)
 with pytest.raises(ValueError):READERS[name].from_json(text)

def test_frozen_failure_and_scientific_links():
 w=WorkflowReport.from_json(original('workflow')).to_dict()
 assert w['scientific_summary']['scientific_status']=='FITTED'
 assert w['scientific_summary']['fit_data_origin']=='synthetic'
 assert w['workflow_evidence']==w['applied_workflow_evidence']['workflow_evidence']
 assert all(a['data']['counts']['failed']==3 for a in w['robust_report']['analyses'])
 h=RobustDTCOReport.from_json(original('robust')).to_dict()
 assert all(a['data']['counts']['failed']==3 for a in h['analyses'])
 assert json.loads(original('sample_manifest'))==h['analyses'][0]['data']['source']['manifest']

def test_restore_in_fresh_process_without_scipy_or_execution():
 code="""import sys,json
from pathlib import Path
from ncmemsim.dtco import DTCOReport,RobustDTCOReport,SampleManifest
from ncmemsim.workflows import DatasetEvidence,WorkflowEvidence,AppliedWorkflowEvidence,WorkflowReport
import ncmemsim.fitting as fitting
import ncmemsim.dtco.sampling as sampling
import ncmemsim.workflows.application as application
import ncmemsim.simulator as simulator
def forbidden(*a,**kw):raise AssertionError('execution during archive restoration')
fitting.run_least_squares_fit=forbidden
sampling.sample_variations=forbidden
application.run_program_pulse_read=forbidden
application.run_electro_optical_program_pulse_read=forbidden
simulator.Simulator.run=forbidden
root=Path(sys.argv[1])
for name,reader in [('dtco',DTCOReport),('robust',RobustDTCOReport),('workflow',WorkflowReport),('dataset_evidence',DatasetEvidence),('workflow_evidence',WorkflowEvidence),('applied_evidence',AppliedWorkflowEvidence),('sample_manifest',SampleManifest)]:
 text=(root/(name+'.json')).read_text();assert reader.from_json(text).to_dict()==json.loads(text)
assert 'scipy' not in sys.modules
"""
 subprocess.run([sys.executable,'-c',code,str(ROOT.resolve())],check=True)
