from fastapi import Request
from fastapi.responses import Response
from fastapi.concurrency import run_in_threadpool
from lila.domain.extraction import Extraction
from lila.security.sessions import AuthError


def attach_extraction(app,domain,workers):
    service=Extraction(domain)
    def auth(request):
        header=request.headers.get('Authorization','')
        try:
            generation=int(request.headers.get('X-Lila-Generation',''))
        except ValueError:
            raise AuthError('STALE_WORKER') from None
        if not header.startswith('Bearer '):
            raise AuthError('STALE_WORKER')
        return workers.authenticate(header[7:],generation),generation

    @app.post('/internal/v1/documents/next')
    def next_document(request:Request):
        return service.next(*auth(request))

    @app.get('/internal/v1/documents/{operation}/data')
    def data(operation:str,request:Request):
        return Response(service.data(*auth(request),operation),media_type='application/octet-stream')

    @app.post('/internal/v1/documents/{operation}/result')
    async def result(operation:str,request:Request):
        worker,generation=auth(request)
        body=await request.json()
        return await run_in_threadpool(service.result,worker,generation,operation,body)
