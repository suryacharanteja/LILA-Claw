"""Windows user boundary primitives. No machine-wide trust or DPAPI scope."""
import os
from pathlib import Path

import pywintypes
import win32api
import win32con
import win32crypt
import win32event
import win32security


def owner_sid():
    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        return win32security.GetTokenInformation(token, win32security.TokenUser)[0]
    finally:
        token.Close()


def owner_sid_string():
    return win32security.ConvertSidToStringSid(owner_sid())


def security_attributes():
    descriptor = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
        f"D:P(A;;GA;;;{owner_sid_string()})(A;;GA;;;SY)", 1
    )
    attributes = pywintypes.SECURITY_ATTRIBUTES()
    attributes.SECURITY_DESCRIPTOR = descriptor
    attributes.bInheritHandle = False
    return attributes


def restrict_path(path: Path):
    """Protected DACL with owner/SYSTEM, inheritable for managed directories."""
    acl = win32security.ACL()
    flags = (win32con.OBJECT_INHERIT_ACE | win32con.CONTAINER_INHERIT_ACE) if path.is_dir() else 0
    for sid in (owner_sid(), win32security.CreateWellKnownSid(win32security.WinLocalSystemSid)):
        acl.AddAccessAllowedAceEx(win32security.ACL_REVISION_DS, flags, win32con.GENERIC_ALL, sid)
    win32security.SetNamedSecurityInfo(str(path), win32security.SE_FILE_OBJECT,
        win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
        None, None, acl, None)


def private_directory(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.is_junction():
        raise ValueError("managed directory must not be a link")
    restrict_path(path)
    return path


def protect(value: bytes) -> bytes:
    return win32crypt.CryptProtectData(value, "LILA installation secret", None, None, None, 1)


def unprotect(value: bytes) -> bytes:
    return win32crypt.CryptUnprotectData(value, None, None, None, 1)[1]


def write_private(path: Path, data: bytes):
    private_directory(path.parent)
    temporary = path.with_name(path.name + "." + os.urandom(8).hex() + ".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        restrict_path(temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class OwnerLock:
    def __init__(self, install_id: str):
        import uuid
        self.name = f"Local\\LILAClaw-{owner_sid_string()}-{uuid.UUID(install_id)}"
        self.handle = None

    def acquire(self):
        handle = win32event.CreateMutex(security_attributes(), False, self.name)
        # Reject a second acquisition even on the same OS thread (mutexes are recursive).
        existed = win32api.GetLastError() == 183
        result = win32event.WaitForSingleObject(handle, 0) if not existed else 258
        if result not in (0, 0x80):
            handle.Close()
            return False
        self.handle = handle
        return True

    def close(self):
        if self.handle is not None:
            win32event.ReleaseMutex(self.handle)
            self.handle.Close()
            self.handle = None
