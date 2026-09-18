"""Audit release-candidate documentation without changing tracked site output."""
from pathlib import Path
import subprocess
import tempfile
import sys

repository = Path.cwd().resolve()
if not (repository / "docs/dtco.md").is_file():
    raise SystemExit("Run from the repository root after applying the docs audit.")
with tempfile.TemporaryDirectory(prefix="ncmemsim-doc-audit-") as name:
    temporary=Path(name)
    site=temporary/"site"
    subprocess.run([sys.executable,"-m","mkdocs","build","--strict","--site-dir",str(site)],cwd=repository,check=True)
    from pathlib import Path
    from html.parser import HTMLParser
    from urllib.parse import urlsplit,unquote
    import re
    root=site.resolve()
    class Parser(HTMLParser):
     def __init__(self): super().__init__(); self.ids=set(); self.links=[]
     def handle_starttag(self,tag,attrs):
      attrs=dict(attrs)
      if 'id' in attrs:self.ids.add(attrs['id'])
      for attr in ('href','src'):
       if attrs.get(attr):self.links.append(attrs[attr])
    parsed={}
    for path in root.rglob('*.html'):
     p=Parser();p.feed(path.read_text(encoding='utf-8'));parsed[path.resolve()]=p
    errors=set();checks=0
    for path,p in parsed.items():
     for link in p.links:
      url=urlsplit(link)
      if url.scheme or url.netloc:continue
      target=path if not url.path else ((root/unquote(url.path).lstrip('/')) if url.path.startswith('/') else path.parent/unquote(url.path)).resolve()
      if target.is_dir():target=target/'index.html'
      checks+=1
      if not target.exists():errors.add((str(path.relative_to(root)),link,'missing target'))
      elif url.fragment and target.suffix=='.html' and unquote(url.fragment) not in parsed[target.resolve()].ids:
       errors.add((str(path.relative_to(root)),link,'missing anchor'))
    print('Rendered pages:',len(parsed),'local references checked:',checks,'errors:',len(errors))
    for error in sorted(errors):print(error)
    assert not errors
    # Verify repository-relative README links/images, excluding URLs and anchors.
    repo=repository
    s=(repo/'README.md').read_text(encoding='utf-8')
    links=re.findall(r'\]\(([^\s)]+)',s)+re.findall(r'(?:src|href)="([^"]+)"',s)
    for link in links:
     u=urlsplit(link)
     if not u.scheme and u.path:assert (repo/unquote(u.path)).exists(),link
    print('README local file references: PASS')

    from pathlib import Path
    import ast,importlib,re,sys
    repo=repository;sys.path.insert(0,str(repo))
    counts={'python_blocks':0,'syntax_complete':0,'imports_checked':0};syntax=[];missing=[]
    for path in [repo/'README.md',*sorted((repo/'docs').glob('*.md'))]:
     if path.name=='NCMemSim_v6_Software_Design_Specification_Rev1.md':continue
     for i,b in enumerate(re.findall(r'```python\s*\n(.*?)```',path.read_text(encoding='utf-8'),re.S)):
      counts['python_blocks']+=1
      try:t=ast.parse(b)
      except SyntaxError as e:syntax.append((path.name,i,e.msg));continue
      counts['syntax_complete']+=1
      for n in ast.walk(t):
       if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('ncmemsim'):
        try:
         module=importlib.import_module(n.module)
         for a in n.names:
          if a.name!='*':getattr(module,a.name);counts['imports_checked']+=1
        except (ImportError,AttributeError) as e:missing.append((path.name,i,str(e)))
    print(counts)
    print('Partial/syntax blocks:',syntax)
    print('Missing public imports:',missing)

    assert not syntax and not missing

    from pathlib import Path
    import re,sys
    r=repository
    sys.path.insert(0,str(r))
    blocks=re.findall(r'```python\n(.*?)```',(r/'docs/dtco.md').read_text(encoding='utf-8'),re.S)
    contexts=[]
    for i,block in enumerate(blocks[:5]):
        context={'__name__':'__documentation_example__'}
        exec(compile(block,'docs/dtco.md block '+str(i),'exec'),context)
        contexts.append(context)
        print('DTCO standalone block',i,'PASS')
    # Bundle example explicitly continues from G4; export to workspace.
    block=blocks[5].replace('"results/my-dtco-study"',repr(str(temporary/'report-example')))
    exec(compile(block,'G6 report continuation','exec'),contexts[3])
    print('G6 report continuation and restoration/export PASS')

    print("Documentation audit verification PASS; no staging/commit/push.")

    for i, block in enumerate(re.findall(r"```python\n(.*?)```", (repository/"docs/robust_dtco.md").read_text(encoding="utf-8"), re.S)):
        exec(compile(block, "Robust DTCO example " + str(i), "exec"), {"__name__": "__documentation_example__"})
    print("H1–H6 examples PASS")


    for i, block in enumerate(re.findall(r"```python\n(.*?)```", (repository/"docs/scientific_workflows.md").read_text(encoding="utf-8"), re.S)):
        exec(compile(block, "Scientific workflow example " + str(i), "exec"), {"__name__": "__documentation_example__"})
    print("I1–I6 documentation examples PASS")
