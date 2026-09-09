import hmac
import secrets
from uuid import uuid4
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from lila.api.auth import create_app
from lila.api.extension import attach_extension, encode, decode,capability_report
from lila.security.pairing import Pairing, transcript


def test_websocket_origin_authentication_renewal_and_revocation(auth):
    sessions,clock = auth
    pairing = Pairing(sessions.writer,Ed25519PrivateKey.generate(),secrets.token_bytes(32),lambda:clock[0])
    app = create_app(sessions,43127)
    extension_id = "a"*32
    attach_extension(app,sessions,pairing,43127,str(uuid4()),extension_id)
    pair_id,secret = pairing.create()
    nonce = pairing.challenge_pair(pair_id)
    client_nonce = secrets.token_bytes(32)
    proof = hmac.digest(secret,transcript(b"lila-pair-v1",pair_id.encode(),nonce,client_nonce),"sha256")
    pairing.prove(pair_id,client_nonce,proof)
    pairing.confirm(pair_id)
    credential = pairing.consume(pair_id,client_nonce,proof)
    url = "wss://127.0.0.1:43127/extension/v1"
    with TestClient(app,base_url="https://127.0.0.1:43127") as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(url,headers={"Origin":"https://evil.invalid"}):
                pass
        with client.websocket_connect(url,headers={'Origin':'chrome-extension://'+extension_id}) as unauthenticated:
            unauthenticated.send_json({'type':'capabilities','payload':{'protocol_version':1,'tools':['inspect_context'],'adapter_ids':['fixture-v1']}})
            with pytest.raises(WebSocketDisconnect):
                unauthenticated.receive_json()
        with client.websocket_connect(url,headers={"Origin":"chrome-extension://"+extension_id}) as ws:
            ws.send_json({"type":"authenticate","payload":{"credential_id":credential["credential_id"]}})
            def authenticate():
                challenge = ws.receive_json()["payload"]
                cn = secrets.token_bytes(32)
                value = transcript(b"lila-extension-v1",credential["credential_id"].encode(),challenge["challenge_id"].encode(),decode(challenge["nonce"]),cn)
                ws.send_json({"type":"proof","payload":{"client_nonce":encode(cn),"proof":encode(hmac.digest(credential["secret"],value,"sha256"))}})
                assert ws.receive_json()["type"] == "authenticated"
            authenticate()
            ws.send_json({"type":"status","payload":{}})
            assert not ws.receive_json()["payload"]["execution_ready"]
            ws.send_json({'type':'capabilities','payload':{'protocol_version':1,'tools':['inspect_context'],'adapter_ids':['fixture-v1']}})
            assert ws.receive_json()=={'type':'capabilities_received','payload':{'accepted':True,'execution_ready':False}}
            ws.send_json({'type':'status','payload':{}})
            assert ws.receive_json()['payload']['capabilities_reported'] is True
            ws.send_json({"type":"renew","payload":{}})
            authenticate()
            ws.send_json({'type':'status','payload':{}})
            assert ws.receive_json()['payload']['capabilities_reported'] is False
            sessions.revoke(credential["principal_id"],1)
            with pytest.raises(WebSocketDisconnect):
                ws.receive_json()


@pytest.mark.parametrize('change',[
    {'protocol_version':True},{'protocol_version':2},{'tools':['Runtime.evaluate']},
    {'tools':['inspect_context','inspect_context']},{'adapter_ids':['fixture','fixture']},
    {'adapter_ids':['https://remote.example/code.js']},{'adapter_ids':['x'*101]},
    {'execution_ready':True},{'adapter_ids':['fixture']*33},
])
def test_capability_report_rejects_invalid_or_authority_fields(change):
    payload={'protocol_version':1,'tools':['inspect_context'],'adapter_ids':['fixture']}
    with pytest.raises(ValueError):
        capability_report(dict(payload,**change))
