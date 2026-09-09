"""Verify the installation CA and leaf SPKI before sending worker credentials."""
import hashlib
import ssl
import httpx
from cryptography import x509
from cryptography.hazmat.primitives import serialization


def verify_pin(stream, expected):
    ssl_object=stream.get_extra_info('ssl_object')
    if ssl_object is None:
        raise ssl.SSLError('worker TLS missing')
    certificate=x509.load_der_x509_certificate(ssl_object.getpeercert(binary_form=True))
    spki=certificate.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
    if hashlib.sha256(spki).hexdigest()!=expected:
        raise ssl.SSLError('worker TLS identity mismatch')


class PinnedAsyncTransport(httpx.AsyncHTTPTransport):
    def __init__(self,boot):
        self.origin=f"https://127.0.0.1:{boot['port']}"
        self.pin=boot['server_spki_pin']
        super().__init__(verify=ssl.create_default_context(cafile=boot['ca_path']),retries=0,
                         limits=httpx.Limits(max_keepalive_connections=0,max_connections=4))

    async def handle_async_request(self,request):
        if str(request.url).split('/',3)[:3]!=self.origin.split('/'):
            raise ValueError('worker origin denied')
        checked=False
        async def trace(name,info):
            nonlocal checked
            if name=='connection.start_tls.complete':
                verify_pin(info['return_value'],self.pin)
                checked=True
            if name.endswith('send_request_headers.started') and not checked:
                raise ssl.SSLError('worker peer not verified')
        request.extensions['trace']=trace
        return await super().handle_async_request(request)


def async_client(boot):
    return httpx.AsyncClient(base_url=f"https://127.0.0.1:{boot['port']}",transport=PinnedAsyncTransport(boot),
        follow_redirects=False,trust_env=False,timeout=httpx.Timeout(10,connect=2),
        headers={'Authorization':'Bearer '+boot['token'],'X-Lila-Generation':str(boot['generation'])})
