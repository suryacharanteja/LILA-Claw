"""M1 worker liveness only; LangGraph execution is added in M3."""
import hashlib
import http.client
import json
import msvcrt
import os
import ssl
import sys
import time
from cryptography import x509
from cryptography.hazmat.primitives import serialization


def main():
    descriptor = msvcrt.open_osfhandle(int(sys.argv[1]),os.O_RDONLY)
    with os.fdopen(descriptor,"rb") as pipe:
        data = pipe.read(8193)
    if len(data)>8192:
        raise ValueError("boot frame too large")
    boot = json.loads(data)
    context = ssl.create_default_context(cafile=boot["ca_path"])
    while True:
        connection = http.client.HTTPSConnection("127.0.0.1",boot["port"],context=context,timeout=2)
        try:
            connection.connect()
            certificate = x509.load_der_x509_certificate(connection.sock.getpeercert(binary_form=True))
            spki = certificate.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
            if hashlib.sha256(spki).hexdigest() != boot["server_spki_pin"]:
                return
            connection.request("POST","/internal/v1/health",body=b"{}",headers={"Authorization":"Bearer "+boot["token"],"X-Lila-Generation":str(boot["generation"]),"Content-Type":"application/json"})
            response = connection.getresponse()
            response.read()
            if response.status != 200:
                return
        except (OSError,ssl.SSLError,http.client.HTTPException):
            return
        finally:
            connection.close()
        time.sleep(2)


if __name__ == "__main__":
    main()
