"""Bounded, local-only Windows control pipe with peer SID verification."""
import json
import time
from threading import Event, Thread
from uuid import UUID
import pywintypes
import win32api
import win32con
import win32event
import win32file
import win32pipe
import win32security
from lila.security.windows import owner_sid_string, security_attributes

MAX_FRAME = 8192


def pipe_name(install_id):
    return rf"\\.\pipe\LILAClaw-{owner_sid_string()}-{UUID(install_id)}"


def verify_process(pid):
    process = win32api.OpenProcess(0x1000, False, pid)
    try:
        token = win32security.OpenProcessToken(process, win32con.TOKEN_QUERY)
        try:
            sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
            if win32security.ConvertSidToStringSid(sid) != owner_sid_string():
                raise PermissionError("wrong control peer")
        finally:
            token.Close()
    finally:
        process.Close()


def overlapped():
    operation = pywintypes.OVERLAPPED()
    operation.hEvent = win32event.CreateEvent(None, True, False, None)
    return operation


def finish(handle, operation, timeout=2000):
    if win32event.WaitForSingleObject(operation.hEvent, timeout) != win32event.WAIT_OBJECT_0:
        win32file.CancelIo(handle)
        win32event.WaitForSingleObject(operation.hEvent, 2000)
        raise TimeoutError("control pipe timeout")
    return win32file.GetOverlappedResult(handle, operation, False)


def read_frame(handle):
    operation = overlapped()
    try:
        buffer = win32file.AllocateReadBuffer(MAX_FRAME)
        status, _ = win32file.ReadFile(handle, buffer, operation)
        count = finish(handle, operation) if status == 997 else win32file.GetOverlappedResult(handle, operation, True)
        return json.loads(bytes(buffer[:count]))
    finally:
        operation.hEvent.Close()


def write_frame(handle, value):
    data = json.dumps(value).encode()
    if len(data) > MAX_FRAME:
        raise ValueError("control frame too large")
    operation = overlapped()
    try:
        status, _ = win32file.WriteFile(handle, data, operation)
        if status == 997:
            finish(handle, operation)
    finally:
        operation.hEvent.Close()


class ControlPipe:
    def __init__(self, install_id, handler):
        self.name, self.handler = pipe_name(install_id), handler
        self.stop = Event()
        self.ready = Event()
        self.error = None
        self.thread = Thread(target=self._serve, daemon=True, name="lila-control-pipe")

    def start(self):
        self.thread.start()
        if not self.ready.wait(5):
            raise RuntimeError("control pipe startup timeout")
        if self.error:
            raise self.error

    def _serve(self):
        first = True
        while not self.stop.is_set():
            handle = None
            operation = None
            try:
                handle = win32pipe.CreateNamedPipe(self.name,
                    win32pipe.PIPE_ACCESS_DUPLEX | win32file.FILE_FLAG_OVERLAPPED | (0x00080000 if first else 0),
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT | win32pipe.PIPE_REJECT_REMOTE_CLIENTS,
                    1, MAX_FRAME, MAX_FRAME, 2000, security_attributes())
                first = False
                self.ready.set()
                operation = overlapped()
                try:
                    status = win32pipe.ConnectNamedPipe(handle, operation)
                    if status in (0,535):
                        win32event.SetEvent(operation.hEvent)
                except pywintypes.error as exc:
                    if exc.winerror != 535:
                        raise
                    win32event.SetEvent(operation.hEvent)
                while win32event.WaitForSingleObject(operation.hEvent, 100) != 0:
                    if self.stop.is_set():
                        win32file.CancelIo(handle)
                        win32event.WaitForSingleObject(operation.hEvent,2000)
                        return
                verify_process(win32pipe.GetNamedPipeClientProcessId(handle))
                request = read_frame(handle)
                if not isinstance(request, dict) or set(request) != {"operation"} or request["operation"] not in {"launch", "status", "quit", "worker_boot", "worker_fence"}:
                    write_frame(handle, {"error":"INVALID_REQUEST"})
                else:
                    write_frame(handle, self.handler(request["operation"]))
                read_frame(handle)  # Bounded client acknowledgement before closing the pipe.
            except Exception as exc:
                if not self.ready.is_set():
                    self.error = exc
                    self.ready.set()
                    return
                # No request/secret or exception repr is logged.
            finally:
                if operation:
                    operation.hEvent.Close()
                if handle:
                    handle.Close()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise RuntimeError("control pipe shutdown timeout")


def request(install_id, operation):
    name = pipe_name(install_id)
    deadline = time.monotonic()+2
    while True:
        try:
            win32pipe.WaitNamedPipe(name, 2000)
            handle = win32file.CreateFile(name, win32con.GENERIC_READ | win32con.GENERIC_WRITE, 0, None,
                win32con.OPEN_EXISTING, win32file.FILE_FLAG_OVERLAPPED | 0x00100000, None)
            break
        except pywintypes.error as exc:
            # Only retry before sending: absence/busy while the preceding client disconnects.
            if exc.winerror not in (2,231) or time.monotonic()>=deadline:
                raise
            time.sleep(0.02)
    try:
        verify_process(win32pipe.GetNamedPipeServerProcessId(handle))
        win32pipe.SetNamedPipeHandleState(handle, win32pipe.PIPE_READMODE_MESSAGE, None, None)
        write_frame(handle, {"operation":operation})
        result = read_frame(handle)
        write_frame(handle, {"received":True})
        return result
    finally:
        handle.Close()
