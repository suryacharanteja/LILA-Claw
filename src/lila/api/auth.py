import json
from uuid import UUID, uuid4
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from lila.security.sessions import AuthError

COOKIE = "__Host-lila-session"
CSP = "default-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; connect-src 'self'"


class BootstrapBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class RenewBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: UUID


class RevokeBody(RenewBody):
    principal_id: UUID
    expected_revision: int = Field(ge=1,strict=True)


def error(code, status=401):
    return JSONResponse({"code": code, "message": code.replace("_", " ").lower(),
        "retryable": False, "correlation_id": str(uuid4())}, status_code=status)


class Boundary:
    """Bound bodies before JSON parsing; no CORS or plaintext/Host fallback."""
    def __init__(self, app, host):
        self.app, self.host = app, host

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = scope.get("headers", [])
        hosts = [v.decode() for k,v in headers if k == b"host"]
        if hosts != [self.host] or scope["scheme"] != "https":
            await error("HOST_DENIED", 403)(scope, receive, send)
            return
        header = {k.decode():v.decode() for k,v in headers}
        origin = header.get("origin")
        expected = "https://" + self.host
        if (origin and origin != expected) or header.get("sec-fetch-site") in {"cross-site", "same-site"}:
            await error("ORIGIN_DENIED", 403)(scope, receive, send)
            return
        internal = scope["path"].startswith("/internal/")
        if scope["method"] not in {"GET", "HEAD"} and origin != expected and not internal:
            await error("ORIGIN_DENIED", 403)(scope, receive, send)
            return
        async def secure_send(message):
            if message['type']=='http.response.start':
                message['headers'] += [(b'cache-control',b'no-store'),(b'content-security-policy',CSP.encode()),(b'referrer-policy',b'no-referrer'),(b'x-content-type-options',b'nosniff')]
            await send(message)
        if scope['method']=='POST' and scope['path']=='/api/v1/documents/uploads':
            # This route authenticates before consuming its bounded multipart stream.
            await self.app(scope,receive,secure_send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > 1024*1024:
                await error("PAYLOAD_TOO_LARGE", 413)(scope, receive, send)
                return
            if not message.get("more_body"):
                break
        if body:
            def unique(pairs):
                result = {}
                for key,value in pairs:
                    if key in result:
                        raise ValueError("duplicate key")
                    result[key] = value
                return result
            try:
                json.loads(body, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            except (ValueError, UnicodeError):
                await error("INVALID_REQUEST", 400)(scope, receive, send)
                return
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type":"http.request", "body":bytes(body), "more_body":False}
            return await receive()
        await self.app(scope, replay, secure_send)


def create_app(sessions, port, health=lambda: {"state":"STARTING", "blockers":["DOMAIN_NOT_IMPLEMENTED"]}, workers=None):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(Boundary, host=f"127.0.0.1:{port}")

    @app.exception_handler(AuthError)
    async def auth_error(request, exc):
        status = 409 if str(exc) in {"REVISION_CONFLICT","COMMAND_ID_REUSED"} else 403 if str(exc) in {"CSRF_DENIED","STALE_WORKER"} else 401
        return error(str(exc), status)

    def response(data):
        public = {k:v for k,v in data.items() if k not in {"secret", "session_id"}}
        result = JSONResponse(public)
        result.set_cookie(COOKIE, data["secret"], max_age=86400, path="/", secure=True, httponly=True, samesite="strict")
        return result

    @app.post("/api/v1/auth/bootstrap")
    def bootstrap(body: BootstrapBody):
        return response(sessions.consume_bootstrap(body.token))

    @app.get("/api/v1/auth/session")
    def session(request: Request):
        return sessions.session(request.cookies.get(COOKIE, ""))

    @app.post("/api/v1/auth/renew")
    def renew(body: RenewBody, request: Request):
        return response(sessions.renew(request.cookies.get(COOKIE, ""), request.headers.get("X-Lila-CSRF", "")))

    @app.post("/api/v1/auth/revoke")
    def revoke(body: RevokeBody, request: Request):
        return sessions.revoke_command(request.cookies.get(COOKIE,""),request.headers.get("X-Lila-CSRF",""),str(body.command_id),str(body.principal_id),body.expected_revision)

    @app.get("/api/v1/health")
    def get_health(request: Request):
        if request.cookies.get(COOKIE):
            sessions.authenticate(request.cookies[COOKIE])
            return health()
        return {"live": True}

    @app.post("/internal/v1/health")
    def worker_health(request: Request):
        authorization = request.headers.get("Authorization", "")
        try:
            generation = int(request.headers.get("X-Lila-Generation", ""))
        except ValueError:
            raise AuthError("STALE_WORKER")
        if workers is None or not authorization.startswith("Bearer "):
            raise AuthError("STALE_WORKER")
        workers.authenticate(authorization[7:],generation)
        return {"live": True}

    return app
