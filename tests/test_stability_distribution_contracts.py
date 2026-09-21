"""Local distribution inventory/byte gates; no build, pip or network."""
import io,json,tarfile,zipfile
from pathlib import Path
import pytest
from scripts.validate_dtco_distribution import REQUIRED,SOURCE_REQUIRED,check_archive,check_source_content,PROBE
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('name',['ncmemsim/simulator.py','ncmemsim/materials/optics/near_edge.py','ncmemsim/device_calibration.py','ncmemsim/constants.py'])
@pytest.mark.parametrize('kind',['wheel','sdist'])
def test_all_package_modules_required(tmp_path,name,kind):
 assert name in REQUIRED
 names=(REQUIRED if kind=='wheel' else REQUIRED|SOURCE_REQUIRED)-{name}
 path=tmp_path/('audit.whl' if kind=='wheel' else 'audit.tar.gz')
 if kind=='wheel':
  with zipfile.ZipFile(path,'w') as z:
   for item in names:z.writestr(item,b'')
 else:
  with tarfile.open(path,'w:gz') as z:
   for item in names:z.addfile(tarfile.TarInfo('audit/'+item))
 with pytest.raises(ValueError,match=name):check_archive(path)

@pytest.mark.parametrize('extra',['data/reference/new.csv','examples/new_reference.py','tests/fixtures/archives/older/archive.json','docs/new.md'])
@pytest.mark.parametrize('fault',[None,'missing','changed','duplicate','symlink'])
def test_dynamic_source_bytes(tmp_path,extra,fault):
 root=tmp_path/'checkout';names=REQUIRED|SOURCE_REQUIRED|{'README.md','MANIFEST.in',extra}
 for name in names:
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(('original '+name).encode())
 path=tmp_path/'source.tar.gz'
 with tarfile.open(path,'w:gz') as z:
  for name in sorted(names):
   if name==extra and fault=='missing':continue
   content=(root/name).read_bytes()
   if name==extra and fault=='changed':content=b'changed'
   info=tarfile.TarInfo('source/'+name);info.size=len(content)
   if name==extra and fault=='symlink':info.type=tarfile.SYMTYPE;info.linkname='other';info.size=0;z.addfile(info)
   else:z.addfile(info,io.BytesIO(content))
   if name==extra and fault=='duplicate':z.addfile(info,io.BytesIO(content))
 if fault:
  with pytest.raises(ValueError,match=extra):check_source_content(path,root)
 else:assert check_source_content(path,root)==len(names)

def test_actual_source_and_package_inventory():
 assert REQUIRED=={p.relative_to(ROOT).as_posix() for p in (ROOT/'ncmemsim').rglob('*.py')}
 assert len(REQUIRED)==87
 for name in SOURCE_REQUIRED:assert (ROOT/name).is_file(),name
 assert {'LICENSE','pyproject.toml'}<=SOURCE_REQUIRED
 assert 'graft data/reference' in (ROOT/'MANIFEST.in').read_text(encoding='utf-8')
 assert 'recursive-include tests/fixtures/archives *.json' in (ROOT/'MANIFEST.in').read_text(encoding='utf-8')
 compile(PROBE,'installed-probe','exec')

def test_isolation_and_frozen_probe_wiring():
 import ast
 from scripts import validate_dtco_distribution as validator
 tree=ast.parse(Path(validator.__file__).read_text(encoding='utf-8'))
 main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
 calls=[n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='run']
 assert any(any(isinstance(a,ast.Constant) and a.value=='-I' for a in call.args) for call in calls)
 # Execute the actual frozen-reader portion of the installed probe without building.
 import shutil,subprocess,sys
 from tempfile import TemporaryDirectory
 with TemporaryDirectory(dir=ROOT.parent) as temporary:
  work=Path(temporary);shutil.copytree(ROOT/'tests/fixtures/archives/v0_14_0',work/'archive_fixtures')
  snippet=PROBE.split('# Frozen published-code archives must be readable by the installed package.')[1].split('print("Installed DTCO reference,')[0]
  prelude='import json\nfrom pathlib import Path\nfrom ncmemsim.dtco import DTCOReport,RobustDTCOReport\nfrom ncmemsim.workflows import DatasetEvidence,WorkflowEvidence,AppliedWorkflowEvidence,WorkflowReport\nwork=Path('+repr(str(work))+')\n'
  subprocess.run([sys.executable,'-c',prelude+snippet],cwd=ROOT,check=True)


def test_legacy_manifest_identity_scope_and_config_alias(monkeypatch):
 from ncmemsim.builder import DeviceBuilder
 from ncmemsim.reproducibility import build_reproducibility_manifest
 from ncmemsim.hashing import canonical_hash
 monkeypatch.setenv('GITHUB_SHA','declared-ci-commit')
 config={'internal_dt_s':1e-5};d=DeviceBuilder.v2(1)
 a=build_reproducibility_manifest(d,simulation_config=config,random_seed=1)
 b=build_reproducibility_manifest(d,simulation_config=config,random_seed=2)
 assert a['schema_version']==2 and a['physics_model']=='PhaseD6'
 assert a['git_commit']=='declared-ci-commit'
 assert a['simulation_hash']==b['simulation_hash'] # Seed/runtime are recorded outside this hash.
 assert a['runtime']['numpy_version']
 assert a['material_models'][0]['properties']
 recorded_hash=a['simulation_hash'];config['internal_dt_s']=2e-5
 assert a['simulation_config']['internal_dt_s']==2e-5 # Legacy shallow reference, not immutable evidence.
 assert canonical_hash({'device':a['device'],'physics_model':a['physics_model'],'config':a['simulation_config']})!=recorded_hash
 c=build_reproducibility_manifest(d,simulation_config=config)
 assert c['simulation_hash']!=recorded_hash


def test_git_commit_unavailable_is_none(monkeypatch):
 import ncmemsim.reproducibility as repro
 monkeypatch.delenv('GITHUB_SHA',raising=False)
 def unavailable(*args,**kwargs):raise OSError('git unavailable')
 monkeypatch.setattr(repro.subprocess,'check_output',unavailable)
 assert repro.git_commit() is None
