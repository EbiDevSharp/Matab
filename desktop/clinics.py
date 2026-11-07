"""Clinic registry and isolated SQLite files; no process-global active clinic."""
import sqlite3,threading,uuid,re
from pathlib import Path
from contextlib import closing
from database import Database
class Clinics:
 def __init__(self,primary):
  self.primary=primary;self.path=primary.path.parent/'clinics.sqlite3';self.lock=threading.RLock();self.databases={'main':primary}
  with closing(sqlite3.connect(self.path)) as db:
   db.execute('CREATE TABLE IF NOT EXISTS clinics(id TEXT PRIMARY KEY,name TEXT NOT NULL)');db.execute('INSERT OR IGNORE INTO clinics VALUES(?,?)',('main','مطب من'));db.commit()
 def get(self,id):
  with self.lock,closing(sqlite3.connect(self.path)) as db:
   if not isinstance(id,str) or not db.execute('SELECT 1 FROM clinics WHERE id=?',(id,)).fetchone():raise ValueError('مطب انتخاب‌شده وجود ندارد.')
   if id not in self.databases:self.databases[id]=Database(self.primary.path.parent/('clinic-'+id+'.sqlite3'))
   return self.databases[id]
 def list(self):
  with self.lock,closing(sqlite3.connect(self.path)) as db:
   out=[]
   for id,name in db.execute('SELECT id,name FROM clinics ORDER BY rowid'):
    state=self.get(id).read()['state'];out.append({'id':id,'name':state['clinic'] if state else name})
   return {'clinics':out}
 def create(self,name):
  if not isinstance(name,str) or not name.strip() or len(name.strip())>80:raise ValueError('نام مطب باید بین ۱ تا ۸۰ حرف باشد.')
  name=name.strip()
  with self.lock,closing(sqlite3.connect(self.path)) as db:
   rows=self.list()['clinics']
   if len(rows)>=100:raise ValueError('حداکثر ۱۰۰ مطب قابل تعریف است.')
   if any(x['name'].strip().casefold()==name.casefold() for x in rows):raise ValueError('مطب هم‌نام وجود دارد.')
   id=uuid.uuid4().hex;db.execute('INSERT INTO clinics VALUES(?,?)',(id,name));db.commit();return {'id':id,'name':name}
 def backup_all(self):
  with self.lock:
   rows=[]
   for clinic in self.list()['clinics']:
    db=self.get(clinic['id']);state=db.read()['state'];payload=db.backup('full') if state else {'format':'matab-backup','formatVersion':1,'state':None,'history':db.history()['rows']}
    rows.append({'name':clinic['name'],'backup':payload})
   return {'format':'matab-all-clinics','formatVersion':1,'clinics':rows}
 def restore_all(self,payload):
  from database import validate
  import audit
  if not isinstance(payload,dict) or payload.get('format')!='matab-all-clinics' or payload.get('formatVersion')!=1 or not isinstance(payload.get('clinics'),list) or not 1<=len(payload['clinics'])<=100:raise ValueError('پشتیبان کلی معتبر نیست.')
  for item in payload['clinics']:
   if not isinstance(item.get('name'),str) or not 1<=len(item['name'].strip())<=80 or not isinstance(item.get('backup'),dict):raise ValueError('مشخصات مطب معتبر نیست.')
   b=item['backup']
   if b.get('format')!='matab-backup' or b.get('formatVersion')!=1:raise ValueError('بانک مطب معتبر نیست.')
   if b.get('state') is not None:validate(b['state'])
   audit.validate_import(b.get('history'))
  staged=[]
  with self.lock,closing(sqlite3.connect(self.path)) as registry:
   existing=self.list()['clinics']
   if len(existing)+len(payload['clinics'])>100:raise ValueError('بازیابی از سقف ۱۰۰ مطب عبور می‌کند.')
   names={r['name'].casefold() for r in existing}
   try:
    registry.execute('BEGIN IMMEDIATE')
    for item in payload['clinics']:
     name=item['name'].strip();i=1;base=name
     while name.casefold() in names:name=base[:55]+' (بازیابی '+str(i)+')';i+=1
     names.add(name.casefold());id=uuid.uuid4().hex;path=self.primary.path.parent/('clinic-'+id+'.sqlite3');staged.append((id,path));bank=Database(path);b=item['backup']
     if b.get('state') is not None:
      import copy
      state=copy.deepcopy(b['state']);state['clinic']=name;bank.write(0,state,'restore',b.get('history'))
     registry.execute('INSERT INTO clinics VALUES(?,?)',(id,name))
    registry.commit();return {'count':len(staged),'firstId':staged[0][0]}
   except Exception:
    registry.rollback()
    for id,path in staged:
     for suffix in ['','-wal','-shm']:
      try:Path(str(path)+suffix).unlink(missing_ok=True)
      except OSError:pass
    raise
 def backup_all_event(self,destination):
  with self.lock:
   for c in self.list()['clinics']:self.get(c['id']).backup_event('full',destination)
