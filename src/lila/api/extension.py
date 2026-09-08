"""M1 authenticated WSS boundary. Execution/control dispatch is added in M2/M4."""
import asyncio
import base64
import json
import re
from uuid import UUID
from fastapi import Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict
from cryptography.hazmat.primitives import serialization
from lila.api.auth import COOKIE
from lila.security.sessions import AuthError


def encode(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def decode(value):
    if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}",value):
        raise AuthError("AUTH_REQUIRED")
    return base64.urlsafe_b64decode(value+"=")


class Confirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pairing_id: UUID


def attach_extension(app, sessions, pairing, port, install_id, extension_id):
    if extension_id is not None and not re.fullmatch(r"[a-p]{32}",extension_id):
        raise ValueError("invalid explicitly configured extension ID")
    active = {}

    def revoke(principal):
        for identity, sockets in list(active.items()):
            if principal is None or principal == identity:
                for websocket, loop in list(sockets):
                    asyncio.run_coroutine_threadsafe(websocket.close(code=4401),loop)
    sessions.revocation_listeners.append(revoke)

    def owner(request):
        return sessions.authenticate(request.cookies.get(COOKIE,""), request.headers.get("X-Lila-CSRF",""))

    @app.post("/api/v1/auth/pairing")
    def create_pair(request: Request):
        owner(request)
        if extension_id is None:
            raise AuthError("EXTENSION_NOT_CONFIGURED")
        pair_id, secret = pairing.create()
        public = pairing.identity.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        return {"version":1,"install_id":install_id,"port":port,"pairing_id":pair_id,"server_public_key":encode(public),"secret":encode(secret)}

    @app.post("/api/v1/auth/pairing/confirm")
    def confirm_pair(body: Confirm, request: Request):
        owner(request)
        pairing.confirm(str(body.pairing_id))
        return {"state":"OWNER_CONFIRMED"}

    async def receive(websocket):
        raw = await asyncio.wait_for(websocket.receive_text(),timeout=60)
        if len(raw.encode())>1024*1024:
            raise AuthError("FRAME_TOO_LARGE")
        def unique(pairs):
            result = {}
            for key,value in pairs:
                if key in result:
                    raise ValueError("duplicate frame key")
                result[key] = value
            return result
        frame = json.loads(raw,object_pairs_hook=unique)
        if not isinstance(frame,dict) or set(frame) != {"type","payload"} or not isinstance(frame["payload"],dict):
            raise AuthError("INVALID_FRAME")
        return frame

    @app.websocket("/extension/v1")
    async def extension(websocket: WebSocket):
        expected = f"chrome-extension://{extension_id}"
        if extension_id is None or websocket.headers.get("origin") != expected or websocket.headers.get("host") != f"127.0.0.1:{port}" or websocket.scope["scheme"] != "wss" or websocket.url.query:
            await websocket.close(code=4403)
            return
        await websocket.accept()
        principal = None
        member = None
        try:
            first = await receive(websocket)
            if first["type"] == "pair":
                pair_id = str(UUID(first["payload"]["pairing_id"]))
                nonce = pairing.challenge_pair(pair_id)
                await websocket.send_json({"type":"pair_challenge","payload":{"nonce":encode(nonce)}})
                proof_frame = await receive(websocket)
                if proof_frame["type"] != "pair_proof":
                    raise AuthError("INVALID_FRAME")
                nonce = decode(proof_frame["payload"]["client_nonce"])
                proof = decode(proof_frame["payload"]["proof"])
                signature = pairing.prove(pair_id,nonce,proof)
                await websocket.send_json({"type":"owner_confirmation_required","payload":{"signature":encode(signature)}})
                frame = await receive(websocket)
                if frame["type"] != "consume_pairing":
                    raise AuthError("INVALID_FRAME")
                credentials = pairing.consume(pair_id,nonce,proof)
                credentials["secret"] = encode(credentials["secret"])
                await websocket.send_json({"type":"credential","payload":credentials})
                first = await receive(websocket)
            if first["type"] != "authenticate":
                raise AuthError("AUTH_REQUIRED")
            credential_id = str(UUID(first["payload"]["credential_id"]))
            while True:
                challenge_id, nonce = pairing.challenge(credential_id)
                await websocket.send_json({"type":"challenge","payload":{"challenge_id":challenge_id,"nonce":encode(nonce)}})
                frame = await receive(websocket)
                if frame["type"] != "proof":
                    raise AuthError("AUTH_REQUIRED")
                authenticated = pairing.authenticate(challenge_id,decode(frame["payload"]["client_nonce"]),decode(frame["payload"]["proof"]))
                principal = authenticated["principal_id"]
                if member is None:
                    member = (websocket,asyncio.get_running_loop())
                    active.setdefault(principal,set()).add(member)
                secret = authenticated.pop("session_secret")
                authenticated["signature"] = encode(authenticated["signature"])
                await websocket.send_json({"type":"authenticated","payload":authenticated})
                while True:
                    pairing.validate_session(secret)
                    try:
                        frame = await asyncio.wait_for(receive(websocket),timeout=5)
                    except asyncio.TimeoutError:
                        await websocket.send_json({"type":"heartbeat","payload":{}})
                        continue
                    pairing.validate_session(secret)
                    if frame["type"] == "renew":
                        break
                    if frame["type"] != "status":
                        raise AuthError("SCOPE_DENIED")
                    await websocket.send_json({"type":"status","payload":{"execution_ready":False,"blockers":["EXECUTION_NOT_IMPLEMENTED"]}})
        except (AuthError,ValueError,KeyError,TypeError,WebSocketDisconnect,asyncio.TimeoutError):
            try:
                await websocket.close(code=4401)
            except RuntimeError:
                pass
        finally:
            if member and principal in active:
                active[principal].discard(member)
                if not active[principal]:
                    del active[principal]
