"""Coordinator validation of every deterministic answer and narrative segment."""
from lila.contracts.canonical import canonical
from lila.domain.core import DomainError
from lila.worker.provider import grounded,ProviderError


def current_facts(domain,db,account,versions):
    result=[]
    for version in set(versions):
        row=db.execute('SELECT f.field_key,v.value_version,v.status,f.current_version,f.account_id FROM fact_versions v JOIN facts f ON f.id=v.fact_id WHERE v.id=?',(version,)).fetchone()
        if not row or row[2:]!=('VERIFIED',version,account):
            raise DomainError('FACTS_REQUIRED',422)
        value=domain.value(db,row[1])
        result.append({'version_id':version,'field_key':row[0],'value':value,
                       'text':value if isinstance(value,str) else canonical(value).decode()})
    if not result:
        raise DomainError('FACTS_REQUIRED',422)
    return result


def validate_payload(domain,db,account,value,versions):
    facts=current_facts(domain,db,account,versions)
    if not isinstance(value,dict) or not value:
        raise DomainError('FACTS_REQUIRED',422)
    lookup={fact['field_key']:fact['value'] for fact in facts}
    for field,answer in value.items():
        if field=='narrative':
            try:
                grounded(answer,facts)
            except ProviderError as exc:
                raise DomainError(str(exc),422) from None
        elif field not in lookup or canonical(answer)!=canonical(lookup[field]):
            raise DomainError('UNSUPPORTED_FACTUAL_ANSWER',422)
    return facts


def validate_draft(domain,db,draft_id,account):
    row=db.execute('SELECT content_version FROM drafts WHERE id=?',(draft_id,)).fetchone()
    if not row:
        raise DomainError('FACTS_REQUIRED',422)
    refs=[r[0] for r in db.execute('SELECT fact_version_id FROM draft_facts WHERE draft_id=?',(draft_id,))]
    validate_payload(domain,db,account,domain.value(db,row[0]),refs)
