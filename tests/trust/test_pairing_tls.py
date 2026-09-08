import hashlib
import hmac
import secrets
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from lila.security.pairing import Pairing, transcript
from lila.security.sessions import AuthError
from lila.security.tls import generate, server_context, client_context, renew_leaf


def test_pairing_confirmation_atomic_consume_and_reconnect(auth):
    sessions, clock = auth
    identity = Ed25519PrivateKey.generate()
    pairing = Pairing(sessions.writer,identity,secrets.token_bytes(32),lambda:clock[0])
    pair_id, secret = pairing.create()
    server_nonce, client_nonce = pairing.challenge_pair(pair_id), secrets.token_bytes(32)
    value = transcript(b"lila-pair-v1",pair_id.encode(),server_nonce,client_nonce)
    proof = hmac.digest(secret,value,"sha256")
    signature = pairing.prove(pair_id,client_nonce,proof)
    identity.public_key().verify(signature,hashlib.sha256(value+proof).digest())
    with pytest.raises(AuthError):
        pairing.consume(pair_id,client_nonce,proof)
    pairing.confirm(pair_id)
    def consume():
        try:
            return pairing.consume(pair_id,client_nonce,proof)
        except AuthError:
            return None
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _:consume(),range(2)))
    credentials = [x for x in results if x]
    assert len(credentials) == 1
    credential = credentials[0]
    challenge_id, nonce = pairing.challenge(credential["credential_id"])
    client_nonce = secrets.token_bytes(32)
    value = transcript(b"lila-extension-v1",credential["credential_id"].encode(),challenge_id.encode(),nonce,client_nonce)
    proof = hmac.digest(credential["secret"],value,"sha256")
    authenticated = pairing.authenticate(challenge_id,client_nonce,proof)
    identity.public_key().verify(authenticated["signature"],hashlib.sha256(value+proof).digest())
    assert pairing.validate_session(authenticated["session_secret"]) == credential["principal_id"]
    with pytest.raises(AuthError):
        pairing.authenticate(challenge_id,client_nonce,proof)
    with pytest.raises(AuthError):
        sessions.authenticate(authenticated["session_secret"])
    sessions.revoke(credential["principal_id"],1)
    with pytest.raises(AuthError):
        pairing.validate_session(authenticated["session_secret"])


def test_pairing_attempt_limit_and_expiry(auth):
    sessions, clock = auth
    pairing = Pairing(sessions.writer,Ed25519PrivateKey.generate(),secrets.token_bytes(32),lambda:clock[0])
    pair_id, _ = pairing.create()
    for _ in range(5):
        pairing.challenge_pair(pair_id)
        with pytest.raises(AuthError):
            pairing.prove(pair_id,secrets.token_bytes(32),secrets.token_bytes(32))
    with pytest.raises(AuthError):
        pairing.challenge_pair(pair_id)
    pair_id,_ = pairing.create()
    clock[0] += 300
    with pytest.raises(AuthError):
        pairing.challenge_pair(pair_id)


def handshake(server, client):
    listener = socket.socket()
    listener.bind(("127.0.0.1",0))
    listener.listen()
    listener.settimeout(5)
    def accept():
        try:
            connection,_ = listener.accept()
            with server.wrap_socket(connection,server_side=True) as secure:
                value = secure.recv(1)
                secure.sendall(b"y")
                return value
        except (ssl.SSLError, ConnectionAbortedError, ConnectionResetError):
            return None
        finally:
            listener.close()
    with ThreadPoolExecutor(1) as pool:
        result = pool.submit(accept)
        try:
            with socket.create_connection(listener.getsockname(),timeout=5) as connection:
                with client.wrap_socket(connection,server_hostname="127.0.0.1") as secure:
                    secure.sendall(b"x")
                    assert secure.recv(1) == b"y"
        finally:
            result.result(timeout=6)


def test_tls_constraints_verified_handshake_and_impostor(tmp_path):
    directory = tmp_path/"tls"
    generate(directory,str(uuid4()))
    ca = x509.load_pem_x509_certificate((directory/"ca.pem").read_bytes())
    constraints = ca.extensions.get_extension_for_class(x509.NameConstraints)
    assert constraints.critical
    assert len(constraints.value.permitted_subtrees) == 3
    assert ca.extensions.get_extension_for_class(x509.BasicConstraints).value.path_length == 0
    context = server_context(directory)
    assert not list(directory.glob("*.tmp"))
    handshake(context,client_context(directory))
    other = tmp_path/"other"
    generate(other,str(uuid4()))
    with pytest.raises(ssl.SSLError):
        handshake(context,client_context(other))
    assert not renew_leaf(directory)
    from datetime import datetime,timedelta,timezone
    from cryptography.hazmat.primitives import serialization
    from lila.security.windows import unprotect,write_private
    from lila.security.tls import issue_leaf
    ca_key = serialization.load_pem_private_key(unprotect((directory/"ca.key.dpapi").read_bytes()),None)
    leaf_key = serialization.load_pem_private_key(unprotect((directory/"leaf.key.dpapi").read_bytes()),None)
    expiring = issue_leaf(ca,ca_key,leaf_key,datetime.now(timezone.utc)-timedelta(days=80))
    write_private(directory/"leaf.pem",expiring.public_bytes(serialization.Encoding.PEM))
    assert renew_leaf(directory)
    renewed = x509.load_pem_x509_certificate((directory/"leaf.pem").read_bytes())
    assert renewed.not_valid_after_utc > expiring.not_valid_after_utc
    assert renewed.public_key().public_numbers() == expiring.public_key().public_numbers()
    with pytest.raises(ValueError):
        generate(directory,str(uuid4()))
