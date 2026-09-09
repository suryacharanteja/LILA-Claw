"""Private graph transport and owner-specified execution bounds."""
from uuid import UUID
from typing import Literal
from fastapi import Request
from pydantic import BaseModel,ConfigDict,Field,JsonValue
from lila.api.auth import COOKIE
from lila.security.sessions import AuthError
from lila.domain.core import DomainError


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')


class Execution(Strict):
    command_id:UUID
    expected_revision:int=Field(ge=1,strict=True)
    max_candidates:int=Field(ge=1,le=10000,strict=True)
    policy_id:UUID|None=None


class Scope(Strict):
    run_id:UUID
    lease_id:UUID
    generation:int=Field(ge=1,strict=True)


class Call(Scope):
    operation:Literal['readiness','criteria','discover_page','classify_candidates','prepare_facts','validate_payload','ensure_action','action_status','record_progress','finish_discovery','narrative_context','publish_narrative']
    args:list[JsonValue]=Field(default_factory=list,max_length=5)


class Acknowledge(Scope):
    state:Literal['WAITING','DONE']
    error_code:Literal['FACTS_REQUIRED','MANDATORY_CRITERIA_UNRESOLVED','CRITERIA_CHANGED','EXECUTION_PAUSED','EXECUTION_UNAVAILABLE','PROVIDER_NOT_ENABLED','TOKEN_BOUND_QUALIFICATION_REQUIRED','POLICY_REQUIRED','OUTCOME_UNRESOLVED','WORKER_ERROR','WORKER_TRANSPORT_ERROR','BROWSER_UNAVAILABLE','WORKER_UNAVAILABLE','AI_RECONCILIATION_REQUIRED','AI_OUTPUT_INVALID','AI_REQUEST_REJECTED','AI_BOUND_EXCEEDED','AI_CONTEXT_TOO_LARGE','INVALID_FACT_CONTEXT','BUDGET_EXHAUSTED','BUDGET_OR_POLICY_CHANGED','POLICY_EXPIRED','COST_CONFIGURATION_REQUIRED','COST_BOUND_INVALIDATED','PROVIDER_CONFIGURATION_CHANGED']|None=None


def attach_work(app,domain,sessions,workers,work):
    def auth(request):
        value=request.headers.get('Authorization','')
        try:
            generation=int(request.headers.get('X-Lila-Generation',''))
        except ValueError:
            raise AuthError('STALE_WORKER') from None
        if not value.startswith('Bearer '):
            raise AuthError('STALE_WORKER')
        return workers.authenticate(value[7:],generation)

    @app.post('/api/v1/tasks/{task}/execution')
    def execution(task:UUID,body:Execution,request:Request):
        owner=sessions.authenticate(request.cookies.get(COOKIE,''),request.headers.get('X-Lila-CSRF',''))['principal_id']
        return work.configure(owner,str(task),str(body.command_id),body.expected_revision,body.max_candidates,str(body.policy_id) if body.policy_id else None)

    @app.post('/internal/v1/work/next')
    def next_work(request:Request):
        return work.next(auth(request))

    @app.post('/internal/v1/work/call')
    def call(body:Call,request:Request):
        lengths={'readiness':0,'criteria':0,'discover_page':2,'classify_candidates':2,'prepare_facts':2,
                 'validate_payload':3,'ensure_action':3,'action_status':1,'record_progress':2,'finish_discovery':1,'narrative_context':2,'publish_narrative':3}
        if len(body.args)!=lengths[body.operation]:
            raise DomainError('INVALID_REQUEST',422)
        return work.call(auth(request),str(body.run_id),str(body.lease_id),body.generation,body.operation,body.args)

    @app.post('/internal/v1/work/acknowledge')
    def acknowledge(body:Acknowledge,request:Request):
        return work.acknowledge(auth(request),str(body.run_id),str(body.lease_id),body.generation,body.state,body.error_code)
