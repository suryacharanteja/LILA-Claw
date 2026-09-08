import secrets
import pytest
from lila.domain.artifacts import Artifacts
from lila.domain.core import DomainError
from io import BytesIO
from pypdf import PdfWriter


def pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=100,height=100)
    writer.add_metadata({'/Title':'private fixture content'})
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


def test_encrypted_publication_corruption_and_recovery(domain,tmp_path):
    artifacts = Artifacts(domain,tmp_path/'objects',secrets.token_bytes(32))
    plain = pdf()
    version = artifacts.publish(domain.account_id,plain,'application/pdf')
    assert artifacts.read(version,domain.account_id)==plain
    path = next((tmp_path/'objects').glob('*.obj'))
    assert plain not in path.read_bytes()
    encoded = bytearray(path.read_bytes())
    encoded[-1] ^= 1
    path.write_bytes(encoded)
    with pytest.raises(DomainError,match='ARTIFACT_CORRUPT'):
        artifacts.read(version,domain.account_id)
    artifacts.recover()
    assert domain.writer.call(lambda db:db.execute('SELECT readiness FROM artifact_versions').fetchone()[0])=='CORRUPT'


def test_missing_staging_and_cross_account(domain,tmp_path):
    artifacts = Artifacts(domain,tmp_path/'objects',secrets.token_bytes(32))
    version = artifacts.publish(domain.account_id,pdf(),'application/pdf')
    other = domain.register_account('another-fixture')
    with pytest.raises(DomainError,match='NOT_FOUND'):
        artifacts.read(version,other)
    path = next((tmp_path/'objects').glob('*.obj'))
    path.rename(path.with_suffix('.missing'))
    artifacts.recover()
    with pytest.raises(DomainError,match='ARTIFACT_NOT_READY'):
        artifacts.read(version,domain.account_id)


def test_invalid_type_archive_traversal_and_docx(domain,tmp_path):
    from docx import Document
    import zipfile
    artifacts = Artifacts(domain,tmp_path/'objects',secrets.token_bytes(32))
    with pytest.raises(DomainError,match='INVALID_ARTIFACT'):
        artifacts.publish(domain.account_id,b'not a PDF','application/pdf')
    doc = Document()
    doc.add_paragraph('fixture only')
    stream = BytesIO()
    doc.save(stream)
    media = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    version = artifacts.publish(domain.account_id,stream.getvalue(),media)
    assert artifacts.read(version,domain.account_id)==stream.getvalue()
    bad = BytesIO(stream.getvalue())
    with zipfile.ZipFile(bad,'a') as archive:
        archive.writestr('../payload.xml','<x/>')
    with pytest.raises(DomainError,match='INVALID_ARTIFACT'):
        artifacts.publish(domain.account_id,bad.getvalue(),media)
