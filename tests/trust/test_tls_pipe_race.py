import time
from uuid import uuid4
import pywintypes
import win32pipe
from lila.security.tls import generate,server_context


def test_tls_key_reader_connecting_before_server_wait_is_valid(tmp_path,monkeypatch):
    directory=tmp_path/'tls'
    generate(directory,str(uuid4()))
    original=win32pipe.ConnectNamedPipe
    raced=[]
    def delayed(handle,operation):
        deadline=time.monotonic()+3
        while True:
            try:
                win32pipe.GetNamedPipeClientProcessId(handle)
                break
            except pywintypes.error:
                if time.monotonic()>=deadline:
                    raise AssertionError('TLS reader did not connect')
                time.sleep(0.001)
        try:
            result=original(handle,operation)
            raced.append(result==535)
            return result
        except pywintypes.error as exc:
            raced.append(exc.winerror==535)
            raise
    monkeypatch.setattr(win32pipe,'ConnectNamedPipe',delayed)
    assert server_context(directory)
    assert raced==[True]
    assert not list(directory.glob('*.key'))
