import time
from uuid import uuid4
from lila.runtime.installation import prepare
from lila.runtime.service import Runtime


class EmptyBrowser:
    def ready(self,account):
        return True
    def capability(self,account,domain,tab):
        return False
    def discover_page(self,account,criteria,cursor,size):
        return {'jobs':[],'next_cursor':None,'exhausted':True}


def test_separate_worker_runs_zero_match_graph_over_https(tmp_path):
    root=tmp_path/'installation'
    prepare(root)
    runtime=Runtime(root,require_trust=False,preferred_port=0,embedded_test_worker=True,browser_adapter=EmptyBrowser())
    try:
        assert runtime.start()
        domain=runtime.domain
        owner=str(uuid4())
        account=domain.register_account('worker-graph-fixture')
        task=domain.create_task(owner,{'command_id':str(uuid4()),'account_id':account,'instruction':'Find fixture jobs','criteria':{'titles':['Engineer'],'locations':[],'conditions':[]}})['entity_id']
        runtime.work.configure(owner,task,str(uuid4()),1,5)
        domain.task_command(owner,task,{'command_id':str(uuid4()),'expected_revision':2,'operation':'start'})
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            state=domain.task(task)
            if state['state']=='COMPLETED':
                break
            time.sleep(0.1)
        assert state['state']=='COMPLETED'
        assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM checkpoints').fetchone())[0]>0
        assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM actions').fetchone())[0]==0
        assert runtime.worker.process.poll() is None
    finally:
        runtime.close()
