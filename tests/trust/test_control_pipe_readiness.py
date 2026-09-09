import pytest
import pywintypes
from lila.runtime import control_pipe


@pytest.mark.parametrize('code',[2,231])
def test_pipe_readiness_timeout_is_catchable_by_supervisor(monkeypatch,code):
    clock=iter([0,3])
    monkeypatch.setattr(control_pipe.time,'monotonic',lambda:next(clock))
    def unavailable(*args):
        raise pywintypes.error(code,'WaitNamedPipe','fixture')
    monkeypatch.setattr(control_pipe.win32pipe,'WaitNamedPipe',unavailable)
    with pytest.raises(TimeoutError,match='control pipe not ready'):
        control_pipe.request('00000000-0000-4000-8000-000000000001','status')


def test_pipe_permission_failure_is_not_treated_as_readiness(monkeypatch):
    def denied(*args):
        raise pywintypes.error(5,'WaitNamedPipe','fixture')
    monkeypatch.setattr(control_pipe.win32pipe,'WaitNamedPipe',denied)
    with pytest.raises(pywintypes.error) as error:
        control_pipe.request('00000000-0000-4000-8000-000000000001','status')
    assert error.value.winerror==5
