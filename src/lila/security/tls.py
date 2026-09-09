"""Installation CA/leaf creation and verified TLS contexts. Trust is opt-in."""
import ipaddress
import ssl
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from lila.security.windows import protect, unprotect, write_private


def generate(directory: Path, install_id: str):
    identity = str(UUID(install_id))
    if (directory / "ca.pem").exists():
        raise ValueError("refusing to replace installation identity")
    clock = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"LILA local {identity}")])
    ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(clock-timedelta(minutes=5)).not_valid_after(clock+timedelta(days=1825))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), True)
        .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), True)
        .add_extension(x509.NameConstraints([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_network("127.0.0.1/32")), x509.IPAddress(ipaddress.ip_network("::1/128"))], None), True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), False)
        .sign(ca_key, hashes.SHA256()))
    leaf = issue_leaf(ca, ca_key, leaf_key, clock)
    for stem, key, certificate in (("ca", ca_key, ca), ("leaf", leaf_key, leaf)):
        write_private(directory / f"{stem}.pem", certificate.public_bytes(serialization.Encoding.PEM))
        write_private(directory / f"{stem}.key.dpapi", protect(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())))
    return ca.fingerprint(hashes.SHA1()).hex().upper()


def issue_leaf(ca, ca_key, leaf_key, clock):
    return (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .issuer_name(ca.subject).public_key(leaf_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(clock-timedelta(minutes=5)).not_valid_after(clock+timedelta(days=90))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
        .add_extension(x509.KeyUsage(True, False, True, False, False, False, False, False, False), True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), False)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1")), x509.IPAddress(ipaddress.ip_address("::1"))]), False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), False)
        .sign(ca_key, hashes.SHA256()))


def renew_leaf(directory: Path):
    current = x509.load_pem_x509_certificate((directory / "leaf.pem").read_bytes())
    clock = datetime.now(timezone.utc)
    if current.not_valid_after_utc > clock + timedelta(days=30):
        return False
    ca = x509.load_pem_x509_certificate((directory / "ca.pem").read_bytes())
    if ca.not_valid_after_utc <= clock + timedelta(days=90):
        raise RuntimeError("new CA setup confirmation required")
    ca_key = serialization.load_pem_private_key(unprotect((directory / "ca.key.dpapi").read_bytes()), None)
    leaf_key = serialization.load_pem_private_key(unprotect((directory / "leaf.key.dpapi").read_bytes()), None)
    leaf = issue_leaf(ca, ca_key, leaf_key, clock)
    write_private(directory / "leaf.pem", leaf.public_bytes(serialization.Encoding.PEM))
    return True


def server_context(directory: Path):
    # OpenSSL accepts a Windows pipe path: private key bytes never touch a disk file,
    # including if this process is killed during context construction.
    from contextlib import contextmanager
    from threading import Event, Thread
    from uuid import uuid4
    import win32pipe
    import win32file
    import win32event
    import pywintypes
    from lila.security.windows import security_attributes
    from lila.runtime.control_pipe import overlapped, finish
    name = rf"\\.\pipe\LILAKey-{uuid4()}"
    handle = win32pipe.CreateNamedPipe(name,win32pipe.PIPE_ACCESS_OUTBOUND | win32file.FILE_FLAG_OVERLAPPED | 0x00080000,
        win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_WAIT | win32pipe.PIPE_REJECT_REMOTE_CLIENTS,
        1,8192,8192,2000,security_attributes())
    done = Event()
    errors = []
    progress = {'stage':'waiting','bytes_written':0}
    def supply():
        operation = overlapped()
        key_bytes = None
        try:
            try:
                status = win32pipe.ConnectNamedPipe(handle,operation)
            except pywintypes.error as exc:
                if exc.winerror != 535:  # ERROR_PIPE_CONNECTED: reader won the race.
                    raise
                status = 535
            if status == 997:
                finish(handle,operation,5000)
            elif status not in (0,535,None):
                raise RuntimeError('TLS key pipe connection failed')
            progress['stage']='connected'
            operation.hEvent.Close()
            operation = overlapped()
            # An overlapped write may still reference the supplied buffer after
            # WriteFile returns. Keep it alive through completion and reader close.
            key_bytes = unprotect((directory/"leaf.key.dpapi").read_bytes())
            status,_ = win32file.WriteFile(handle,key_bytes,operation)
            if status == 997:
                progress['bytes_written']=finish(handle,operation,5000)
            else:
                progress['bytes_written']=win32file.GetOverlappedResult(handle,operation,True)
            progress['stage']='written'
            done.wait(10)
        except BaseException as exc:
            errors.append((type(exc).__name__,getattr(exc,'winerror',None)))
        finally:
            operation.hEvent.Close()
            handle.Close()
            key_bytes = None
    thread = Thread(target=supply,daemon=True,name="lila-tls-key")
    thread.start()
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        try:
            context.load_cert_chain(str(directory / "leaf.pem"), name)
        except ssl.SSLError:
            raise RuntimeError(f"TLS key channel failed: {progress}, errors={errors}") from None
        if errors:
            raise RuntimeError("TLS private-key load failed")
        return context
    finally:
        done.set()
        thread.join(timeout=6)
        if thread.is_alive():
            raise RuntimeError("TLS key channel shutdown incomplete")


def client_context(directory: Path):
    return ssl.create_default_context(cafile=str(directory / "ca.pem"))
