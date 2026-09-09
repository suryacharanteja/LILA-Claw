"""ID-only orchestration. Coordinator adapters own facts, authority and effects."""
from typing import TypedDict
from uuid import UUID, uuid5
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt


class RunState(TypedDict, total=False):
    run_id: str
    criteria_version: str
    current_candidate_id: str|None
    prepared_payload_id: str|None
    fact_refs: list[str]
    artifact_ref: str|None
    blocker_ids: list[str]
    last_action_id: str|None
    queue: list[str]
    seen: list[str]
    processed: int
    max_candidates: int
    page_cursor: str|None
    empty_pages: int
    exhausted: bool
    stopped: bool
    narrative_required: bool
    complete: bool


def logical_step(run_id, candidate_id, criteria_version=None):
    suffix=':'+criteria_version if criteria_version is not None else ''
    return str(uuid5(UUID(run_id), "prepare-application:"+candidate_id+suffix))


def compile_graph(coordinator, saver):
    """Adapter methods are authenticated coordinator calls, never model tools.

    Resume values are notification signals only; they cannot grant authority.
    Implementations must recheck version/scope in each mutation transaction.
    """
    graph = StateGraph(RunState)

    async def gate(state):
        status = await coordinator.readiness(state['run_id'])
        if status['stopped']:
            return False
        while status['blocker_ids']:
            interrupt({'run_id':state['run_id'],'blocker_ids':status['blocker_ids']})
            status = await coordinator.readiness(state['run_id'])
            if status['stopped']:
                return False
        return True

    async def readiness(state):
        if not await gate(state):
            return {'stopped':True}
        criteria = await coordinator.criteria(state['run_id'])
        maximum = criteria['max_candidates']
        if type(maximum) is not int or not 1<=maximum<=10000:
            raise ValueError('owner candidate limit required')
        return {'criteria_version':criteria['version_id'],'max_candidates':maximum,
                'queue':[], 'seen':[], 'processed':0,'empty_pages':0,'page_cursor':None,
                'exhausted':False,'stopped':False,'complete':False,'blocker_ids':[]}

    async def discover(state):
        if not await gate(state):
            return {'stopped':True}
        page = await coordinator.discover_page(state['run_id'],state['page_cursor'],25)
        ids = page['candidate_ids']
        if not isinstance(ids,list) or len(ids)>25 or any(not isinstance(i,str) or not 1<=len(i)<=200 for i in ids):
            raise ValueError('invalid discovery page')
        unseen = list(dict.fromkeys(i for i in ids if i not in state['seen']))
        unseen = unseen[:state['max_candidates']-len(state['seen'])]
        return {'queue':unseen, 'seen':state['seen']+unseen,
                'empty_pages':0 if unseen else state['empty_pages']+1,
                'exhausted':page['exhausted'] is True,'page_cursor':page['next_cursor']}

    async def classify(state):
        if not await gate(state):
            return {'stopped':True}
        # The coordinator stores classification/provenance, including excluded rows.
        queue = await coordinator.classify_candidates(state['run_id'],state['criteria_version'],state['queue'])
        if not isinstance(queue,list) or len(set(queue))!=len(queue) or any(i not in state['queue'] for i in queue):
            raise ValueError('classification scope mismatch')
        return {'queue':queue}

    async def select(state):
        return {'current_candidate_id':state['queue'][0], 'queue':state['queue'][1:],
                'prepared_payload_id':None,'fact_refs':[],'artifact_ref':None,'last_action_id':None}

    async def prepare(state):
        if not await gate(state):
            return {'stopped':True}
        result = await coordinator.prepare_facts(state['run_id'],state['current_candidate_id'],state['criteria_version'])
        while result['blocker_ids']:
            interrupt({'candidate_id':state['current_candidate_id'],'blocker_ids':result['blocker_ids']})
            result = await coordinator.prepare_facts(state['run_id'],state['current_candidate_id'],state['criteria_version'])
        return {k:result[k] for k in ('prepared_payload_id','fact_refs','artifact_ref','narrative_required')}

    async def draft(state):
        if not await gate(state):
            return {'stopped':True}
        version = await coordinator.draft_narrative(state['run_id'],state['current_candidate_id'],state['prepared_payload_id'])
        return {'prepared_payload_id':version}

    async def validate(state):
        if not await gate(state):
            return {'stopped':True}
        blockers = await coordinator.validate_payload(state['run_id'],state['current_candidate_id'],state['prepared_payload_id'],state['criteria_version'])
        while blockers:
            interrupt({'candidate_id':state['current_candidate_id'],'blocker_ids':blockers})
            blockers = await coordinator.validate_payload(state['run_id'],state['current_candidate_id'],state['prepared_payload_id'],state['criteria_version'])
        return {}

    async def ensure(state):
        if not await gate(state):
            return {'stopped':True}
        action = await coordinator.ensure_action(state['run_id'],state['current_candidate_id'],
                  state['prepared_payload_id'],logical_step(state['run_id'],state['current_candidate_id'],state['criteria_version']))
        return {'last_action_id':action}

    async def authority(state):
        if not await gate(state):
            return {'stopped':True}
        result = await coordinator.action_status(state['run_id'],state['last_action_id'])
        while result['resolved'] is not True:
            interrupt({'action_id':state['last_action_id'],'blocker_ids':result['blocker_ids']})
            result = await coordinator.action_status(state['run_id'],state['last_action_id'])
        return {}

    async def progress(state):
        await coordinator.record_progress(state['run_id'],state['current_candidate_id'],state['last_action_id'])
        return {'processed':state['processed']+1}

    async def finish(state):
        # Coordinator independently checks unresolved actions and completion criteria.
        result = await coordinator.finish_discovery(state['run_id'],state['criteria_version'])
        return {'complete':result['complete'] is True,'blocker_ids':result['blocker_ids']}

    def next_candidate(state):
        if state.get('stopped'):
            return END
        if state['queue']:
            return 'select_candidate'
        if state['exhausted'] or state['empty_pages']>=2 or len(state['seen'])>=state['max_candidates']:
            return 'finish'
        return 'discover_page'

    nodes = {'readiness':readiness,'discover_page':discover,'classify_candidates':classify,
             'select_candidate':select,'prepare_facts':prepare,'draft_narrative':draft,
             'validate_payload':validate,'ensure_action':ensure,'await_authority_outcome':authority,
             'record_progress':progress,'finish':finish}
    for name, node in nodes.items():
        graph.add_node(name,node)
    graph.add_edge(START,'readiness')
    def edge(source, target):
        graph.add_conditional_edges(source,lambda state:END if state.get('stopped') else target)
    edge('readiness','discover_page')
    edge('discover_page','classify_candidates')
    graph.add_conditional_edges('classify_candidates',next_candidate)
    edge('select_candidate','prepare_facts')
    graph.add_conditional_edges('prepare_facts',lambda state:END if state.get('stopped') else 'draft_narrative' if state['narrative_required'] else 'validate_payload')
    edge('draft_narrative','validate_payload')
    edge('validate_payload','ensure_action')
    edge('ensure_action','await_authority_outcome')
    edge('await_authority_outcome','record_progress')
    graph.add_conditional_edges('record_progress',next_candidate)
    graph.add_edge('finish',END)
    return graph.compile(checkpointer=saver)
