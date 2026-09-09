"""Private worker checkpoint routes; no owner-cookie or extension fallback."""
from fastapi import Request, Query
from lila.api.auth import error
from lila.domain.checkpoints import Checkpoints
from lila.domain.core import DomainError
from lila.security.sessions import AuthError
from lila.contracts import checkpoint_json as codec


def attach_checkpoints(app, domain, workers):
    store = Checkpoints(domain)

    def authenticate(request):
        authorization = request.headers.get("Authorization", "")
        try:
            generation = int(request.headers.get("X-Lila-Generation", ""))
        except ValueError:
            raise AuthError("STALE_WORKER") from None
        if workers is None or not authorization.startswith("Bearer "):
            raise AuthError("STALE_WORKER")
        return workers.authenticate(authorization[7:], generation)

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        return error(exc.code, exc.status)

    @app.get("/internal/v1/checkpoints/list")
    def listing(request: Request, run_id: str, generation: int, namespace: str="", before: str|None=None,
                limit: int=Query(200, ge=1, le=200), filter: str|None=None, checkpoint_id: str|None=None):
        worker = authenticate(request)
        try:
            metadata_filter = codec.loads(filter, 65536) if filter is not None else None
        except ValueError:
            raise DomainError("INVALID_REQUEST", 422) from None
        return store.list(worker, run_id, generation, namespace, before=before, limit=limit,
                          filter=metadata_filter, checkpoint_id=checkpoint_id)

    @app.get("/internal/v1/checkpoints")
    def get(request: Request, run_id: str, generation: int, namespace: str="", checkpoint_id: str|None=None):
        rows = store.list(authenticate(request), run_id, generation, namespace, checkpoint_id=checkpoint_id, limit=1)
        return rows[0] if rows else None

    @app.post("/internal/v1/checkpoints")
    async def put(request: Request):
        worker = authenticate(request)
        return store.put(worker, await request.json())

    @app.post("/internal/v1/checkpoints/writes")
    async def writes(request: Request):
        worker = authenticate(request)
        return store.put_writes(worker, await request.json())
