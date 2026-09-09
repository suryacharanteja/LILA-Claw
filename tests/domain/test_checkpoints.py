import asyncio
import json
from typing import TypedDict
import httpx
import httpx2
import pytest
from fastapi.testclient import TestClient
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, Interrupt, interrupt
from langgraph.checkpoint.base import empty_checkpoint
from conftest import task, uid
from lila.api.auth import create_app
from lila.api.checkpoints import attach_checkpoints
from lila.contracts import checkpoint_json as codec
from lila.domain.checkpoints import Checkpoints
from lila.domain.core import DomainError
from lila.runtime.checkpointer import CoordinatorSaver
from lila.runtime.worker import WorkerRegistry


@pytest.fixture
def checkpoints(domain):
    task_id = task(domain)
    domain.task_command(domain.owner, task_id, {"command_id":uid(), "expected_revision":1, "operation":"start"})
    run = domain.task(task_id)["run_id"]
    registry = WorkerRegistry()
    boot = registry.register()
    lease = domain.issue_lease(run, boot["worker_id"], 1)
    app = create_app(None, 43127, workers=registry)
    attach_checkpoints(app, domain, registry)
    headers = {"Authorization":"Bearer "+boot["token"], "X-Lila-Generation":str(boot["generation"])}
    with TestClient(app, base_url="https://127.0.0.1:43127", headers=headers) as client:
        yield domain, run, boot, lease, app, headers, client


def saver(fixture, async_client=None):
    _, run, _, _, _, _, client = fixture
    return CoordinatorSaver(run, 1, client, async_client)


def config(fixture):
    return {"configurable":{"thread_id":fixture[1], "checkpoint_ns":""}}


@pytest.mark.parametrize("value", [float("nan"), 1.2, object(), {"x":2**63}, {"$lila_checkpoint":"bytes"}])
def test_codec_rejects_unsafe_values(value):
    with pytest.raises(ValueError):
        codec.dumps(value)


@pytest.mark.parametrize("text", ['{"x":1,"x":2}', '{"x":NaN}', '{"$lila_checkpoint":"import","value":"os"}', '{"$lila_checkpoint":"bytes","value":"!!!"}'])
def test_codec_rejects_unsafe_wire(text):
    with pytest.raises(ValueError):
        codec.loads(text)


def test_codec_interrupt_and_bytes_roundtrip():
    result = codec.loads(codec.dumps({"bytes":b"\x00\xff", "interrupt":Interrupt({"question":"fixture"}, id="id")}))
    assert result["bytes"] == b"\x00\xff"
    assert result["interrupt"].id == "id"
    assert result["interrupt"].value == {"question":"fixture"}
    with pytest.raises(ValueError):
        codec.CheckpointSerializer().loads_typed(("pickle", b"payload"))


def test_checkpoint_history_writes_conflicts_and_fences(checkpoints):
    domain, run, boot, lease, *_ = checkpoints
    cp = saver(checkpoints)
    first = empty_checkpoint()
    first["channel_values"] = {"artifact":b"fixture"}
    first["channel_versions"] = {"artifact":1}
    initial = config(checkpoints)
    saved = cp.put(initial, first, {"step":0, "source":"input"}, {"artifact":1})
    assert cp.put(initial, first, {"step":0, "source":"input"}, {"artifact":1}) == saved
    cp.put_writes(saved, [("value", "original"), ("__error__", "first")], "task", "path/a")
    cp.put_writes(saved, [("value", "replacement"), ("__error__", "second")], "task", "path/b")
    pending = cp.get_tuple(saved).pending_writes
    assert ("task", "value", "original") in pending
    assert ("task", "__error__", "second") in pending
    assert domain.writer.call(lambda db:db.execute("SELECT task_path FROM checkpoint_writes WHERE write_index=-1").fetchone())[0] == "path/b"
    second = empty_checkpoint()
    saved2 = cp.put(saved, second, {"step":1, "source":"loop"}, {})
    assert cp.get_tuple(initial).config == saved2
    assert cp.get_tuple(saved2).parent_config == saved
    assert len(list(cp.list(initial, filter={"source":"input"}))) == 1
    assert list(cp.list(initial, before=saved2))[0].config == saved
    first["channel_values"] = {"changed":True}
    with pytest.raises((httpx.HTTPStatusError, httpx2.HTTPStatusError)) as conflict:
        cp.put(initial, first, {"step":0, "source":"input"}, {})
    assert conflict.value.response.status_code == 409
    domain.test_clock[0] += 11
    with pytest.raises((httpx.HTTPStatusError, httpx2.HTTPStatusError)) as stale:
        cp.get_tuple(saved)
    assert stale.value.response.status_code == 403
    with pytest.raises((httpx.HTTPStatusError, httpx2.HTTPStatusError)):
        cp.put(saved, second, {"step":1, "source":"loop"}, {})


class State(TypedDict):
    candidate_id: str
    approved: bool


