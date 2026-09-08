import secrets
import httpx
import pytest
from fastapi.testclient import TestClient
from lila.api.auth import create_app
from lila.api.domain import attach_domain
from lila.api.uploads import UploadParser
from lila.domain.artifacts import Artifacts
from lila.domain.documents import Documents
from lila.domain.core import DomainError
from lila.storage.writer import StoreWriter
from lila.security.sessions import Sessions
from conftest import uid
from test_artifacts import pdf


def multipart(account,command,data):
    request = httpx.Request('POST','https://127.0.0.1',data={'account_id':account,'command_id':command},files={'file':('resume.pdf',data,'application/pdf')})
    return request.headers['content-type'],request.read()


def test_chunked_multipart_limits_duplicates_and_truncation(domain):
    content_type,data = multipart(domain.account_id,uid(),pdf())
    parser = UploadParser(content_type)
    for position in range(0,len(data),7):
        parser.write(data[position:position+7])
    assert parser.result()['data']==pdf()
    small = UploadParser(content_type,max_size=20)
    with pytest.raises(DomainError,match='PAYLOAD_TOO_LARGE'):
        small.write(data)
    truncated = UploadParser(content_type)
    truncated.write(data[:-10])
    with pytest.raises(DomainError,match='INVALID_MULTIPART'):
        truncated.result()


def test_upload_status_selection_idempotency_auth_and_safe_files(domain,tmp_path):
    artifacts = Artifacts(domain,tmp_path/'objects',secrets.token_bytes(32))
    domain.artifacts,domain.documents = artifacts,Documents(domain,artifacts)
    auth = StoreWriter(tmp_path/'auth.db',secrets.token_bytes(32),'auth')
    try:
        sessions = Sessions(auth,secrets.token_bytes(32))
        app = create_app(sessions,43127)
        attach_domain(app,sessions,domain)
        url='https://127.0.0.1:43127'
        with TestClient(app,base_url=url) as client:
            body = {'command_id':uid(),'account_id':domain.account_id}
            files = {'file':('resume.pdf',pdf(),'application/pdf')}
            assert client.post('/api/v1/documents/uploads',headers={'Origin':url},data=body,files=files).status_code==401
            session = client.post('/api/v1/auth/bootstrap',headers={'Origin':url},json={'token':sessions.issue_bootstrap()}).json()
            headers = {'Origin':url,'X-Lila-CSRF':session['csrf_token']}
            receipt = client.post('/api/v1/documents/uploads',headers=headers,data=body,files=files)
            assert receipt.status_code==200,receipt.text
            assert 'no-store' in receipt.headers['cache-control']
            result = receipt.json()
            assert client.post('/api/v1/documents/uploads',headers=headers,data=body,files=files).json()==result
            status = client.get('/api/v1/documents/uploads/'+result['upload_id']).json()
            assert status['status']=='READY'
            selected = client.post('/api/v1/documents/'+result['upload_id']+'/commands',headers=headers,json={'command_id':uid(),'expected_revision':status['revision'],'operation':'select','source_version':status['version_id'],'format':'pdf'})
            assert selected.status_code==200,selected.text
            assert selected.json()['state']=='SELECTED'
            assert domain.writer.call(lambda db:db.execute("SELECT count(*) FROM operations WHERE kind='DOCUMENT_EXTRACT'").fetchone()[0])==1
            assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM facts').fetchone()[0])==0
            assert len(list((tmp_path/'objects').iterdir()))==1
            assert not any(pdf() in path.read_bytes() for path in (tmp_path/'objects').iterdir())
    finally:
        auth.close()


def test_publication_failure_and_recovery_are_visible(domain,tmp_path):
    artifacts = Artifacts(domain,tmp_path/'objects',secrets.token_bytes(32))
    documents = Documents(domain,artifacts)
    receipt = documents.accept(domain.owner,uid(),domain.account_id,'resume.pdf',b'bad','application/pdf')
    documents.publish(receipt['upload_id'],b'bad','application/pdf')
    assert documents.status(receipt['upload_id'])['error_code']=='INVALID_ARTIFACT'
    accepted = documents.accept(domain.owner,uid(),domain.account_id,'resume.pdf',pdf(),'application/pdf')
    documents.recover()
    assert documents.status(accepted['upload_id'])['error_code']=='UPLOAD_INTERRUPTED'
    recovered = documents.accept(domain.owner,uid(),domain.account_id,'resume.pdf',pdf(),'application/pdf')
    artifacts.publish(domain.account_id,pdf(),'application/pdf',document_id=recovered['upload_id'])
    documents.recover()
    assert documents.status(recovered['upload_id'])['status']=='READY'
