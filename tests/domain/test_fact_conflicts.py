from conftest import uid,action,policy


def test_conflicting_import_does_not_replace_verified_fact_or_approval(domain):
    a,w,l,_,_ = action(domain)
    head = domain.writer.call(lambda db:db.execute("SELECT current_version FROM facts WHERE field_key='name'").fetchone()[0])
    preview = domain.prepare_review([a])
    domain.approval_command(domain.owner,preview['review_id'],{'command_id':uid(),'expected_revision':1,'operation':'approve','payload_version':preview['payload_version'],'members':preview['members']})
    domain.fact_command(domain.owner,domain.account_id,{'command_id':uid(),'expected_revision':1,'operation':'propose','field_key':'name','value':'Conflicting imported name'})
    assert domain.writer.call(lambda db:db.execute("SELECT current_version FROM facts WHERE field_key='name'").fetchone()[0])==head
    assert domain.writer.call(lambda db:db.execute('SELECT state FROM approvals').fetchone()[0])=='ACTIVE'
    assert domain.writer.call(lambda db:db.execute("SELECT count(*) FROM fact_versions WHERE status='PROPOSED'").fetchone()[0])==1
    domain.fact_command(domain.owner,domain.account_id,{'command_id':uid(),'expected_revision':2,'operation':'verify','field_key':'name','value':'Owner chosen correction'})
    assert domain.writer.call(lambda db:db.execute('SELECT state FROM approvals').fetchone()[0])=='REVOKED'
