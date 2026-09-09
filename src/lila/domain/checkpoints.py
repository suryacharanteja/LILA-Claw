"""Coordinator-owned persistence for generation-scoped worker checkpoints."""
from langgraph.checkpoint.base import WRITES_IDX_MAP
from lila.contracts import checkpoint_json as codec
from lila.contracts.canonical import canonical
from lila.domain.core import DomainError, identifier, validate


class Checkpoints:
    def __init__(self, domain):
        self.domain = domain

    def _scope(self, db, worker, run, generation):
        row = db.execute("SELECT id FROM leases WHERE run_id=? AND worker_id=? AND generation=? AND fenced=0",
                         (identifier(run), identifier(worker), generation)).fetchone()
        if not row:
            raise DomainError("STALE_LEASE", 403)
        # Saving state is allowed while paused, but never under an expired/fenced lease.
        self.domain._lease(db, row[0], worker, generation, run, require_live=False)

    def _command(self, worker, body, kind, change):
        with self.domain.dispatch_lock:
            self.domain.writer.call(lambda db: self._scope(db, worker, body["run_id"], body["generation"]), transaction=False)
            return self.domain.command(worker, body["command_id"], [kind, body], change)

    def _json(self, value, limit=1024*1024):
        try:
            return codec.dumps(codec.loads(value, limit), limit)
        except (ValueError, TypeError, RecursionError):
            raise DomainError("INVALID_CHECKPOINT", 422) from None

    def put(self, worker, body):
        body = validate("CheckpointPut", body)
        for key, limit in (("checkpoint_json", 1048576), ("metadata_json", 65536), ("new_versions_json", 65536)):
            body[key] = self._json(body[key], limit)
        checkpoint = codec.loads(body["checkpoint_json"])
        if not isinstance(checkpoint, dict) or checkpoint.get("id") != body["checkpoint_id"]:
            raise DomainError("INVALID_CHECKPOINT", 422)
        if not all(isinstance(codec.loads(body[key]), dict) for key in ("metadata_json", "new_versions_json")):
            raise DomainError("INVALID_CHECKPOINT", 422)
        def change(db):
            self._scope(db, worker, body["run_id"], body["generation"])
            key = (body["run_id"], body["namespace"], body["checkpoint_id"])
            payload = tuple(body[k] for k in ("parent_id", "checkpoint_json", "metadata_json", "new_versions_json"))
            old = db.execute("SELECT parent_id,checkpoint_json,metadata_json,new_versions_json FROM checkpoints WHERE run_id=? AND namespace=? AND checkpoint_id=?", key).fetchone()
            if old is not None and old != payload:
                raise DomainError("CHECKPOINT_CONFLICT")
            if old is None:
                if body["parent_id"] is not None and not db.execute("SELECT 1 FROM checkpoints WHERE run_id=? AND namespace=? AND checkpoint_id=?", (*key[:2], body["parent_id"])).fetchone():
                    raise DomainError("CHECKPOINT_PARENT_MISSING")
                db.execute("INSERT INTO checkpoints(run_id,namespace,checkpoint_id,parent_id,generation,checkpoint_json,metadata_json,new_versions_json) VALUES(?,?,?,?,?,?,?,?)",
                           (*key, body["parent_id"], body["generation"], *payload[1:]))
            return {"configurable": {"thread_id": key[0], "checkpoint_ns": key[1], "checkpoint_id": key[2]}}
        return self._command(worker, body, "checkpoint_put", change)

    def put_writes(self, worker, body):
        body = validate("CheckpointWrites", body)
        seen = set()
        for position, item in enumerate(body["writes"]):
            expected = WRITES_IDX_MAP.get(item["channel"], position)
            if item["index"] != expected or expected in seen:
                raise DomainError("INVALID_CHECKPOINT_WRITES", 422)
            seen.add(expected)
            item["value_json"] = self._json(item["value_json"])
        if len(canonical(body)) > 4*1024*1024:
            raise DomainError("PAYLOAD_TOO_LARGE", 413)
        def change(db):
            self._scope(db, worker, body["run_id"], body["generation"])
            key = (body["run_id"], body["namespace"], body["checkpoint_id"])
            if not db.execute("SELECT 1 FROM checkpoints WHERE run_id=? AND namespace=? AND checkpoint_id=?", key).fetchone():
                raise DomainError("CHECKPOINT_NOT_FOUND", 404)
            for item in body["writes"]:
                values = (*key, body["task_id"], item["index"], body["task_path"], item["channel"], item["value_json"])
                if item["index"] < 0:
                    db.execute("INSERT INTO checkpoint_writes VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(run_id,namespace,checkpoint_id,task_id,write_index) DO UPDATE SET task_path=excluded.task_path,channel=excluded.channel,value_json=excluded.value_json", values)
                else:
                    db.execute("INSERT OR IGNORE INTO checkpoint_writes VALUES(?,?,?,?,?,?,?,?)", values)
            return {"saved": True}
        return self._command(worker, body, "checkpoint_writes", change)

    def list(self, worker, run, generation, namespace="", *, checkpoint_id=None, before=None, limit=200, filter=None):
        if type(generation) is not int or generation < 1 or not isinstance(namespace, str) or len(namespace)>200 or type(limit) is not int or not 1<=limit<=200:
            raise DomainError("INVALID_REQUEST", 422)
        for value in (checkpoint_id, before):
            if value is not None and (not isinstance(value, str) or not 1<=len(value)<=100):
                raise DomainError("INVALID_REQUEST", 422)
        filter = {} if filter is None else filter
        if not isinstance(filter, dict):
            raise DomainError("INVALID_REQUEST", 422)
        try:
            codec.dumps(filter, 65536)
        except ValueError:
            raise DomainError("INVALID_REQUEST", 422) from None
        def read(db):
            self._scope(db, worker, run, generation)
            query = "SELECT checkpoint_id,parent_id,checkpoint_json,metadata_json,new_versions_json FROM checkpoints WHERE run_id=? AND namespace=?"
            args = [run, namespace]
            if checkpoint_id is not None:
                query += " AND checkpoint_id=?"
                args.append(checkpoint_id)
            if before is not None:
                query += " AND checkpoint_id<?"
                args.append(before)
            query += " ORDER BY checkpoint_id DESC"
            result = []
            for cid, parent, checkpoint, metadata, versions in db.execute(query, args):
                actual = codec.loads(metadata)
                if any(k not in actual or actual[k] != v for k, v in filter.items()):
                    continue
                writes = db.execute("SELECT task_id,channel,value_json FROM checkpoint_writes WHERE run_id=? AND namespace=? AND checkpoint_id=? ORDER BY task_id,write_index", (run, namespace, cid)).fetchall()
                result.append({"run_id": run, "namespace": namespace, "checkpoint_id": cid, "parent_id": parent,
                               "checkpoint_json": checkpoint, "metadata_json": metadata, "new_versions_json": versions,
                               "pending_writes": [list(row) for row in writes]})
                if len(result) == limit:
                    break
            return result
        with self.domain.dispatch_lock:
            return self.domain.writer.call(read, transaction=False)
