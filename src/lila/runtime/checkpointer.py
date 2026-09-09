"""LangGraph saver using separate injected sync/async coordinator HTTP clients."""
from uuid import uuid5, NAMESPACE_URL
from langgraph.checkpoint.base import BaseCheckpointSaver, CheckpointTuple, WRITES_IDX_MAP
from lila.contracts import checkpoint_json as codec
from lila.contracts.canonical import canonical


class CoordinatorSaver(BaseCheckpointSaver[int]):
    def __init__(self, run_id, generation, client, async_client, namespace_prefix=""):
        super().__init__(serde=codec.CheckpointSerializer())
        self.run_id, self.generation = run_id, generation
        self.client, self.async_client = client, async_client
        self.namespace_prefix = namespace_prefix

    def _scope(self, config):
        value = config.get("configurable", {}) if config else {}
        if value.get("thread_id", self.run_id) != self.run_id:
            raise ValueError("checkpoint run scope mismatch")
        return {"run_id": self.run_id, "generation": self.generation,
                "namespace": self.namespace_prefix+value.get("checkpoint_ns", "")}

    def _config(self, namespace, checkpoint_id):
        if not namespace.startswith(self.namespace_prefix):
            raise ValueError('checkpoint namespace scope mismatch')
        namespace=namespace[len(self.namespace_prefix):]
        return {"configurable": {"thread_id": self.run_id, "checkpoint_ns": namespace,
                                 "checkpoint_id": checkpoint_id}}

    def _tuple(self, row):
        if row is None:
            return None
        if row["run_id"] != self.run_id:
            raise ValueError("checkpoint response scope mismatch")
        namespace = row["namespace"]
        return CheckpointTuple(self._config(namespace, row["checkpoint_id"]),
                               codec.loads(row["checkpoint_json"]), codec.loads(row["metadata_json"], 65536),
                               self._config(namespace, row["parent_id"]) if row["parent_id"] else None,
                               [(task, channel, codec.loads(value)) for task, channel, value in row["pending_writes"]])

    def _query(self, config, *, filter=None, before=None, limit=None):
        query = self._scope(config)
        if config and config.get("configurable", {}).get("checkpoint_id"):
            query["checkpoint_id"] = config["configurable"]["checkpoint_id"]
        if before:
            if self._scope(before) != self._scope(config):
                raise ValueError("checkpoint cursor scope mismatch")
            query["before"] = before["configurable"]["checkpoint_id"]
        if filter is not None:
            query["filter"] = codec.dumps(filter, 65536)
        if limit is not None:
            query["limit"] = limit
        return query

    def get_tuple(self, config):
        response = self.client.get("/internal/v1/checkpoints", params=self._query(config))
        response.raise_for_status()
        return self._tuple(response.json())

    async def aget_tuple(self, config):
        response = await self.async_client.get("/internal/v1/checkpoints", params=self._query(config))
        response.raise_for_status()
        return self._tuple(response.json())

    def list(self, config, *, filter=None, before=None, limit=None):
        if limit is not None and limit <= 0:
            return
        remaining = limit
        while True:
            query = self._query(config, filter=filter, before=before, limit=min(remaining, 200) if remaining is not None else 200)
            response = self.client.get("/internal/v1/checkpoints/list", params=query)
            response.raise_for_status()
            rows = response.json()
            for row in rows:
                yield self._tuple(row)
            if remaining is not None:
                remaining -= len(rows)
            if not rows or len(rows)<query["limit"] or remaining == 0:
                return
            before = self._config(rows[-1]["namespace"], rows[-1]["checkpoint_id"])

    async def alist(self, config, *, filter=None, before=None, limit=None):
        if limit is not None and limit <= 0:
            return
        remaining = limit
        while True:
            query = self._query(config, filter=filter, before=before, limit=min(remaining, 200) if remaining is not None else 200)
            response = await self.async_client.get("/internal/v1/checkpoints/list", params=query)
            response.raise_for_status()
            rows = response.json()
            for row in rows:
                yield self._tuple(row)
            if remaining is not None:
                remaining -= len(rows)
            if not rows or len(rows)<query["limit"] or remaining == 0:
                return
            before = self._config(rows[-1]["namespace"], rows[-1]["checkpoint_id"])

    def _command(self, operation, body):
        # Identical network replay carries the same command identity; changed special
        # pending writes get a new identity while retaining their reserved write index.
        import hashlib
        digest = hashlib.sha256(canonical([operation, body])).hexdigest()
        return dict(body, command_id=str(uuid5(NAMESPACE_URL, "lila-checkpoint:"+digest)))

    def _put(self, config, checkpoint, metadata, new_versions):
        return self._command("put", dict(self._scope(config), checkpoint_id=checkpoint["id"],
            parent_id=config.get("configurable", {}).get("checkpoint_id"),
            checkpoint_json=codec.dumps(checkpoint), metadata_json=codec.dumps(metadata, 65536),
            new_versions_json=codec.dumps(new_versions, 65536)))

    def put(self, config, checkpoint, metadata, new_versions):
        body = self._put(config, checkpoint, metadata, new_versions)
        response = self.client.post("/internal/v1/checkpoints", json=body)
        response.raise_for_status()
        return self._config(body["namespace"], checkpoint["id"])

    async def aput(self, config, checkpoint, metadata, new_versions):
        body = self._put(config, checkpoint, metadata, new_versions)
        response = await self.async_client.post("/internal/v1/checkpoints", json=body)
        response.raise_for_status()
        return self._config(body["namespace"], checkpoint["id"])

    def _writes(self, config, writes, task_id, task_path):
        return self._command("writes", dict(self._scope(config),
            checkpoint_id=config["configurable"]["checkpoint_id"], task_id=task_id, task_path=task_path,
            writes=[{"index": WRITES_IDX_MAP.get(channel, index), "channel": channel, "value_json": codec.dumps(value)}
                    for index, (channel, value) in enumerate(writes)]))

    @staticmethod
    def _awaiting_checkpoint(response):
        return response.status_code == 404 and response.json().get("code") == "CHECKPOINT_NOT_FOUND"

    def put_writes(self, config, writes, task_id, task_path=""):
        import time
        body = self._writes(config, writes, task_id, task_path)
        deadline = time.monotonic()+5
        while True:
            response = self.client.post("/internal/v1/checkpoints/writes", json=body)
            if not self._awaiting_checkpoint(response) or time.monotonic() >= deadline:
                response.raise_for_status()
                return
            # LangGraph schedules checkpoint puts and writes concurrently. Retry only
            # the explicit missing-parent response, preserving the command identity.
            time.sleep(0.02)

    async def aput_writes(self, config, writes, task_id, task_path=""):
        import asyncio
        import time
        body = self._writes(config, writes, task_id, task_path)
        deadline = time.monotonic()+5
        while True:
            response = await self.async_client.post("/internal/v1/checkpoints/writes", json=body)
            if not self._awaiting_checkpoint(response) or time.monotonic() >= deadline:
                response.raise_for_status()
                return
            await asyncio.sleep(0.02)

    def delete_thread(self, thread_id):
        raise PermissionError("checkpoint deletion requires coordinator privacy operation")

    async def adelete_thread(self, thread_id):
        raise PermissionError("checkpoint deletion requires coordinator privacy operation")

    def get_next_version(self, current, channel):
        if current is None:
            return 1
        if type(current) is not int or current < 0 or current >= 2**63-1:
            raise ValueError("invalid channel version")
        return current+1

    def get_delta_channel_history(self, **kwargs):
        raise NotImplementedError("DeltaChannel is not part of the approved graph")

    async def aget_delta_channel_history(self, **kwargs):
        raise NotImplementedError("DeltaChannel is not part of the approved graph")
