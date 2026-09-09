"""Reservation → one-time claim → provider → usage; replay never resends a claim."""
import hashlib
from dataclasses import asdict
from lila.contracts.canonical import canonical
from lila.worker.provider import ResponsesProvider,build_request


async def invoke(coordinator, *, invocation_id,run_id,lease_id,generation,config_version,policy_id,facts,job_excerpt,provider=None):
    body=build_request(facts,job_excerpt)
    reservation={'invocation_id':invocation_id,'run_id':run_id,'lease_id':lease_id,'generation':generation,
                 'provider_config_version':config_version,'policy_id':policy_id,
                 'limits':{'max_input_tokens':32768,'max_output_tokens':2048},
                 'request_digest':hashlib.sha256(canonical(body)).hexdigest()}
    response=await coordinator.post('/internal/v1/ai/reservations',json=reservation)
    response.raise_for_status()
    reservation_id=response.json()['reservation_id']
    identity={'invocation_id':invocation_id,'generation':generation}
    response=await coordinator.post('/internal/v1/ai/claim',json=identity)
    response.raise_for_status()
    if response.json()['may_send'] is not True:
        return {'status':'RECONCILIATION_REQUIRED','value':None}
    response=await coordinator.post('/internal/v1/ai/credential',json=identity)
    response.raise_for_status()
    key=response.json()['api_key']
    try:
        result=await (provider or ResponsesProvider()).invoke(body,key)
    finally:
        key=None
        response=None
    usage=asdict(result)
    usage.pop('value')
    input_tokens=usage.pop('input_tokens')
    output_tokens=usage.pop('output_tokens')
    usage['usage']={'input_tokens':input_tokens,'output_tokens':output_tokens} if input_tokens is not None else None
    usage['reservation_id']=reservation_id
    response=await coordinator.post('/internal/v1/ai/results',json=dict(identity,**usage))
    response.raise_for_status()
    return {'status':result.status,'value':result.value}
