"""Link each approved cost case to concrete results, without declaring M3 accepted."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/implementation-evidence/M3'
MAPPING={
 'T-COST-01':('Per-run action cap',['test_run_cap_counts_attempts_independently_of_daily_cap']),
 'T-COST-02':('Cross-run daily cap',['test_daily_cap_and_confirmed_duplicate','test_concurrent_runs_cannot_reserve_beyond_shared_daily_budget']),
 'T-COST-03':('Timezone edit',['test_timezone_roundtrip_and_late_usage_do_not_reset_or_double_budget','test_timezone_changes_roundtrip_and_late_release']),
 'T-COST-04':('Invocation timeout',['test_ai_claim_timeout_late_usage_and_no_double_charge','test_provider_transport_contract[timeout]']),
 'T-COST-05':('Unknown or stale rates',['test_unknown_or_invalid_rates_cannot_reserve_budget','test_ai_stale_prices_and_disabled_provider']),
 'T-COST-06':('Reservation reconciliation',['test_restart_releases_unsent_ai_and_retains_claimed_budget','test_replacement_worker_cannot_claim_or_reconcile_predecessor_invocation','test_failed_attempt_migration_repairs_linked_windows_once']),
}
cases=ET.parse(OUT/'domain.xml').getroot().findall('.//testcase')
hashes=json.loads((OUT/'source-hashes.json').read_text())
records=[]
for key,(description,prefixes) in MAPPING.items():
    matches=[]
    for prefix in prefixes:
        selected=[case for case in cases if case.attrib['name']==prefix or case.attrib['name'].startswith(prefix+'[')]
        if not selected:
            raise RuntimeError('Missing evidence: '+prefix)
        for case in selected:
            path='/'.join(case.attrib['classname'].split('.'))+'.py'
            if hashes.get(path)!=hashlib.sha256((ROOT/path).read_bytes()).hexdigest():
                raise RuntimeError('Stale evidence: '+path)
            if any(case.find(tag) is not None for tag in ('failure','error','skipped')):
                raise RuntimeError('Non-passing evidence: '+case.attrib['name'])
            matches.append({'test_id':case.attrib['classname']+'::'+case.attrib['name'],'source':path,'source_sha256':hashes[path],'result':'passed'})
    records.append({'acceptance_id':key,'description':description,'status':'LOCAL_EVIDENCE_PASSED','tests':matches})
(OUT/'cost-acceptance.json').write_text(json.dumps({'milestone_status':'IN_PROGRESS','scope':'Local deterministic evidence; not provider, browser or sponsor acceptance','cases':records},indent=2)+'\n')
lines=['# M3 cost acceptance evidence','',
       'All six approved T-COST categories have passing local evidence with source hashes checked against the last regression. This is component evidence, not M3 exit approval, live-provider qualification or business UAT.','',
       'T-COST-01 tests the approved per-run action cap; the monetary budget is separately checked across runs sharing a policy. See exit-review.md for the baseline interpretation.','']
for record in records:
    lines.extend([f"## {record['acceptance_id']} — {record['description']}",''])
    lines.extend(f"- `{test['test_id']}` — passed" for test in record['tests'])
    lines.append('')
lines.extend(['Exact hashes and test references: [cost-acceptance.json](cost-acceptance.json).','',
              'Still open: complete replay-matrix mapping; factual-label review; representative provider evaluation corpus; full request/token-bound qualification; authorized real-provider evaluation; M4 browser integration.'])
(OUT/'cost-acceptance.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('6 cost categories linked to passing, source-verified local evidence.')