def graph(cp):
    builder = StateGraph(State)
    def review(state):
        approved = interrupt({"candidate_id":state["candidate_id"]})
        return {"approved":approved}
    builder.add_node("review", review)
    builder.add_edge(START, "review")
    builder.add_edge("review", END)
    return builder.compile(checkpointer=cp)


def test_real_langgraph_resume_from_new_saver(checkpoints):
    cfg = config(checkpoints)
    result = graph(saver(checkpoints)).invoke({"candidate_id":"fixture-id", "approved":False}, cfg)
    assert result["__interrupt__"][0].value == {"candidate_id":"fixture-id"}
    resumed = graph(saver(checkpoints)).invoke(Command(resume=True), cfg)
    assert resumed["approved"] is True
    assert resumed["candidate_id"] == "fixture-id"


def test_real_async_langgraph_resume(checkpoints):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=checkpoints[4]), base_url="https://127.0.0.1:43127", headers=checkpoints[5]) as client:
            cp = saver(checkpoints, client)
            cfg = config(checkpoints)
            result = await graph(cp).ainvoke({"candidate_id":"async-fixture", "approved":False}, cfg)
            assert result["__interrupt__"]
            result = await graph(saver(checkpoints, client)).ainvoke(Command(resume=True), cfg)
            assert result["approved"] is True
            assert len([item async for item in cp.alist(cfg)]) >= 3
            with pytest.raises(PermissionError):
                await cp.adelete_thread(checkpoints[1])
    asyncio.run(run())


def test_worker_scope_and_deletion_denied(checkpoints):
    cp = saver(checkpoints)
    with pytest.raises(ValueError):
        cp.get_tuple({"configurable":{"thread_id":uid()}})
    with pytest.raises(PermissionError):
        cp.delete_thread(checkpoints[1])
    assert checkpoints[6].get("/internal/v1/checkpoints", params={"run_id":checkpoints[1],"generation":1}, headers={"Authorization":"Bearer invalid"}).status_code == 403
    with pytest.raises(DomainError):
        Checkpoints(checkpoints[0]).list(uid(), checkpoints[1], 1)


@pytest.mark.parametrize('operation',['checkpoint','writes'])
def test_lost_checkpoint_reply_replays_once_and_fenced_replay_is_denied(checkpoints,operation):
    class LoseReply(httpx.ASGITransport):
        lost=False
        async def handle_async_request(self,request):
            response=await super().handle_async_request(request)
            target='/internal/v1/checkpoints'+('/writes' if operation=='writes' else '')
            if request.method=='POST' and request.url.path==target and not self.lost:
                self.lost=True
                await response.aclose()
                raise httpx.ReadError('Injected lost checkpoint reply',request=request)
            return response
    async def run():
        async with httpx.AsyncClient(transport=LoseReply(app=checkpoints[4]),base_url='https://127.0.0.1:43127',headers=checkpoints[5]) as client:
            cp=saver(checkpoints,client)
            initial=config(checkpoints)
            value=empty_checkpoint()
            saved={'configurable':dict(initial['configurable'],checkpoint_id=value['id'])}
            async def send():
                if operation=='checkpoint':
                    return await cp.aput(initial,value,{'step':0},{})
                return await cp.aput_writes(saved,[('value','fixture')],'fixture-task')
            if operation=='writes':
                await cp.aput(initial,value,{'step':0},{})
            with pytest.raises(httpx.ReadError):
                await send()
            await send()
            row=await cp.aget_tuple(saved)
            assert row.checkpoint['id']==value['id']
            assert row.pending_writes==([('fixture-task','value','fixture')] if operation=='writes' else [])
            assert checkpoints[0].writer.call(lambda db:db.execute('SELECT count(*) FROM checkpoints').fetchone())==(1,)
            checkpoints[0].issue_lease(checkpoints[1],uid(),2)
            with pytest.raises(httpx.HTTPStatusError) as denied:
                await send()
            assert denied.value.response.status_code==403
    asyncio.run(run())


def test_checkpoint_pagination_and_criteria_namespace_isolation(checkpoints):
    cp=CoordinatorSaver(checkpoints[1],1,checkpoints[6],None,namespace_prefix='criteria:first/')
    initial=config(checkpoints)
    saved=initial
    ids=[]
    for index in range(205):
        value=empty_checkpoint()
        ids.append(value['id'])
        saved=cp.put(saved,value,{'step':index},{})
    assert [row.checkpoint['id'] for row in cp.list(initial)]==list(reversed(ids))
    assert len(list(cp.list(initial,limit=201)))==201
    other=CoordinatorSaver(checkpoints[1],1,checkpoints[6],None,namespace_prefix='criteria:second/')
    assert other.get_tuple(initial) is None
    assert list(other.list(initial))==[]
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=checkpoints[4]),base_url='https://127.0.0.1:43127',headers=checkpoints[5]) as client:
            reader=CoordinatorSaver(checkpoints[1],1,None,client,namespace_prefix='criteria:first/')
            assert [row.checkpoint['id'] async for row in reader.alist(initial)]==list(reversed(ids))
            assert all([row.config['configurable']['checkpoint_ns']=='' async for row in reader.alist(initial,limit=2)])
    asyncio.run(run())
