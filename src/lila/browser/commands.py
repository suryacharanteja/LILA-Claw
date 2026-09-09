"""Pure validation before an authenticated browser command may be dispatched."""
from dataclasses import dataclass
from lila.domain.core import DomainError,validate
from lila.security.sessions import seconds


@dataclass(frozen=True)
class Context:
    run_id:str
    generation:int
    account_id:str
    tab_id:int
    origin:str
    adapter_id:str
    payload_version:str
    connected:bool
    form_fingerprint:str|None=None


ARGUMENTS={
    'inspect_context':set(),
    'discover_jobs':{'query'},
    'inspect_form':{'expected_step'},
    'fill_fields':{'field_values'},
    'attach_document':{'document_capability'},
    'advance_step':{'expected_step'},
    'submit_application':set(),
    'inspect_outcome':{'existing_action_id'},
}
MUTATING={'fill_fields','attach_document','advance_step','submit_application'}


def validate_command(body,context:Context,now):
    """Context is trusted coordinator state, never populated from command fields.

    This validates context, not action authority. Dispatcher policy/hold/lease
    gates and fresh extension-side inspection remain mandatory before effects.
    """
    body=validate('BrowserAction',body)
    if context.connected is not True:
        raise DomainError('BROWSER_UNAVAILABLE',422)
    if seconds(body['expires_at'])<=now:
        raise DomainError('BROWSER_COMMAND_EXPIRED',422)
    for field in ('run_id','generation','account_id','tab_id','adapter_id','payload_version'):
        if body[field]!=getattr(context,field):
            raise DomainError('BROWSER_CONTEXT_CHANGED',403)
    if context.origin!=body['allowed_origin']:
        raise DomainError('BROWSER_CONTEXT_CHANGED',403)
    tool=body['tool']
    if set(body['arguments'])!=ARGUMENTS[tool]:
        raise DomainError('INVALID_TOOL_ARGUMENTS',422)
    if tool in MUTATING:
        if not context.form_fingerprint or body.get('form_fingerprint')!=context.form_fingerprint:
            raise DomainError('FORM_CHANGED',422)
    if tool=='fill_fields':
        fields=body['arguments']['field_values']
        if not fields or len({f['field_key'] for f in fields})!=len(fields):
            raise DomainError('INVALID_TOOL_ARGUMENTS',422)
    return body
