"""Typed graph adapter to private coordinator operations."""
import httpx


class Coordinator:
    def __init__(self,client,assignment):
        self.client=client
        self.scope={key:assignment[key] for key in ('run_id','lease_id','generation')}

    async def _call(self,run,operation,*args):
        if run!=self.scope['run_id']:
            raise ValueError('worker run scope mismatch')
        response=await self.client.post('/internal/v1/work/call',json=dict(self.scope,operation=operation,args=list(args)))
        response.raise_for_status()
        return response.json()

    async def readiness(self,run):
        return await self._call(run,'readiness')
    async def criteria(self,run):
        return await self._call(run,'criteria')
    async def discover_page(self,run,cursor,size):
        return await self._call(run,'discover_page',cursor,size)
    async def classify_candidates(self,run,criteria,ids):
        return await self._call(run,'classify_candidates',criteria,ids)
    async def prepare_facts(self,run,job,criteria):
        return await self._call(run,'prepare_facts',job,criteria)
    async def validate_payload(self,run,job,draft,criteria):
        return await self._call(run,'validate_payload',job,draft,criteria)
    async def ensure_action(self,run,job,draft,key):
        return await self._call(run,'ensure_action',job,draft,key)
    async def action_status(self,run,action):
        return await self._call(run,'action_status',action)
    async def record_progress(self,run,job,action):
        return await self._call(run,'record_progress',job,action)
    async def finish_discovery(self,run,criteria):
        return await self._call(run,'finish_discovery',criteria)
    async def draft_narrative(self,run,job,draft):
        context=await self._call(run,'narrative_context',job,draft)
        if context.get('ready_draft_id'):
            return context['ready_draft_id']
        from lila.worker.ai_client import invoke
        result=await invoke(self.client,**self.scope,**context)
        if result['status']!='COMPLETED':
            raise NarrativeUnavailable(result['status'])
        return await self._call(run,'publish_narrative',job,draft,result['value'])


class NarrativeUnavailable(Exception):
    def __init__(self,status):
        self.code={
            'RECONCILIATION_REQUIRED':'AI_RECONCILIATION_REQUIRED',
            'UNCERTAIN':'AI_RECONCILIATION_REQUIRED',
            'INVALID':'AI_OUTPUT_INVALID',
            'REJECTED':'AI_REQUEST_REJECTED',
            'BOUND_EXCEEDED':'AI_BOUND_EXCEEDED',
        }.get(status,'WORKER_ERROR')
        super().__init__(self.code)
