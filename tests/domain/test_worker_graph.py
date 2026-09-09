import asyncio
from uuid import uuid4
import httpx
from langgraph.types import Command
from lila.runtime.checkpointer import CoordinatorSaver
from lila.worker.graph import compile_graph, logical_step
from test_checkpoints import checkpoints


class CoordinatorFixture:
    def __init__(self, maximum=2, repeat=False):
        self.maximum,self.repeat=maximum,repeat
        self.pages=0
        self.actions={}
        self.progress=set()
        self.resolved=False
        self.stopped=False
        self.finished=False

    async def readiness(self, run):
        return {'stopped':self.stopped,'blocker_ids':[]}
    async def criteria(self, run):
        return {'version_id':'fixture-criteria','max_candidates':self.maximum}
    async def discover_page(self,run,cursor,size):
        assert size==25
        self.pages+=1
        return {'candidate_ids':['candidate-a'] if self.repeat else ['candidate-a','candidate-b'],
                'exhausted':not self.repeat,'next_cursor':str(self.pages)}
    async def classify_candidates(self,run,criteria,ids):
        return ids
    async def prepare_facts(self,run,candidate,criteria):
        return {'blocker_ids':[],'prepared_payload_id':'fixture-payload-'+candidate,
                'fact_refs':['fixture-fact'],'artifact_ref':None,'narrative_required':False}
    async def validate_payload(self,*args):
        return []
    async def ensure_action(self,run,candidate,payload,key):
        assert key==logical_step(run,candidate,'fixture-criteria')
        self.actions.setdefault(key,str(uuid4()))
        return self.actions[key]
    async def action_status(self,*args):
        return {'resolved':self.resolved,'blocker_ids':[] if self.resolved else ['APPROVAL_REQUIRED']}
    async def record_progress(self,run,candidate,action):
        self.progress.add(candidate)
    async def finish_discovery(self,*args):
        self.finished=True
        return {'complete':True,'blocker_ids':[]}


def test_graph_interrupt_resume_stable_action_and_maximum(checkpoints):
    async def run():
        coordinator=CoordinatorFixture(maximum=1)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=checkpoints[4]),base_url='https://127.0.0.1:43127',headers=checkpoints[5]) as client:
            def graph():
                return compile_graph(coordinator,CoordinatorSaver(checkpoints[1],1,checkpoints[6],client))
            config={'configurable':{'thread_id':checkpoints[1]},'recursion_limit':100}
            first=await graph().ainvoke({'run_id':checkpoints[1]},config)
            assert first['__interrupt__'] and len(coordinator.actions)==1
            coordinator.resolved=True
            final=await graph().ainvoke(Command(resume={'approved':True}),config)
            assert final['complete'] and len(coordinator.actions)==1
            assert coordinator.progress=={'candidate-a'}
    asyncio.run(run())


def test_graph_two_repeated_pages_terminate(checkpoints):
    async def run():
        coordinator=CoordinatorFixture(maximum=5,repeat=True)
        coordinator.resolved=True
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=checkpoints[4]),base_url='https://127.0.0.1:43127',headers=checkpoints[5]) as client:
            graph=compile_graph(coordinator,CoordinatorSaver(checkpoints[1],1,checkpoints[6],client))
            final=await graph.ainvoke({'run_id':checkpoints[1]},{'configurable':{'thread_id':checkpoints[1]},'recursion_limit':100})
            assert final['complete'] and coordinator.pages==3 and len(coordinator.actions)==1
    asyncio.run(run())


def test_graph_stop_during_wait_prevents_next_candidate(checkpoints):
    async def run():
        coordinator=CoordinatorFixture()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=checkpoints[4]),base_url='https://127.0.0.1:43127',headers=checkpoints[5]) as client:
            graph=compile_graph(coordinator,CoordinatorSaver(checkpoints[1],1,checkpoints[6],client))
            cfg={'configurable':{'thread_id':checkpoints[1]},'recursion_limit':100}
            await graph.ainvoke({'run_id':checkpoints[1]},cfg)
            coordinator.stopped=True
            result=await graph.ainvoke(Command(resume=True),cfg)
            assert result['stopped'] and not coordinator.finished and len(coordinator.actions)==1
    asyncio.run(run())
