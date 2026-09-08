"""Versioned LILAOBJ1 publication. Paths contain only generated opaque IDs."""
import base64
import hashlib
import json
import secrets
import struct
import io
import zipfile
from pathlib import Path
from uuid import uuid4
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from lila.contracts.canonical import canonical
from lila.domain.core import DomainError,identifier
from lila.security.windows import private_directory,write_private

MAGIC = b'LILAOBJ1'
MAX_SIZE = 100*1024*1024
MEDIA = {'application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document'}


def validate_document(data,media_type):
    """Bounded format preflight; extraction is a separate worker operation."""
    try:
        if media_type=='application/pdf':
            from pypdf import PdfReader
            if not data.startswith(b'%PDF-') or b'%%EOF' not in data[-1024:]:
                raise ValueError()
            reader = PdfReader(io.BytesIO(data),strict=True)
            if reader.is_encrypted or not 1<=len(reader.pages)<=2000:
                raise ValueError()
            root = reader.trailer['/Root']
            if any(key in root for key in ('/OpenAction','/AA')):
                raise ValueError()
            names = root.get('/Names')
            if names and any(key in names.get_object() for key in ('/JavaScript','/EmbeddedFiles')):
                raise ValueError()
        else:
            from defusedxml.ElementTree import fromstring
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries = archive.infolist()
                names = [entry.filename for entry in entries]
                if len(entries)>2000 or len(names)!=len(set(names)) or not {'[Content_Types].xml','word/document.xml'}.issubset(names):
                    raise ValueError()
                if sum(entry.file_size for entry in entries)>MAX_SIZE:
                    raise ValueError()
                for entry in entries:
                    if entry.flag_bits&1 or entry.file_size>20*1024*1024 or entry.file_size>max(1,entry.compress_size)*1000:
                        raise ValueError()
                    name = entry.filename
                    if name.startswith(('/','\\')) or '..' in name.replace('\\','/').split('/') or ':' in name or name.lower().endswith(('.bin','.exe','.dll')):
                        raise ValueError()
                    if name.endswith(('.xml','.rels')):
                        root = fromstring(archive.read(entry))
                        if name.endswith('.rels') and any(node.attrib.get('TargetMode')=='External' for node in root):
                            raise ValueError()
                if archive.testzip() is not None:
                    raise ValueError()
    except Exception as exc:
        # Third-party parse errors must not leak file content or parser internals.
        raise DomainError('INVALID_ARTIFACT',422) from None


