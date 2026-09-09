"""Export the existing engineering truth labels for owner/reviewer inspection."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests/domain')]
source=ROOT/'tests/domain/test_ai.py'
fixture=runpy.run_path(str(source))
out=ROOT/'docs/implementation-evidence/M3'
cases=[]
for index in range(100):
    fact=fixture['fact'](index)
    value=fixture['narrative'](fact)
    current=[fact]
    expected=index<30 or 70<=index<80
    if index<30:
        group,reason='Known','Exact current fact text is supported.'
    elif index<50:
        group,reason='Missing','Required field is missing; do not invent its value.'
        value['missing_fields']=['work_authorization' if index%2 else 'salary']
    elif index<70:
        group,reason='Contradictory or stale','The referenced fact is absent or its current text has changed.'
        current=[] if index%2 else [dict(fact,text='Owner corrected this fact.')]
    elif index<90:
        group='Narrative'
        if index>=80:
            reason='Connector introduces unsupported leadership and education claims.'
            value['segments'].append({'kind':'connector','fact_ref':None,'text':'I led a team of 100 and earned a doctorate.'})
        else:
            reason='Whitespace plus exact fact text introduces no new claim.'
            value['segments'].insert(0,{'kind':'connector','fact_ref':None,'text':'\n'})
    else:
        group,reason='Material edit','Edited fact text adds unsupported leadership experience.'
        value['segments'][0]['text']+=' I also have ten years of leadership experience.'
    try:
        fixture['grounded'](value,current)
        accepted=True
    except fixture['ProviderError']:
        accepted=False
    if accepted!=expected:
        raise RuntimeError(f'Fixture expectation mismatch: {index}')
    cases.append({'test_id':f'T-FACT-{index+1:03}','category':group,'current_facts':current,
                  'proposed_output':value,'expected':'ACCEPT' if expected else 'BLOCK',
                  'reason':reason,'review_status':'PENDING'})
payload={'status':'PROPOSED_ENGINEERING_LABELS','source':'tests/domain/test_ai.py',
         'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'cases':cases}
data=(json.dumps(payload,indent=2,ensure_ascii=False)+'\n').encode()
(out/'factual-review.json').write_bytes(data)
lines=['# M3 factual fixture review','',
       'Status: **Pending owner/reviewer review. No approval recorded.**','',
       'This package makes the existing 100 engineering labels inspectable. It is not business UAT or a live-provider evaluation. All facts are synthetic. ACCEPT means the current strict grounding validator accepts the content; it does not authorize submission. BLOCK means owner clarification or correction is required.','',
       'The approved LLD-08 requires owner/reviewer-approved fixture truth labels. Review the expected result and reasoning below; the accompanying JSON contains every exact input and output. Report corrections by test ID, or explicitly approve this package. Approval applies only to these labels, not provider spending, browser actions or milestone completion.','',
       '**Coverage limitation:** these are repeated variants of a small number of templates (30 known, 20 missing, 20 contradictory/stale, 20 narrative and 10 material edits). They validate the exact-quote policy, not broad factual reasoning, varied form coverage or fluent paraphrasing. A provider-quality evaluation needs a more representative corpus before it can support broader claims.','',
       f'Package SHA-256: `{hashlib.sha256(data).hexdigest()}`','',
       '[Exact cases](factual-review.json)','',
       '| Test ID | Category | Expected | Reason |','|---|---|---|---|']
lines.extend(f"| {c['test_id']} | {c['category']} | {c['expected']} | {c['reason']} |" for c in cases)
(out/'factual-review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'Exported {len(cases)} cases; labels pending review; 0 provider calls.')
