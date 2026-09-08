"""Owner-session domain endpoints. Internal adapters are deliberately not public routes."""
from fastapi import Request,Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,ConfigDict,Field
from uuid import UUID
from typing import Literal
import asyncio
import json
from lila.api.auth import COOKIE,error
from lila.domain.core import DomainError


class PolicyCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    command_id: UUID
    expected_revision: int = Field(ge=1,strict=True)
    operation: Literal['revise','revoke']
    policy: dict | None = None


class ConfirmOperation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    command_id: UUID
    expected_revision: int = Field(ge=1,strict=True)
    preview_digest: str = Field(pattern='^[0-9a-f]{64}$')


class SelectDocument(BaseModel):
    model_config = ConfigDict(extra='forbid')
    command_id: UUID
    expected_revision: int = Field(ge=1,strict=True)
    operation: Literal['select']
    source_version: UUID
    format: Literal['pdf','docx']


def attach_domain(app,sessions,domain,quit_callback=None):
    upload_lock = asyncio.Lock()
    @app.exception_handler(DomainError)
    async def domain_error(request,exc):
        return error(exc.code,exc.status)

    def principal(request,write=False):
        return sessions.authenticate(request.cookies.get(COOKIE,''),request.headers.get('X-Lila-CSRF','') if write else None)['principal_id']

    @app.post('/api/v1/documents/uploads')
    async def upload(request:Request):
        owner = principal(request,True)
        if not hasattr(domain,'documents'):
            raise DomainError('DOCUMENT_SERVICE_UNAVAILABLE',503)
        if upload_lock.locked():
            raise DomainError('UPLOAD_BUSY',429)
        await upload_lock.acquire()
        try:
            from lila.api.uploads import read_upload
            body = await read_upload(request)
            # Re-check credentials after a potentially long receive, before accepting work.
            principal(request,True)
            receipt = await run_in_threadpool(domain.documents.accept,owner,**body)
            # Return the durable acceptance receipt; status reports publication's current result.
            await run_in_threadpool(domain.documents.publish,receipt['upload_id'],body['data'],body['media_type'])
            return receipt
        finally:
            upload_lock.release()

    @app.get('/api/v1/documents/uploads/{id}')
    def upload_status(id:str,request:Request):
        principal(request)
        return domain.documents.status(id)

    @app.post('/api/v1/documents/{id}/commands')
    def select_document(id:str,body:SelectDocument,request:Request):
        return domain.documents.select(principal(request,True),id,str(body.command_id),body.expected_revision,str(body.source_version),body.format)

    @app.post('/api/v1/tasks')
    async def create_task(request:Request):
        owner = principal(request,True)
        return await run_in_threadpool(domain.create_task,owner,await request.json())

    @app.get('/api/v1/tasks/{id}')
    def task(id:str,request:Request):
        principal(request)
        return domain.task(id)

    @app.post('/api/v1/tasks/{id}/commands')
    async def task_command(id:str,request:Request):
        owner = principal(request,True)
        return await run_in_threadpool(domain.task_command,owner,id,await request.json())

    @app.post('/api/v1/execution/commands')
    async def global_command(request:Request):
        owner = principal(request,True)
        body = await request.json()
        receipt = await run_in_threadpool(domain.global_command,owner,body)
        if body['operation']=='quit' and quit_callback:
            quit_callback()
        return receipt

    @app.post('/api/v1/facts/commands')
    async def fact_command(request:Request,account_id:str):
        owner = principal(request,True)
        return await run_in_threadpool(domain.fact_command,owner,account_id,await request.json())

    @app.post('/api/v1/policies')
    async def policy(request:Request):
        owner = principal(request,True)
        return await run_in_threadpool(domain.create_policy,owner,await request.json())

    @app.post('/api/v1/policies/{id}/commands')
    def policy_command(id:str,body:PolicyCommand,request:Request):
        return domain.policy_command(principal(request,True),id,str(body.command_id),body.expected_revision,body.operation,body.policy)

    @app.post('/api/v1/reviews/{id}/commands')
    async def approval(id:str,request:Request):
        owner = principal(request,True)
        return await run_in_threadpool(domain.approval_command,owner,id,await request.json())

    @app.post('/api/v1/applications/{id}/manual-outcome')
    async def manual(id:str,request:Request):
        owner = principal(request,True)
        return await run_in_threadpool(domain.manual_outcome,owner,id,await request.json())

    @app.get('/api/v1/commands/{id}')
    def receipt(id:str,request:Request):
        return domain.get_receipt(principal(request),id)

    @app.get('/api/v1/operations/{id}')
    def correction(id:str,request:Request):
        principal(request)
        return domain.correction(id)

    @app.post('/api/v1/operations/{id}/confirm')
    def confirm(id:str,body:ConfirmOperation,request:Request):
        return domain.confirm_correction(principal(request,True),id,str(body.command_id),body.expected_revision,body.preview_digest)

    @app.get('/api/v1/events')
    def events(request:Request,after:str|None=None):
        owner = principal(request)
        initial = after or request.headers.get('Last-Event-ID')
        async def stream():
            cursor = initial
            while not await request.is_disconnected():
                try:
                    await run_in_threadpool(principal,request)
                    page = await run_in_threadpool(domain.events_page,owner,cursor)
                except DomainError as exc:
                    yield 'event: snapshot_required\ndata: '+json.dumps({'code':exc.code})+'\n\n'
                    return
                except Exception as exc:
                    from lila.security.sessions import AuthError
                    if not isinstance(exc,AuthError):
                        raise
                    return
                for event in page['events']:
                    yield 'id: '+event['cursor']+'\nevent: state_event\ndata: '+json.dumps(event)+'\n\n'
                cursor = page['next_cursor']
                if len(page['events'])<100:
                    yield ': heartbeat\n\n'
                    await asyncio.sleep(5)
        return StreamingResponse(stream(),media_type='text/event-stream')

    def register_list(kind):
        def listing(request:Request,account_id:str,after:str|None=None,limit:int=Query(100,ge=1,le=200)):
            return domain.list_entities(principal(request),kind,account_id,after,limit)
        app.add_api_route('/api/v1/'+kind,listing,methods=['GET'])
    for kind in ('tasks','jobs','applications','facts','documents','policies','history'):
        register_list(kind)
