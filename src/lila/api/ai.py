"""Owner provider configuration and private, lease-scoped AI accounting endpoints."""
from uuid import UUID
from typing import Literal
from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel,ConfigDict,Field
from lila.api.auth import COOKIE
from lila.domain.ai import AI
from lila.domain.core import DomainError
from lila.security.sessions import AuthError
from lila.worker.provider import MODEL,validate_config,ProviderError

# Live hard-budget enablement awaits recorded tokenizer qualification, not a UI flag.
TOKEN_BOUND_QUALIFIED=False


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')


class Credential(Strict):
    command_id:UUID
    provider:Literal['openai']
    api_key:str=Field(min_length=1,max_length=1024,repr=False)


class Configuration(Strict):
    command_id:UUID
    account_id:UUID
    expected_revision:int=Field(ge=0,strict=True)
    credential_id:UUID
    model:Literal['gpt-4.1-mini-2025-04-14']
    input_rate:int=Field(gt=0,lt=2**53,strict=True)
    output_rate:int=Field(gt=0,lt=2**53,strict=True)
    checked_at:str
    enabled:bool=Field(strict=True)


class Limits(Strict):
    max_input_tokens:Literal[32768]
    max_output_tokens:Literal[2048]


class Reservation(Strict):
    invocation_id:UUID
    run_id:UUID
    lease_id:UUID
    generation:int=Field(ge=1,strict=True)
    provider_config_version:UUID
    policy_id:UUID
    request_digest:str=Field(pattern='^[0-9a-f]{64}$')
    limits:Limits


class Invocation(Strict):
    invocation_id:UUID
    generation:int=Field(ge=1,strict=True)


class Usage(Strict):
    input_tokens:int=Field(ge=0,strict=True)
    output_tokens:int=Field(ge=0,strict=True)


class Result(Invocation):
    reservation_id:UUID
    status:Literal['COMPLETED','INVALID','REJECTED','UNCERTAIN','BOUND_EXCEEDED']
    usage:Usage|None
    provider_request_id:str|None=Field(default=None,max_length=200)


def attach_ai(app,domain,sessions,workers,credentials):
    service=AI(domain)
    def auth(request):
        value=request.headers.get('Authorization','')
        try:
            generation=int(request.headers.get('X-Lila-Generation',''))
        except ValueError:
            raise AuthError('STALE_WORKER') from None
        if not value.startswith('Bearer '):
            raise AuthError('STALE_WORKER')
        return workers.authenticate(value[7:],generation)

    @app.post('/api/v1/provider/credentials')
    def save(body:Credential,request:Request):
        return credentials.save(request.cookies.get(COOKIE,''),request.headers.get('X-Lila-CSRF',''),str(body.command_id),body.api_key)

    @app.post('/api/v1/provider/configuration')
    def configure(body:Configuration,request:Request):
        owner=sessions.authenticate(request.cookies.get(COOKIE,''),request.headers.get('X-Lila-CSRF',''))['principal_id']
        if not credentials.exists(str(body.credential_id)):
            raise DomainError('PROVIDER_CREDENTIAL_REQUIRED',422)
        config={k:getattr(body,k) for k in ('model','input_rate','output_rate','checked_at','enabled')}
        config['token_bound_qualified']=TOKEN_BOUND_QUALIFIED
        if body.enabled:
            try:
                validate_config(config,domain.clock())
            except ProviderError as exc:
                raise DomainError('TOKEN_BOUND_QUALIFICATION_REQUIRED' if not TOKEN_BOUND_QUALIFIED else str(exc),422) from None
        def change(db):
            account=domain.account(db,str(body.account_id))
            old=db.execute('SELECT revision FROM provider_settings WHERE account_id=?',(account,)).fetchone()
            revision=old[0] if old else 0
            if revision!=body.expected_revision:
                raise DomainError('REVISION_CONFLICT')
            version=domain.content(db,'provider_config',config)
            db.execute('INSERT INTO provider_settings VALUES(?,?,?,?) ON CONFLICT(account_id) DO UPDATE SET config_version=excluded.config_version,credential_id=excluded.credential_id,revision=excluded.revision',(account,version,str(body.credential_id),revision+1))
            domain.event(db,'PROVIDER_CONFIGURED','account',account,revision+1)
            return {'config_version':version,'revision':revision+1,'enabled':body.enabled}
        return domain.command(owner,str(body.command_id),['provider_configuration',body.model_dump(mode='json')],change)

    @app.post('/internal/v1/ai/reservations')
    def reserve(body:Reservation,request:Request):
        worker=auth(request)
        def scope(db):
            row=db.execute('SELECT p.config_version FROM provider_settings p JOIN tasks t ON t.account_id=p.account_id JOIN runs r ON r.task_id=t.id WHERE r.id=?',(str(body.run_id),)).fetchone()
            if row!=(str(body.provider_config_version),):
                raise DomainError('PROVIDER_CONFIGURATION_CHANGED',403)
        domain.writer.call(scope,transaction=False)
        return service.reserve(worker,invocation_id=str(body.invocation_id),run_id=str(body.run_id),lease_id=str(body.lease_id),generation=body.generation,config_version=str(body.provider_config_version),policy_id=str(body.policy_id),request_digest=body.request_digest)

    @app.post('/internal/v1/ai/claim')
    def claim(body:Invocation,request:Request):
        return service.claim(auth(request),str(body.invocation_id),body.generation)

    @app.post('/internal/v1/ai/credential')
    def key(body:Invocation,request:Request):
        worker=auth(request)
        def scoped(db):
            row=db.execute("SELECT a.run_id,o.lease_id,p.credential_id,a.config_version,p.config_version FROM ai_invocations a JOIN ai_ownership o ON o.invocation_id=a.id JOIN runs r ON r.id=a.run_id JOIN tasks t ON t.id=r.task_id JOIN provider_settings p ON p.account_id=t.account_id WHERE a.id=? AND o.worker_id=? AND o.generation=? AND a.state='CLAIMED'",(str(body.invocation_id),worker,body.generation)).fetchone()
            if not row or row[3]!=row[4]:
                raise DomainError('SCOPE_DENIED',403)
            domain._lease(db,row[1],worker,body.generation,row[0])
            return row[2]
        with domain.dispatch_lock:
            credential=domain.writer.call(scoped,transaction=False)
            return {'api_key':credentials.read(credential)}

    @app.post('/internal/v1/ai/results')
    def result(body:Result,request:Request):
        worker=auth(request)
        row=domain.writer.call(lambda db:db.execute('SELECT reservation_id FROM ai_invocations WHERE id=?',(str(body.invocation_id),)).fetchone(),transaction=False)
        if row!=(str(body.reservation_id),):
            raise DomainError('SCOPE_DENIED',403)
        return service.result(worker,str(body.invocation_id),body.generation,status=body.status,
            input_tokens=body.usage.input_tokens if body.usage else None,
            output_tokens=body.usage.output_tokens if body.usage else None,provider_request_id=body.provider_request_id)
