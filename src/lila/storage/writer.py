"""One owner thread per store; synchronous submission for FastAPI threadpool routes."""
from concurrent.futures import Future
from queue import Queue
from threading import Thread, Lock

from lila.storage.connection import open_store


class StoreWriter:
    def __init__(self, path, key, kind):
        self.queue = Queue()
        self.lock = Lock()
        self.closed = False
        ready = Future()
        def run():
            try:
                db = open_store(path, key, kind)
            except BaseException as exc:
                ready.set_exception(exc)
                return
            ready.set_result(True)
            try:
                while (item := self.queue.get()) is not None:
                    function, transaction, result = item
                    try:
                        if transaction:
                            db.execute("BEGIN IMMEDIATE")
                        value = function(db)
                        if transaction:
                            db.commit()
                        result.set_result(value)
                    except BaseException as exc:
                        db.rollback()
                        result.set_exception(exc)
            finally:
                db.close()
        self.thread = Thread(target=run, name=f"lila-{kind}-writer", daemon=True)
        self.thread.start()
        ready.result(timeout=15)

    def call(self, function, *, transaction=True):
        result = Future()
        with self.lock:
            if self.closed:
                raise RuntimeError("store closed")
            self.queue.put((function, transaction, result))
        return result.result()

    def close(self):
        with self.lock:
            if not self.closed:
                self.closed = True
                self.queue.put(None)
        self.thread.join(timeout=15)
        if self.thread.is_alive():
            raise RuntimeError("store shutdown incomplete")
