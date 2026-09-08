import secrets
import pytest
from lila.storage.writer import StoreWriter
from lila.security.sessions import Sessions


@pytest.fixture
def auth(tmp_path):
    writer = StoreWriter(tmp_path / "auth.db", secrets.token_bytes(32), "auth")
    clock = [1800000000.0]
    sessions = Sessions(writer, secrets.token_bytes(32), lambda:clock[0])
    yield sessions, clock
    writer.close()