class Artifacts:
    def __init__(self,domain,root,wrap_key,key_id='1'):
        self.domain,self.root,self.wrap_key,self.key_id = domain,Path(root),wrap_key,key_id
        private_directory(self.root)

    def _path(self,object_id):
        return self.root/(identifier(object_id)+'.obj')

    def publish(self,account_id,plaintext,media_type,document_id=None):
        if not isinstance(plaintext,bytes) or not 0<len(plaintext)<=MAX_SIZE or media_type not in MEDIA:
            raise DomainError('INVALID_ARTIFACT',422)
        validate_document(plaintext,media_type)
        version,object_id = str(uuid4()),str(uuid4())
        document_id = identifier(document_id) if document_id else str(uuid4())
        dek,nonce,wrap_nonce = secrets.token_bytes(32),secrets.token_bytes(12),secrets.token_bytes(12)
        header = {'format':1,'object_id':object_id,'version_id':version,'key_id':self.key_id,'nonce_b64':base64.b64encode(nonce).decode(),'plaintext_length':len(plaintext),'media_type':media_type}
        encoded = canonical(header)
        aad = MAGIC+struct.pack('>I',len(encoded))+encoded
        ciphertext = aad+AESGCM(dek).encrypt(nonce,plaintext,aad)
        wrap_aad = canonical({'format':1,'key_id':self.key_id,'object_id':object_id,'version_id':version})
        wrapped = wrap_nonce+AESGCM(self.wrap_key).encrypt(wrap_nonce,dek,wrap_aad)
        def stage(db):
            self.domain.account(db,account_id)
            owner = db.execute('SELECT account_id FROM artifact_versions WHERE document_id=? LIMIT 1',(document_id,)).fetchone()
            if owner and owner[0]!=account_id:
                raise DomainError('SCOPE_DENIED',403)
            db.execute("INSERT INTO artifact_versions VALUES(?,?,?,?,?,?,?,?,?,'STAGING',?)",(version,document_id,account_id,object_id,media_type,len(plaintext),hashlib.sha256(plaintext).hexdigest(),self.key_id,wrapped,self.domain.stamp()))
        self.domain.writer.call(stage)
        write_private(self._path(object_id),ciphertext)
        def ready(db):
            # Verify publication before exposing READY; crash leaves a recoverable STAGING row.
            self.read_in_transaction(db,version,account_id,allow_staging=True)
            db.execute("UPDATE artifact_versions SET readiness='READY' WHERE id=?",(version,))
            self.domain.event(db,'ARTIFACT_READY','artifact',version,1)
        self.domain.writer.call(ready)
        return version

    def read_in_transaction(self,db,version,account_id,allow_staging=False):
        row = db.execute('SELECT object_id,media_type,byte_length,digest,key_id,wrapped_dek,readiness,account_id FROM artifact_versions WHERE id=?',(identifier(version),)).fetchone()
        if not row or row[7]!=account_id:
            raise DomainError('NOT_FOUND',404)
        if row[6]!='READY' and not (allow_staging and row[6]=='STAGING'):
            raise DomainError('ARTIFACT_NOT_READY',422)
        try:
            path = self._path(row[0])
            if path.is_symlink() or path.is_junction() or path.stat().st_size>MAX_SIZE+4124:
                raise ValueError()
            data = path.read_bytes()
            size = struct.unpack('>I',data[8:12])[0]
            if data[:8]!=MAGIC or not 0<size<=4096:
                raise ValueError()
            encoded = data[12:12+size]
            header = json.loads(encoded)
            nonce = base64.b64decode(header['nonce_b64'],validate=True)
            expected = {'format':1,'object_id':row[0],'version_id':version,'key_id':row[4],'nonce_b64':header['nonce_b64'],'plaintext_length':row[2],'media_type':row[1]}
            if header!=expected or canonical(header)!=encoded or len(nonce)!=12 or row[4]!=self.key_id:
                raise ValueError()
            wrap_aad = canonical({'format':1,'key_id':row[4],'object_id':row[0],'version_id':version})
            dek = AESGCM(self.wrap_key).decrypt(row[5][:12],row[5][12:],wrap_aad)
            plain = AESGCM(dek).decrypt(nonce,data[12+size:],data[:12+size])
            if len(plain)!=row[2] or hashlib.sha256(plain).hexdigest()!=row[3]:
                raise ValueError()
            return plain
        except (OSError,ValueError,KeyError,TypeError,struct.error,InvalidTag):
            raise DomainError('ARTIFACT_CORRUPT',422) from None

    def read(self,version,account_id):
        try:
            return self.domain.writer.call(lambda db:self.read_in_transaction(db,version,account_id),transaction=False)
        except DomainError as exc:
            if exc.code=='ARTIFACT_CORRUPT':
                self.domain.writer.call(lambda db:db.execute("UPDATE artifact_versions SET readiness='CORRUPT' WHERE id=?",(version,)))
            raise

    def recover(self):
        rows = self.domain.writer.call(lambda db:db.execute("SELECT id,account_id FROM artifact_versions WHERE readiness IN('STAGING','READY')").fetchall(),transaction=False)
        for version,account in rows:
            def inspect(db):
                try:
                    self.read_in_transaction(db,version,account,allow_staging=True)
                    state = 'READY'
                except DomainError:
                    state = 'CORRUPT'
                db.execute('UPDATE artifact_versions SET readiness=? WHERE id=?',(state,version))
            self.domain.writer.call(inspect)
