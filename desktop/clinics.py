"""Clinic registry and isolated SQLite files; no process-global active clinic."""
import sqlite3,threading,uuid,re
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
