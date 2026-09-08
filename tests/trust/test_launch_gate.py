import pytest
from lila.runtime.launcher import open_authenticated


def test_automatic_bootstrap_launch_requires_resolved_decision(monkeypatch):
    import webbrowser
    calls = []
    monkeypatch.setattr(webbrowser,"open",lambda url:calls.append(url))
    with pytest.raises(PermissionError):
        open_authenticated({"install_id":"unused"})
    assert not calls


def test_approved_bootstrap_launch_uses_only_pipe_capability(monkeypatch):
    from lila.runtime import launcher
    calls = []
    url = "https://127.0.0.1:43127/#bootstrap=synthetic-test-capability"
    monkeypatch.setattr(launcher,"request",lambda identity,operation:{"url":url})
    monkeypatch.setattr(launcher.webbrowser,"open",lambda value:calls.append(value))
    launcher.open_authenticated({"install_id":"fixture","allow_fragment_launch":True})
    assert calls == [url]
