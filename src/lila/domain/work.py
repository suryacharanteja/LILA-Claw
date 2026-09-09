"""Coordinator task assignments and graph operations. Browser adapter is injected."""
from uuid import uuid4,uuid5,UUID
from lila.domain.core import DomainError,identifier
from lila.domain.grounding import validate_draft
from lila.security.sessions import timestamp


class UnavailableBrowser:
    def ready(self,account):
        return False


class Work:
    TRANSIENT_ERRORS={'WORKER_TRANSPORT_ERROR','EXECUTION_UNAVAILABLE','BROWSER_UNAVAILABLE','WORKER_UNAVAILABLE'}

    def __init__(self,domain,browser=None):
        self.domain=domain
        self.browser=browser or UnavailableBrowser()
        self.domain.work_service=self
        self.retry_after={}

    def _wake_cursor(self,db):
        return db.execute("SELECT coalesce(max(cursor),0) FROM events WHERE kind NOT LIKE 'WORKER_%' AND kind!='ACTION_PREPARED'").fetchone()[0]

    def configure(self,principal,task,command,revision,maximum,policy=None):
        if type(maximum) is not int or not 1<=maximum<=10000 or type(revision) is not int or revision<1:
            raise DomainError('INVALID_REQUEST',422)
        def change(db):
            account,current=self.domain._task(db,task)
            if current!=revision:
                raise DomainError('REVISION_CONFLICT')
            run=self.domain._run(db,task)
            if run and (run[1] not in {'QUEUED','BLOCKED'} or db.execute('SELECT 1 FROM leases WHERE run_id=?',(run[0],)).fetchone()):
                raise DomainError('EXECUTION_SETTINGS_LOCKED')
            if policy and db.execute('SELECT account_id FROM policies WHERE id=?',(identifier(policy),)).fetchone()!=(account,):
                raise DomainError('SCOPE_DENIED',403)
            db.execute('INSERT INTO task_execution VALUES(?,?,?,1) ON CONFLICT(task_id) DO UPDATE SET max_candidates=excluded.max_candidates,policy_id=excluded.policy_id,revision=task_execution.revision+1',(task,maximum,policy))
            db.execute('UPDATE tasks SET revision=revision+1 WHERE id=?',(task,))
            self.domain.event(db,'TASK_EXECUTION_CONFIGURED','task',task,revision+1)
            return self.domain.receipt(task,revision+1,'QUEUED' if run else 'DRAFT')
        return self.domain.command(principal,command,['execution_settings',task,revision,maximum,policy],change)

    def _scope(self,db,worker,run,lease,generation,live=True):
        self.domain._lease(db,lease,worker,generation,run,require_live=live)
        row=db.execute('SELECT t.id,t.account_id,t.criteria_version,t.revision,e.max_candidates,e.policy_id,r.state,r.stop_requested,r.individual_hold FROM runs r JOIN tasks t ON t.id=r.task_id JOIN task_execution e ON e.task_id=t.id WHERE r.id=?',(identifier(run),)).fetchone()
        if not row:
            raise DomainError('EXECUTION_SETTINGS_REQUIRED',422)
        return row

    def next(self,worker):
        worker=identifier(worker)
        with self.domain.dispatch_lock:
            def choose(db):
                self.domain.check_time()
                if self.domain.readiness() or db.execute('SELECT global_hold FROM execution_control WHERE id=1').fetchone()[0]:
                    return None
                cursor=self._wake_cursor(db)
                rows=db.execute("SELECT r.id,t.account_id,t.criteria_version,w.state,w.wake_cursor,w.criteria_version,w.lease_id,w.error_code FROM runs r JOIN tasks t ON t.id=r.task_id JOIN task_execution e ON e.task_id=t.id LEFT JOIN worker_jobs w ON w.run_id=r.id WHERE r.state NOT IN('STOPPED','COMPLETED') AND r.stop_requested=0 AND r.individual_hold=0 ORDER BY t.created_at,r.id").fetchall()
                for run,account,criteria,state,wake,oldcriteria,lease,error in rows:
                    if not self.browser.ready(account):
                        continue
                    if state=='WAITING':
                        if error in self.TRANSIENT_ERRORS:
                            if self.domain.monotonic()<self.retry_after.get(run,0):
                                continue
                        elif wake>=cursor and criteria==oldcriteria:
                            continue
                    if lease:
                        prior=db.execute('SELECT worker_id,generation FROM leases WHERE id=?',(lease,)).fetchone()
                        try:
                            self.domain._lease(db,lease,*prior,run,require_live=False)
                            if prior[0]!=worker:
                                continue
                            return run,criteria,lease,prior[1]
                        except DomainError as exc:
                            if exc.code!='STALE_LEASE':
                                raise
                    generation=(db.execute('SELECT max(generation) FROM leases WHERE run_id=?',(run,)).fetchone()[0] or 0)+1
                    return run,criteria,None,generation
            selected=self.domain.writer.call(choose,transaction=False)
            if selected is None:
                return {'available':False}
            run,criteria,lease,generation=selected
            self.retry_after.pop(run,None)
            lease=lease or self.domain.issue_lease(run,worker,generation)
            def assign(db):
                self._scope(db,worker,run,lease,generation)
                db.execute("INSERT INTO worker_jobs(run_id,lease_id,criteria_version,state) VALUES(?,?,?,'RUNNING') ON CONFLICT(run_id) DO UPDATE SET lease_id=excluded.lease_id,criteria_version=excluded.criteria_version,state='RUNNING',wake_cursor=(SELECT coalesce(max(cursor),0) FROM events),error_code=NULL",(run,lease,criteria))
                db.execute("DELETE FROM run_blockers WHERE run_id=? AND reason='WORKER_UNAVAILABLE'",(run,))
                task=db.execute('SELECT task_id FROM runs WHERE id=?',(run,)).fetchone()[0]
                db.execute("UPDATE runs SET state='ACTIVE',revision=revision+1 WHERE id=?",(run,))
                db.execute('UPDATE tasks SET revision=revision+1 WHERE id=?',(task,))
                self.domain.event(db,'WORKER_ACQUIRED','task',task,self.domain._task(db,task)[1])
                db.execute('UPDATE worker_jobs SET wake_cursor=? WHERE run_id=?',(self._wake_cursor(db),run))
                return {'available':True,'run_id':run,'lease_id':lease,'generation':generation,
                        'namespace':'criteria:'+criteria,'criteria_version':criteria}
            return self.domain.writer.call(assign)

    def call(self,worker,run,lease,generation,operation,args):
        allowed={'readiness','criteria','discover_page','classify_candidates','prepare_facts','validate_payload',
                 'ensure_action','action_status','record_progress','finish_discovery','narrative_context','publish_narrative'}
        if operation not in allowed or not isinstance(args,list):
            raise DomainError('INVALID_REQUEST',422)
        shapes={'readiness':(), 'criteria':(), 'discover_page':((str,type(None)),int),
                'classify_candidates':(str,list),'prepare_facts':(str,str),'validate_payload':(str,str,str),
                'ensure_action':(str,str,str),'action_status':(str,),'record_progress':(str,str),
                'finish_discovery':(str,),'narrative_context':(str,str),'publish_narrative':(str,str,dict)}
        if len(args)!=len(shapes[operation]) or any(not isinstance(v,t) for v,t in zip(args,shapes[operation])):
            raise DomainError('INVALID_REQUEST',422)
        # All mutations re-enter the existing domain gates under the shared control lock.
        def invoke():
            scope=self.domain.writer.call(lambda db:self._scope(db,worker,run,lease,generation,live=operation!='readiness'),transaction=False)
            return getattr(self,'_'+operation)(worker,run,lease,generation,scope,*args)
        if operation in {'discover_page','prepare_facts'}:
            return invoke()  # Browser observations never hold the control lock.
        with self.domain.dispatch_lock:
            return invoke()

    def _readiness(self,worker,run,lease,generation,scope):
        state=self.domain.task(scope[0])
        return {'stopped':scope[6] in {'STOPPED','COMPLETED'} or bool(scope[7]),
                'blocker_ids':state['blocking_reasons']+([] if self.browser.ready(scope[1]) else ['BROWSER_UNAVAILABLE'])}

    def _criteria(self,worker,run,lease,generation,scope):
        return {'version_id':scope[2],'max_candidates':scope[4]}

    def _criteria_version(self,scope,version):
        if scope[2]!=version:
            raise DomainError('CRITERIA_CHANGED',422)

    def _discover_page(self,worker,run,lease,generation,scope,cursor,size):
        if size!=25 or cursor is not None and (not isinstance(cursor,str) or len(cursor)>1000):
            raise DomainError('INVALID_REQUEST',422)
        key='null' if cursor is None else 'cursor:'+cursor
        existing=self.domain.writer.call(lambda db:db.execute('SELECT result_version FROM worker_pages WHERE run_id=? AND criteria_version=? AND cursor_key=?',(run,scope[2],key)).fetchone(),transaction=False)
        if existing:
            return self.domain.writer.call(lambda db:self.domain.value(db,existing[0]),transaction=False)
        criteria=self.domain.writer.call(lambda db:self.domain.value(db,scope[2]),transaction=False)
        page=self.browser.discover_page(scope[1],criteria,cursor,size)
        if not isinstance(page,dict) or set(page)!={'jobs','next_cursor','exhausted'} or not isinstance(page['jobs'],list) or len(page['jobs'])>25 or type(page['exhausted']) is not bool or page['next_cursor'] is not None and (not isinstance(page['next_cursor'],str) or len(page['next_cursor'])>1000):
            raise DomainError('INVALID_BROWSER_OBSERVATION',422)
        with self.domain.dispatch_lock:
            self.domain.writer.call(lambda db:self._criteria_version(self._scope(db,worker,run,lease,generation),scope[2]),transaction=False)
            ids=[]
            for job in page['jobs']:
                if not isinstance(job,dict) or set(job)!={'external_id','metadata'} or not isinstance(job['metadata'],dict):
                    raise DomainError('INVALID_BROWSER_OBSERVATION',422)
                ids.append(self.domain.register_job(scope[1],external_id=job['external_id'],metadata=job['metadata'])['job_id'])
            result={'candidate_ids':ids,'next_cursor':page['next_cursor'],'exhausted':page['exhausted']}
            def save(db):
                self._scope(db,worker,run,lease,generation)
                version=self.domain.content(db,'worker_page',result)
                db.execute('INSERT INTO worker_pages VALUES(?,?,?,?)',(run,scope[2],key,version))
            self.domain.writer.call(save)
            return result
    def _classify_candidates(self,worker,run,lease,generation,scope,criteria,ids):
        self._criteria_version(scope,criteria)
        if not isinstance(ids,list) or len(ids)>25:
            raise DomainError('INVALID_REQUEST',422)
        def classify(db):
            selected=[]
            for job in ids:
                result=self.domain._classify(db,run,identifier(job))
                outcome=db.execute('SELECT effective_outcome FROM applications WHERE account_id=? AND job_id=?',(scope[1],job)).fetchone()[0]
                if result['eligibility']!='EXCLUDED' and outcome not in {'CONFIRMED','USER_REPORTED'}:
                    selected.append(job)
            return selected
        return self.domain.writer.call(classify)

    def _preparation(self,db,run,job,criteria):
        return db.execute('SELECT draft_id,context_version FROM worker_preparations WHERE run_id=? AND job_id=? AND criteria_version=?',(run,identifier(job),criteria)).fetchone()

    def _prepare_facts(self,worker,run,lease,generation,scope,job,criteria):
        self._criteria_version(scope,criteria)
        def read(db):
            candidate=db.execute('SELECT eligibility FROM candidates WHERE run_id=? AND job_id=? AND criteria_version=?',(run,identifier(job),criteria)).fetchone()
            if candidate!=('ELIGIBLE',):
                raise DomainError('MANDATORY_CRITERIA_UNRESOLVED',422)
            old=self._preparation(db,run,job,criteria)
            if old:
                validate_draft(self.domain,db,old[0],scope[1])
                refs=[r[0] for r in db.execute('SELECT fact_version_id FROM draft_facts WHERE draft_id=?',(old[0],))]
                artifact=db.execute('SELECT artifact_version FROM drafts WHERE id=?',(old[0],)).fetchone()[0]
                context=self.domain.value(db,old[1])
                return {'prepared_payload_id':old[0],'fact_refs':refs,'artifact_ref':artifact,'narrative_required':context['narrative_required'],'blocker_ids':[]}
            return None
        old=self.domain.writer.call(read,transaction=False)
        if old:
            return old
        context=self.browser.form_context(scope[1],job)
        if not isinstance(context,dict) or set(context)!={'field_keys','domain','tab_id','narrative_required'} or context['domain']!='www.linkedin.com' or type(context['tab_id']) is not int or context['tab_id']<0 or type(context['narrative_required']) is not bool or not isinstance(context['field_keys'],list) or not 1<=len(context['field_keys'])<=100 or any(not isinstance(f,str) or not f or len(f)>100 for f in context['field_keys']):
            raise DomainError('INVALID_BROWSER_OBSERVATION',422)
        with self.domain.dispatch_lock:
            self.domain.writer.call(lambda db:self._criteria_version(self._scope(db,worker,run,lease,generation),scope[2]),transaction=False)
            def facts(db):
                values,refs={},[]
                for field in context['field_keys']:
                    row=db.execute("SELECT v.id,v.value_version FROM facts f JOIN fact_versions v ON v.id=f.current_version WHERE f.account_id=? AND f.field_key=? AND v.status='VERIFIED'",(scope[1],field)).fetchone()
                    if not row:
                        return None
                    values[field]=self.domain.value(db,row[1])
                    refs.append(row[0])
                application=db.execute('SELECT id FROM applications WHERE account_id=? AND job_id=?',(scope[1],job)).fetchone()[0]
                artifact=db.execute('SELECT version_id FROM selected_documents WHERE account_id=?',(scope[1],)).fetchone()
                return values,refs,application,artifact[0] if artifact else None
            resolved=self.domain.writer.call(facts,transaction=False)
            if resolved is None:
                return {'blocker_ids':['FACTS_REQUIRED']}
            values,refs,application,artifact=resolved
            draft=self.domain.create_draft(application,values,refs,artifact)
            def save(db):
                context_id=self.domain.content(db,'worker_form_context',context)
                db.execute('INSERT INTO worker_preparations VALUES(?,?,?,?,?)',(run,job,criteria,draft['draft_id'],context_id))
            self.domain.writer.call(save)
            return {'prepared_payload_id':draft['draft_id'],'fact_refs':refs,'artifact_ref':artifact,'narrative_required':context['narrative_required'],'blocker_ids':[]}
    def _validate_payload(self,worker,run,lease,generation,scope,job,draft,criteria):
        self._criteria_version(scope,criteria)
        def check(db):
            row=self._preparation(db,run,job,criteria)
            if not row or row[0]!=draft:
                raise DomainError('SCOPE_DENIED',403)
            validate_draft(self.domain,db,draft,scope[1])
            result=self.domain._classify(db,run,job)
            if result['eligibility']!='ELIGIBLE':
                return ['MANDATORY_CRITERIA_UNRESOLVED']
            return []
        try:
            return self.domain.writer.call(check)
        except DomainError as exc:
            if exc.status==422:
                return [exc.code]
            raise

    def _narrative_context(self,worker,run,lease,generation,scope,job,draft):
        from lila.domain.grounding import current_facts
        from lila.domain.ai import AI
        def read(db):
            prep=self._preparation(db,run,job,scope[2])
            if not prep:
                raise DomainError('SCOPE_DENIED',403)
            context=self.domain.value(db,prep[1])
            if draft not in {prep[0],context.get('base_draft_id')}:
                raise DomainError('SCOPE_DENIED',403)
            validate_draft(self.domain,db,prep[0],scope[1])
            value=self.domain.value(db,db.execute('SELECT content_version FROM drafts WHERE id=?',(prep[0],)).fetchone()[0])
            if 'narrative' in value:
                return {'ready_draft_id':prep[0]}
            provider=db.execute('SELECT config_version FROM provider_settings WHERE account_id=?',(scope[1],)).fetchone()
            if not provider:
                raise DomainError('PROVIDER_NOT_ENABLED',422)
            AI(self.domain)._config(db,provider[0])
            if scope[5] is None:
                raise DomainError('POLICY_REQUIRED',422)
            refs=[r[0] for r in db.execute('SELECT fact_version_id FROM draft_facts WHERE draft_id=?',(draft,))]
            facts=current_facts(self.domain,db,scope[1],refs)
            metadata=db.execute('SELECT metadata_version FROM jobs WHERE id=?',(job,)).fetchone()[0]
            description=self.domain.value(db,metadata).get('description','') if metadata else ''
            if not isinstance(description,str):
                description=''
            return {'invocation_id':str(uuid5(UUID(run),'narrative:'+draft)),
                    'config_version':provider[0],'policy_id':scope[5],
                    'facts':[{k:fact[k] for k in ('version_id','field_key','text')} for fact in facts],
                    'job_excerpt':description[:4000]}
        return self.domain.writer.call(read,transaction=False)

    def _publish_narrative(self,worker,run,lease,generation,scope,job,draft,value):
        def read(db):
            prep=self._preparation(db,run,job,scope[2])
            if not prep:
                raise DomainError('SCOPE_DENIED',403)
            context=self.domain.value(db,prep[1])
            if prep[0]!=draft:
                if context.get('base_draft_id')==draft:
                    validate_draft(self.domain,db,prep[0],scope[1])
                    return {'ready':prep[0]}
                raise DomainError('SCOPE_DENIED',403)
            invocation=str(uuid5(UUID(run),'narrative:'+draft))
            if db.execute('SELECT state FROM ai_invocations WHERE id=? AND run_id=?',(invocation,run)).fetchone()!=('COMPLETED',):
                raise DomainError('AI_RESULT_REQUIRED',422)
            record=db.execute('SELECT application_id,content_version,artifact_version FROM drafts WHERE id=?',(draft,)).fetchone()
            refs=[r[0] for r in db.execute('SELECT fact_version_id FROM draft_facts WHERE draft_id=?',(draft,))]
            prior=self.domain.value(db,record[1])
            return {'context':context,'invocation':invocation,'application':record[0],
                    'artifact':record[2],'refs':refs,'value':dict(prior,narrative=value)}
        prepared=self.domain.writer.call(read,transaction=False)
        if 'ready' in prepared:
            return prepared['ready']
        created=self.domain.create_draft(prepared['application'],prepared['value'],prepared['refs'],prepared['artifact'])
        def save(db):
            context=self.domain.content(db,'worker_form_context',dict(prepared['context'],base_draft_id=draft))
            db.execute('UPDATE worker_preparations SET draft_id=?,context_version=? WHERE run_id=? AND job_id=? AND criteria_version=?',(created['draft_id'],context,run,job,scope[2]))
            response=self.domain.content(db,'ai_response',value)
            db.execute('UPDATE ai_invocations SET response_version=? WHERE id=?',(response,prepared['invocation']))
        self.domain.writer.call(save)
        return created['draft_id']

    def _ensure_action(self,worker,run,lease,generation,scope,job,draft,key):
        expected=str(uuid5(UUID(run),'prepare-application:'+job+':'+scope[2]))
        if key!=expected:
            raise DomainError('LOGICAL_STEP_REUSED')
        if self._validate_payload(worker,run,lease,generation,scope,job,draft,scope[2]):
            raise DomainError('FACTS_REQUIRED',422)
        def read(db):
            prep=self._preparation(db,run,job,scope[2])
            context=self.domain.value(db,prep[1])
            record=db.execute('SELECT application_id,content_version FROM drafts WHERE id=?',(draft,)).fetchone()
            old=db.execute('SELECT id,draft_id,state FROM actions WHERE run_id=? AND logical_step_key=?',(run,key)).fetchone()
            if old:
                if old[1]!=draft:
                    raise DomainError('LOGICAL_STEP_REUSED')
                if old[2] in {'PREPARED','READY','WAITING_AUTH'}:
                    db.execute('UPDATE actions SET generation=? WHERE id=?',(generation,old[0]))
                return context,record,old[0]
            return context,record,None
        context,record,old=self.domain.writer.call(read)
        if old:
            return old
        body={'command_id':str(uuid5(UUID(run),'ensure:'+key+':'+str(generation))),
              'lease_id':lease,'generation':generation,'run_id':run,'logical_step_key':key,
              'application_id':record[0],'draft_id':draft,'payload_version':record[1],'kind':'submit_application'}
        return self.domain.propose_action(worker,body,domain=context['domain'],tab_id=context['tab_id'])['entity_id']

    def _action_status(self,worker,run,lease,generation,scope,action):
        def read(db):
            row=db.execute('SELECT state FROM actions WHERE id=? AND run_id=?',(identifier(action),run)).fetchone()
            if not row:
                raise DomainError('SCOPE_DENIED',403)
            return {'resolved':row[0] in {'CONFIRMED','FAILED'},'blocker_ids':[] if row[0] in {'CONFIRMED','FAILED'} else ['OUTCOME_UNRESOLVED']}
        return self.domain.writer.call(read,transaction=False)

    def _record_progress(self,worker,run,lease,generation,scope,job,action):
        row=self.domain.writer.call(lambda db:db.execute('SELECT p.job_id FROM actions a JOIN applications p ON p.id=a.application_id WHERE a.id=? AND a.run_id=?',(action,run)).fetchone(),transaction=False)
        if row!=(job,):
            raise DomainError('SCOPE_DENIED',403)
        if not self._action_status(worker,run,lease,generation,scope,action)['resolved']:
            raise DomainError('OUTCOME_UNRESOLVED')
        return {'recorded':True}

    def _finish_discovery(self,worker,run,lease,generation,scope,criteria):
        self._criteria_version(scope,criteria)
        # Final completion is acknowledged after LangGraph persists its last checkpoint.
        return {'complete':True,'blocker_ids':[]}

    def acknowledge(self,worker,run,lease,generation,state,error=None):
        if state not in {'WAITING','DONE'}:
            raise DomainError('INVALID_REQUEST',422)
        with self.domain.dispatch_lock:
            scope=self.domain.writer.call(lambda db:self._scope(db,worker,run,lease,generation,live=False),transaction=False)
            assigned_criteria=self.domain.writer.call(lambda db:db.execute('SELECT criteria_version FROM worker_jobs WHERE run_id=? AND lease_id=?',(run,lease)).fetchone(),transaction=False)
            if assigned_criteria!=(scope[2],):
                state,error='WAITING','CRITERIA_CHANGED'
            if state=='DONE':
                try:
                    for operation in ('discovery_complete','complete'):
                        revision=self.domain.task(scope[0])['revision']
                        self.domain.lifecycle(worker,run,lease,generation,str(uuid5(UUID(run),'worker:'+operation+':'+str(revision))),revision,operation)
                except DomainError as exc:
                    # Completion rechecks controls after the last graph checkpoint.
                    # Expected blockers are durable work state, not worker failures.
                    if exc.code not in {'EXECUTION_PAUSED','EXECUTION_UNAVAILABLE','READINESS_BLOCKED','OUTCOME_UNRESOLVED','CANDIDATES_UNPROCESSED'}:
                        raise
                    state,error='WAITING',exc.code
            def save(db):
                db.execute('UPDATE worker_jobs SET state=?,error_code=? WHERE run_id=? AND lease_id=?',(state,error,run,lease))
                if state=='WAITING':
                    db.execute('UPDATE runs SET state=?,revision=revision+1 WHERE id=?',('AWAITING_INPUT' if error=='FACTS_REQUIRED' else 'BLOCKED',run))
                    db.execute('UPDATE tasks SET revision=revision+1 WHERE id=?',(scope[0],))
                    self.domain.event(db,'WORKER_WAITING','task',scope[0],self.domain._task(db,scope[0])[1])
            self.domain.writer.call(save)
            if state=='WAITING' and error in self.TRANSIENT_ERRORS:
                self.retry_after[run]=self.domain.monotonic()+5
            else:
                self.retry_after.pop(run,None)
            return {'acknowledged':True}
