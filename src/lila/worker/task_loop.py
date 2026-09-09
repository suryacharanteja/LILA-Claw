"""Consume bounded graph assignments while independent heartbeats renew leases."""
import asyncio
import httpx
from langgraph.types import Command
from lila.worker.graph import compile_graph
from lila.worker.coordinator import Coordinator,NarrativeUnavailable
from lila.worker.provider import ProviderError
from lila.runtime.checkpointer import CoordinatorSaver


async def run_assignment(client,assignment):
    scope={key:assignment[key] for key in ('run_id','lease_id','generation')}
    config={'configurable':{'thread_id':scope['run_id'],'checkpoint_ns':''},
            'recursion_limit':150010}
    saver=CoordinatorSaver(scope['run_id'],scope['generation'],None,client,namespace_prefix=assignment['namespace']+'/')
    graph=compile_graph(Coordinator(client,assignment),saver)
    error=None
    state='WAITING'
    try:
        snapshot=await graph.aget_state(config)
        if snapshot.values and snapshot.values.get('complete') and not snapshot.next:
            state='DONE'
        else:
            value=Command(resume=True) if snapshot.interrupts else None if snapshot.values else {'run_id':scope['run_id']}
            result=await graph.ainvoke(value,config)
            if result.get('__interrupt__'):
                reasons=result['__interrupt__'][0].value.get('blocker_ids',[])
                error=next((reason for reason in reasons if reason in {'FACTS_REQUIRED','OUTCOME_UNRESOLVED','MANDATORY_CRITERIA_UNRESOLVED','BROWSER_UNAVAILABLE','WORKER_UNAVAILABLE'}),None)
            if result.get('complete') and not result.get('__interrupt__'):
                state='DONE'
    except NarrativeUnavailable as exc:
        error=exc.code
    except ProviderError as exc:
        code=str(exc)
        error=code if code in {'AI_CONTEXT_TOO_LARGE','INVALID_FACT_CONTEXT','FACTS_REQUIRED'} else 'WORKER_ERROR'
    except httpx.TransportError:
        # No replay of a possibly committed call in this assignment. The saved
        # graph and one-time provider claim govern a subsequent recovery.
        error='WORKER_TRANSPORT_ERROR'
    except httpx.HTTPStatusError as exc:
        code=exc.response.json().get('code')
        if code in {'STALE_LEASE','STALE_WORKER','RUN_TERMINAL'}:
            return
        allowed={'FACTS_REQUIRED','MANDATORY_CRITERIA_UNRESOLVED','CRITERIA_CHANGED','EXECUTION_PAUSED','EXECUTION_UNAVAILABLE','PROVIDER_NOT_ENABLED','TOKEN_BOUND_QUALIFICATION_REQUIRED','POLICY_REQUIRED','OUTCOME_UNRESOLVED','BUDGET_EXHAUSTED','BUDGET_OR_POLICY_CHANGED','POLICY_EXPIRED','COST_CONFIGURATION_REQUIRED','COST_BOUND_INVALIDATED','PROVIDER_CONFIGURATION_CHANGED'}
        error=code if code in allowed else 'WORKER_ERROR'
    try:
        response=await client.post('/internal/v1/work/acknowledge',json=dict(scope,state=state,error_code=error))
    except httpx.TransportError:
        # Acknowledgement may already have committed. Return to assignment polling:
        # terminal runs disappear; unacknowledged work resumes its saved graph.
        # Do not turn a lost reply into a worker-process failure or replay effects.
        return
    if response.status_code==403:
        return
    response.raise_for_status()


async def tasks(client):
    while True:
        response=await client.post('/internal/v1/work/next',json={})
        response.raise_for_status()
        assignment=response.json()
        if assignment['available']:
            await run_assignment(client,assignment)
        await asyncio.sleep(1)
