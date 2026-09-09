import io
import secrets
from docx import Document
from pypdf import PdfWriter
import pytest
from conftest import uid
from lila.worker.documents import extract
from lila.domain.artifacts import Artifacts
from lila.domain.documents import Documents
from lila.domain.extraction import Extraction
from lila.domain.core import DomainError


def test_image_only_pdf_requires_manual_facts():
    writer=PdfWriter()
    writer.add_blank_page(width=100,height=100)
    data=io.BytesIO()
    writer.write(data)
    result=extract(data.getvalue(),'application/pdf')
    assert result=={'text':'','proposals':[],'status':'MANUAL_ENTRY_REQUIRED'}


def test_extraction_reclaim_fences_old_worker_and_replay_is_idempotent(domain,tmp_path):
    domain.artifacts=Artifacts(domain,tmp_path/'objects',secrets.token_bytes(32))
    domain.documents=Documents(domain,domain.artifacts)
    document=Document()
    document.add_paragraph('Name: Fixture Person')
    data=io.BytesIO()
    document.save(data)
    media='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    upload=domain.documents.accept(domain.owner,uid(),domain.account_id,'fixture.docx',data.getvalue(),media)
    domain.documents.publish(upload['upload_id'],data.getvalue(),media)
    service=Extraction(domain)
    old,new=uid(),uid()
    assignment=service.next(old,1)
    assert service.next(new,2)['operation_id']==assignment['operation_id']
    with pytest.raises(DomainError):
        service.data(old,1,assignment['operation_id'])
    result=extract(service.data(new,2,assignment['operation_id']),media)
    first=service.result(new,2,assignment['operation_id'],result)
    assert service.result(new,2,assignment['operation_id'],result)==first
    assert domain.writer.call(lambda db:db.execute('SELECT count(*) FROM fact_versions').fetchone())[0]==1
    assert service.next(new,2)=={'available':False}
