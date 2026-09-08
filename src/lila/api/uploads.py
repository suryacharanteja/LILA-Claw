"""Incremental multipart parsing, bounded memory, no plaintext spool files."""
import asyncio
import re
from python_multipart import MultipartParser
from python_multipart.multipart import parse_options_header
from python_multipart.exceptions import MultipartParseError,FormParserError
from lila.domain.artifacts import MAX_SIZE,MEDIA
from lila.domain.core import DomainError


class UploadParser:
    def __init__(self,content_type,max_size=MAX_SIZE):
        kind,options = parse_options_header(content_type)
        boundary = options.get(b'boundary',b'')
        if kind!=b'multipart/form-data' or not re.fullmatch(rb"[0-9A-Za-z'()+_,./:=?-]{1,70}",boundary):
            raise DomainError('INVALID_MULTIPART',422)
        self.max_size,self.boundary = max_size,boundary
        self.parts,self.current,self.headers = {},bytearray(),{}
        self.field,self.value = bytearray(),bytearray()
        self.name,self.filename,self.media_type = None,None,None
        self.total,self.count,self.done,self.tail = 0,0,False,b''
        self.parser = MultipartParser(boundary,callbacks={
            'on_part_begin':self.begin,'on_header_field':self.header_field,'on_header_value':self.header_value,
            'on_header_end':self.header_end,'on_headers_finished':self.headers_finished,
            'on_part_data':self.data,'on_part_end':self.end,'on_end':self.finish,
        },max_size=max_size+65536,max_header_count=8,max_header_size=8192)

    def begin(self):
        self.count+=1
        if self.count>4:
            raise DomainError('INVALID_MULTIPART',422)
        self.current,self.headers = bytearray(),{}

    def header_field(self,data,start,end):
        self.field.extend(data[start:end])

    def header_value(self,data,start,end):
        self.value.extend(data[start:end])

    def header_end(self):
        name = bytes(self.field).lower()
        if name in self.headers or name not in {b'content-disposition',b'content-type'}:
            raise DomainError('INVALID_MULTIPART',422)
        self.headers[name] = bytes(self.value)
        self.field.clear()
        self.value.clear()

    def headers_finished(self):
        kind,options = parse_options_header(self.headers.get(b'content-disposition',b''))
        self.name = options.get(b'name')
        if kind!=b'form-data' or self.name not in {b'file',b'command_id',b'account_id',b'filename'} or self.name in self.parts:
            raise DomainError('INVALID_MULTIPART',422)
        if self.name==b'file':
            self.filename = options.get(b'filename',b'').decode('utf-8')
            self.media_type = self.headers.get(b'content-type',b'').decode('ascii')
            if not self.filename or self.media_type not in MEDIA:
                raise DomainError('INVALID_ARTIFACT',422)
        elif b'filename' in options:
            raise DomainError('INVALID_MULTIPART',422)

    def data(self,data,start,end):
        limit = self.max_size if self.name==b'file' else 1024
        if len(self.current)+end-start>limit:
            raise DomainError('PAYLOAD_TOO_LARGE',413)
        self.current.extend(data[start:end])

    def end(self):
        self.parts[self.name] = bytes(self.current)
        self.current.clear()

    def finish(self):
        self.done = True

    def write(self,chunk):
        self.total+=len(chunk)
        if self.total>self.max_size+65536:
            raise DomainError('PAYLOAD_TOO_LARGE',413)
        self.tail = (self.tail+chunk)[-256:]
        try:
            self.parser.write(chunk)
        except (MultipartParseError,FormParserError,UnicodeError,ValueError):
            raise DomainError('INVALID_MULTIPART',422) from None

    def result(self):
        self.parser.finalize()
        if not self.done or not self.tail.rstrip(b'\r\n').endswith(b'--'+self.boundary+b'--') or not {b'file',b'command_id',b'account_id'}.issubset(self.parts):
            raise DomainError('INVALID_MULTIPART',422)
        try:
            filename = self.parts.get(b'filename',self.filename.encode()).decode('utf-8')
            if filename!=self.filename:
                raise ValueError()
            return {'command_id':self.parts[b'command_id'].decode('ascii'),'account_id':self.parts[b'account_id'].decode('ascii'),'filename':filename,'data':self.parts[b'file'],'media_type':self.media_type}
        except (UnicodeError,ValueError):
            raise DomainError('INVALID_MULTIPART',422) from None


async def read_upload(request):
    parser = UploadParser(request.headers.get('content-type',''))
    try:
        async with asyncio.timeout(60):
            async for chunk in request.stream():
                parser.write(chunk)
    except TimeoutError:
        raise DomainError('UPLOAD_TIMEOUT',408) from None
    return parser.result()
