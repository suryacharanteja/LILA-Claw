import secrets
from uuid import uuid4
import pytest
import win32security
from lila.runtime.installation import prepare,load,confirm_trust
from lila.security.windows import owner_sid_string
from lila.security.sessions import AuthError


def test_control_pipe_rejects_other_sid(monkeypatch):
    import os
    from lila.runtime import control_pipe
    monkeypatch.setattr(control_pipe,"owner_sid_string",lambda:"S-1-5-21-999-999-999-1000")
    with pytest.raises(PermissionError):
        control_pipe.verify_process(os.getpid())


def test_revocation_idempotency_and_conflicting_command(auth):
    sessions,_ = auth
    actor = sessions.consume_bootstrap(sessions.issue_bootstrap())
    target = sessions.consume_bootstrap(sessions.issue_bootstrap())
    command = str(uuid4())
    args = (actor["secret"],actor["csrf_token"],command,target["principal_id"],1)
    first = sessions.revoke_command(*args)
    assert first["state"] == "REVOKED"
    assert sessions.revoke_command(*args) == first
    with pytest.raises(AuthError,match="COMMAND_ID_REUSED"):
        sessions.revoke_command(actor["secret"],actor["csrf_token"],command,actor["principal_id"],1)
    sessions.authenticate(actor["secret"])


def test_installation_dpapi_separation_acl_and_explicit_trust(tmp_path):
    root = tmp_path/"install"
    prepare(root)
    _,keys = load(root)
    assert len(set(keys.values())) == len(keys)
    protected = (root/"keys.dpapi").read_bytes()
    for key in keys.values():
        assert key not in protected and key.hex().encode() not in protected
    descriptor = win32security.GetNamedSecurityInfo(str(root),win32security.SE_FILE_OBJECT,win32security.DACL_SECURITY_INFORMATION)
    acl = descriptor.GetSecurityDescriptorDacl()
    # Windows may split generic inheritable ACEs into effective and inherit-only ACEs.
    sids = {win32security.ConvertSidToStringSid(acl.GetAce(index)[2]) for index in range(acl.GetAceCount())}
    assert sids == {owner_sid_string(),"S-1-5-18"}
    with pytest.raises(PermissionError):
        confirm_trust(root)
    with pytest.raises(ValueError):
        prepare(root)
