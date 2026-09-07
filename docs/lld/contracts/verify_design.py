"""Structural validation of design artifacts; no production/runtime qualification."""
import json
import pathlib
import sqlite3

ROOT = pathlib.Path(__file__).resolve().parent
checks = []

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)

def rejects(db, sql, name):
    try:
        db.execute(sql)
    except sqlite3.IntegrityError:
        checks.append(name)
    else:
        raise AssertionError(name)

db = sqlite3.connect(':memory:')
db.executescript((ROOT / 'schema-v1.sql').read_text(encoding='utf-8'))
check('business schema integrity', db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')
check('business foreign key integrity', not db.execute('PRAGMA foreign_key_check').fetchall())
db.execute("INSERT INTO accounts VALUES('a','linkedin','subject',1)")
db.execute("INSERT INTO content_versions VALUES('v','criteria','{}','hash','2026-09-07T00:00:00Z')")
db.execute("INSERT INTO tasks VALUES('t','a','v','v',1,'2026-09-07T00:00:00Z')")
db.execute("INSERT INTO runs VALUES('r','t',1,'QUEUED',0,0,1,NULL)")
rejects(db,"INSERT INTO runs VALUES('r2','t',2,'ACTIVE',0,0,1,NULL)",'one live run per task')
rejects(db,"UPDATE content_versions SET digest='changed' WHERE id='v'",'immutable content')
rejects(db,"INSERT INTO tasks VALUES('bad','missing','v','v',1,'now')",'orphan account rejected')
db.execute("INSERT INTO jobs VALUES('j','linkedin','123',NULL,'VERIFIED','v')")
rejects(db,"INSERT INTO jobs VALUES('j2','linkedin','123',NULL,'VERIFIED','v')",'duplicate external job rejected')
db.execute("INSERT INTO applications VALUES('app','a','j','PENDING',1)")
db.execute("INSERT INTO actions VALUES('x','submit','app','r','submit_application','v',NULL,NULL,NULL,NULL,'UNCERTAIN',1,1,'now')")
rejects(db,"INSERT INTO actions VALUES('y','submit2','app','r','submit_application','v',NULL,NULL,NULL,NULL,'CLAIMED',1,1,'now')",'uncertain submission guard index')
rejects(db,"INSERT INTO policies VALUES('p','a',1,'v','later',0,1,'UTC',1,NULL)",'zero standing action cap rejected')
db.execute("INSERT INTO facts VALUES('f','a','name',NULL)")
db.execute("INSERT INTO facts VALUES('f2','a','email',NULL)")
db.execute("INSERT INTO fact_versions VALUES('fv','f','v',NULL,'VERIFIED',NULL,'now')")
rejects(db,"UPDATE facts SET current_version='fv' WHERE id='f2'",'cross-fact version assignment rejected')
db.execute("UPDATE facts SET current_version='fv' WHERE id='f'")
rejects(db,"DELETE FROM fact_versions WHERE id='fv'",'current fact head protected from deletion')
check('post-fixture foreign key integrity',not db.execute('PRAGMA foreign_key_check').fetchall())
auth = sqlite3.connect(':memory:')
auth.executescript((ROOT / 'auth-schema-v1.sql').read_text(encoding='utf-8'))
check('auth schema integrity',auth.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')

schema = json.loads((ROOT / 'protocol-v1.schema.json').read_text(encoding='utf-8'))
openapi = json.loads((ROOT / 'openapi-v1.json').read_text(encoding='utf-8'))
def walk_refs(value):
    if isinstance(value,dict):
        if '$ref' in value:
            ref = value['$ref']
            if '#/$defs/' in ref:
                check('reference '+ref,ref.split('#/$defs/')[1] in schema['$defs'])
        for item in value.values():
            walk_refs(item)
    elif isinstance(value,list):
        for item in value:
            walk_refs(item)
walk_refs(schema)
walk_refs(openapi)
for name, definition in schema['$defs'].items():
    if definition.get('type') == 'object':
        check('required fields declared: '+name, set(definition.get('required',[])) <= set(definition.get('properties',{})))
        check('closed object contract: '+name, definition.get('additionalProperties') is False)
ops = [operation['operationId'] for path in openapi['paths'].values() for operation in path.values()]
check('unique operation IDs',len(ops)==len(set(ops)))
try:
    from jsonschema import Draft202012Validator, FormatChecker
    Draft202012Validator.check_schema(schema)
    checks.append('JSON Schema metaschema validation')
    command_schema = dict(schema)
    command_schema['$ref']='#/$defs/TaskCommand'
    validator=Draft202012Validator(command_schema,format_checker=FormatChecker())
    validator.validate({'command_id':'00000000-0000-4000-8000-000000000001','expected_revision':1,'operation':'pause'})
    check('invalid task command rejected',bool(list(validator.iter_errors({'command_id':'bad','expected_revision':0,'operation':'unsafe'}))))
except ImportError:
    checks.append('JSON Schema metaschema NOT RUN: jsonschema unavailable')

report={'scope':'Design structure only; not SQLCipher/browser/authentication qualification','checks':checks,'unique_checks':len(set(checks)),'business_tables':db.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0],'auth_tables':auth.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0],'contract_types':len(schema['$defs']),'core_api_operations':len(ops)}
(ROOT / 'validation-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
