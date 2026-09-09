"""Reproducible local M3 regression; does not invoke any external provider."""
import csv
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--milestone',choices=['M3','M4'],default='M3')
milestone=parser.parse_args().milestone
OUT=ROOT/'docs/implementation-evidence'/milestone
OUT.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
results={}
transcript=[]
for suite in ('foundation','trust','domain'):
    command=[sys.executable,'-m','pytest',f'tests/{suite}',f'--confcutdir=tests/{suite}',
             '-q','--tb=short',f'--junitxml={OUT/suite}.xml']
    run=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
    transcript.extend([f'## {suite}\n',run.stdout,run.stderr])
    xml=ET.parse(OUT/f'{suite}.xml').getroot()
    cases=xml.findall('.//testcase')
    results[suite]={'tests':len(cases),'failures':sum(c.find('failure') is not None or c.find('error') is not None for c in cases),
                    'skipped':sum(c.find('skipped') is not None for c in cases),'exit_code':run.returncode}
    print(suite,results[suite],flush=True)
checks=[('typecheck',['npm.cmd','run','typecheck']),('build',['npm.cmd','run','build'])]
if milestone=='M4':
    checks.append(('extension_tests',['node','--test',*[str(path.relative_to(ROOT)) for path in sorted((ROOT/'tests/extension').glob('*.test.cjs'))]]))
for name,command in checks:
    run=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
    results[name]={'exit_code':run.returncode}
    if name=='extension_tests':
        import re
        for key in ('tests','pass','fail','skipped'):
            match=re.search(r'^# '+key+r' (\d+)$',run.stdout,re.M)
            results[name][key]=int(match[1]) if match else None
    transcript.extend([f'## {name}\n',run.stdout,run.stderr])
    print(name,results[name],flush=True)
manifest=list(csv.DictReader((ROOT/'docs/lld-versions/v0.2/SHA256-manifest.csv').open(encoding='utf-8-sig')))
unchanged=all(hashlib.sha256(Path(row['Path']).read_bytes()).hexdigest().upper()==row['Hash'].upper() for row in manifest)
results['approved_lld']={'files_checked':len(manifest),'unchanged':unchanged}
results['status']='IN_PROGRESS'
results['external_provider_calls']=0
results['qualification']='Engineering fixtures only; no owner/reviewer label approval or live provider qualification implied.'
(OUT/'summary.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
(OUT/'verification.txt').write_text('\n'.join(transcript),encoding='utf-8')
files=set((ROOT/'src/lila').rglob('*.py'))|set((ROOT/'src/lila/storage/migrations').glob('*.sql'))|set((ROOT/'tests').glob('domain/*.py'))|set((ROOT/'tests').glob('trust/*.py'))|set((ROOT/'tests').glob('foundation/*.py'))
files.update((ROOT/'extension/src').rglob('*.ts'))
files.update((ROOT/'tests/extension').glob('*.cjs'))
files.update(ROOT/name for name in ('requirements.in','requirements.lock','package.json','package-lock.json','pyproject.toml','scripts/m3_evidence.py'))
hashes={str(path.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}
(OUT/'source-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
environment={'python':sys.version,'platform':platform.platform(),'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()}}
(OUT/'environment.json').write_text(json.dumps(environment,indent=2)+'\n',encoding='utf-8')
traces=[]
for suite in ('foundation','trust','domain'):
    for case in ET.parse(OUT/f'{suite}.xml').getroot().findall('.//testcase'):
        name=case.attrib['name']
        module=case.attrib.get('classname','')
        source='/'.join(module.split('.'))+'.py'
        key=module+'::'+name
        requirements=['FR-003','FR-019','FR-029'] if suite!='domain' else ['FR-010','FR-013','FR-022'] if any(word in module for word in ('ai','checkpoint','grounding','worker','work_','extraction')) else ['FR-009','FR-012','FR-018','FR-028']
        if 'test_browser_' in module:
            requirements=['FR-002','FR-012','FR-014','FR-018']
        traces.append({'test_id':key,'milestone':milestone+' regression','source':source,
            'requirement_ids':requirements,'fixture_digest':hashes.get(source),
            'source_sha256':hashes.get(source),'preconditions':'Isolated local fixture, no external provider call',
            'duration_seconds':case.attrib.get('time'),'result':'failed' if case.find('failure') is not None or case.find('error') is not None else 'skipped' if case.find('skipped') is not None else 'passed',
            'evidence':f'{suite}.xml','fixture_label_approval':'Not claimed'})
(OUT/'test-traceability.json').write_text(json.dumps(traces,indent=2)+'\n',encoding='utf-8')
if not unchanged or any(value.get('exit_code',0) for value in results.values() if isinstance(value,dict)):
    raise SystemExit(1)
