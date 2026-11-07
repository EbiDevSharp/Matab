"""One SQLite file, clinic-scoped state and history, shared reference catalogs."""
import copy,json,sqlite3,threading,uuid
from pathlib import Path
from contextlib import closing
from database import Database,Conflict,validate,norm
import audit
COMMON=('services','products','areas','methods')
class Clinics:
 def __init__(self,primary):
  self.primary=primary;legacy_path=primary.path if isinstance(primary,Database) else Path(primary)
  self.path=legacy_path.parent/'matab-unified.sqlite3';self.lock=threading.RLock()
  with closing(self.connect()) as db:
   db.executescript('''CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS clinics(id TEXT PRIMARY KEY,name TEXT NOT NULL,state_json TEXT,revision INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS shared_catalogs(kind TEXT NOT NULL,id TEXT NOT NULL,entry_json TEXT NOT NULL,position INTEGER NOT NULL,PRIMARY KEY(kind,id));
CREATE TABLE IF NOT EXISTS activity_log(id INTEGER PRIMARY KEY AUTOINCREMENT,occurred_at TEXT NOT NULL,local_day TEXT NOT NULL,action TEXT NOT NULL,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,label TEXT NOT NULL,details_json TEXT NOT NULL,imported INTEGER NOT NULL DEFAULT 0,source_key TEXT,clinic_id TEXT NOT NULL DEFAULT 'main',UNIQUE(clinic_id,source_key));
CREATE INDEX IF NOT EXISTS idx_clinic_log ON activity_log(clinic_id,id);''');audit.initialize(db)
   if not db.execute("SELECT 1 FROM meta WHERE key='unifiedMigrated'").fetchone():
    from legacy_clinics import Clinics as Legacy
    legacy=Legacy(primary if isinstance(primary,Database) else Database(legacy_path))
    db.execute('BEGIN IMMEDIATE')
    try:
     for clinic in legacy.list()['clinics']:
      bank=legacy.get(clinic['id']);r=bank.read();state=r['state']
      if state is not None:
       state=self.merge(db,state,'migrate')
       if state.get('version')==5:validate(state)
      db.execute('INSERT INTO clinics VALUES(?,?,?,?)',(clinic['id'],clinic['name'],self.encode(state) if state is not None else None,r['revision']))
      with closing(bank.connect()) as old:
       for event in audit.history(old,all_rows=True)['rows']:self.import_event(db,clinic['id'],event,event['imported'])
     db.execute('INSERT INTO meta VALUES(?,?)',('unifiedMigrated','1'));db.commit()
    except Exception:db.rollback();raise
 def connect(self):
  db=sqlite3.connect(self.path,timeout=30);db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');return db
 @staticmethod
 def encode(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))
 def common(self,db):
  out={k:[] for k in COMMON}
  for row in db.execute('SELECT * FROM shared_catalogs ORDER BY kind,position'):out[row['kind']].append(json.loads(row['entry_json']))
  return out
 def state(self,db,id):
  row=db.execute('SELECT * FROM clinics WHERE id=?',(id,)).fetchone()
  if row is None:raise ValueError('مطب انتخاب‌شده وجود ندارد.')
  state=json.loads(row['state_json']) if row['state_json'] is not None else None
  if state is not None:state['catalogs'].update(self.common(db))
  return row,state
 def merge(self,db,value,mode):
  s=copy.deepcopy(value);common=self.common(db);maps={}
  for kind in COMMON:
   maps[kind]={};items=common[kind]
   for incoming in s['catalogs'].get(kind,[]):
    by_id=next((r for r in items if r['id']==incoming['id']),None);by_name=next((r for r in items if norm(r['name'])==norm(incoming['name'])),None)
    if mode=='save':
     if by_id and by_name and by_id['id']!=by_name['id']:raise ValueError('گزینه مشترک هم‌نام وجود دارد.')
     target=by_id or by_name
    else:target=by_name
    if target:
     id=target['id']
     if mode=='save':target.update(incoming);target['id']=id
     elif mode=='migrate':target['active']=target['active'] or incoming['active']
    else:
     id=incoming['id'] if by_id is None else kind+'-'+uuid.uuid4().hex
     items.append({**incoming,'id':id})
    maps[kind][incoming['id']]=id
   if len(items)>1000:raise ValueError('تعداد گزینه‌های مشترک از سقف مجاز بیشتر است.')
   s['catalogs'][kind]=copy.deepcopy(items)
  for receipt in s.get('receipts',[]):receipt['productId']=maps['products'].get(receipt['productId'],receipt['productId'])
  for record in s.get('records',[]):
   for p in record.get('payments',[]):p['method']=maps['methods'].get(p['method'],p['method'])
  db.execute('DELETE FROM shared_catalogs')
  for kind,items in common.items():db.executemany('INSERT INTO shared_catalogs VALUES(?,?,?,?)',[(kind,c['id'],self.encode(c),i) for i,c in enumerate(items)])
  return s
 def import_event(self,db,id,r,imported=True):audit.add(db,r['action'],r['entityType'],r['label'],r['entityId'],r['details'],r['timestamp'],imported,r['sourceKey'],id)
 def get(self,id):
  with self.lock,closing(self.connect()) as db:self.state(db,id)
  return Bank(self,id)
 def list(self):
  with self.lock,closing(self.connect()) as db:return {'clinics':[{'id':r['id'],'name':r['name']} for r in db.execute('SELECT id,name FROM clinics ORDER BY rowid')]}
 def create(self,name):
  if not isinstance(name,str) or not 1<=len(name.strip())<=80:raise ValueError('نام مطب باید بین ۱ تا ۸۰ حرف باشد.')
  with self.lock,closing(self.connect()) as db:
   db.execute('BEGIN IMMEDIATE');rows=list(db.execute('SELECT name FROM clinics'))
   if len(rows)>=100:raise ValueError('حداکثر ۱۰۰ مطب قابل تعریف است.')
   if any(norm(r['name'])==norm(name) for r in rows):raise ValueError('مطب هم‌نام وجود دارد.')
   id=uuid.uuid4().hex;db.execute('INSERT INTO clinics(id,name) VALUES(?,?)',(id,name.strip()));db.commit();return {'id':id,'name':name.strip()}
 def backup_all(self):
  with self.lock,closing(self.connect()) as db:
   db.execute('BEGIN');rows=[]
   for clinic in db.execute('SELECT id,name FROM clinics ORDER BY rowid').fetchall():rows.append({'name':clinic['name'],'backup':self.envelope(db,clinic['id'],'full')})
   return {'format':'matab-all-clinics','formatVersion':1,'clinics':rows}
 def envelope(self,db,id,scope):
  row,s=self.state(db,id)
  if scope=='settings':
   if s is None:raise ValueError('ابتدا مطب را باز کنید.')
   return {'format':'matab-settings','formatVersion':1,**{k:s[k] for k in ('clinic','settings','catalogs')}}
  if scope!='full':raise ValueError('نوع پشتیبان معتبر نیست.')
  return {'format':'matab-backup','formatVersion':1,'state':s,'history':audit.history(db,all_rows=True,clinic_id=id)['rows'],'releases':audit.release_history(db)['releases']}
 def restore_all(self,payload):
  if not isinstance(payload,dict) or payload.get('format')!='matab-all-clinics' or payload.get('formatVersion')!=1 or not isinstance(payload.get('clinics'),list) or not 1<=len(payload['clinics'])<=100:raise ValueError('پشتیبان کلی معتبر نیست.')
  for item in payload['clinics']:
   if not isinstance(item.get('name'),str) or not 1<=len(item['name'].strip())<=80 or not isinstance(item.get('backup'),dict):raise ValueError('مشخصات مطب معتبر نیست.')
   b=item['backup']
   if b.get('format')!='matab-backup' or b.get('formatVersion')!=1:raise ValueError('بانک مطب معتبر نیست.')
   if b.get('state') is not None:validate(b['state'])
   audit.validate_import(b.get('history'))
  with self.lock,closing(self.connect()) as db:
   db.execute('BEGIN IMMEDIATE');existing=list(db.execute('SELECT name FROM clinics'));names={norm(r['name']) for r in existing};before=self.common(db)
   if len(existing)+len(payload['clinics'])>100:raise ValueError('بازیابی از سقف ۱۰۰ مطب عبور می‌کند.')
   first=None
   for item in payload['clinics']:
    name=item['name'].strip();i=1
    while norm(name) in names:name=item['name'][:55]+' (بازیابی '+str(i)+')';i+=1
    names.add(norm(name));id=uuid.uuid4().hex;first=first or id;b=item['backup'];s=self.merge(db,b['state'],'restore') if b.get('state') is not None else None
    if s is not None:s['clinic']=name;validate(s)
    db.execute('INSERT INTO clinics VALUES(?,?,?,1)',(id,name,self.encode(s) if s is not None else None))
    for event in b.get('history') or []:self.import_event(db,id,event)
    if s is not None:audit.record_changes(db,None,s,'restore',id)
   if self.common(db)!=before:db.execute('UPDATE clinics SET revision=revision+1')
   db.commit();return {'count':len(payload['clinics']),'firstId':first}
 def backup_all_event(self,destination):
  with self.lock,closing(self.connect()) as db:
   if destination not in ('local','drive'):raise ValueError('مقصد معتبر نیست.')
   for c in db.execute('SELECT id FROM clinics').fetchall():audit.add(db,'export','backup','پشتیبان کلی همه مطب‌ها',details={'scope':'all','destination':destination},clinic_id=c['id'])
   db.commit()
class Bank:
 def __init__(self,owner,id):self.owner=owner;self.id=id;self.path=owner.path
 def read(self):
  with self.owner.lock,closing(self.owner.connect()) as db:
   db.execute('BEGIN');row,s=self.owner.state(db,self.id);return {'revision':row['revision'],'state':s,'sharedCatalogs':self.owner.common(db)}
 def write(self,expected,state,operation='save',imported_history=None):
  validate(state);audit.validate_import(imported_history)
  if operation not in ('save','restore','restore-settings') or (imported_history and operation!='restore'):raise ValueError('عملیات معتبر نیست.')
  with self.owner.lock,closing(self.owner.connect()) as db:
   db.execute('BEGIN IMMEDIATE');row,old=self.owner.state(db,self.id)
   if type(expected) is not int or row['revision']!=expected:raise Conflict('اطلاعات یا فهرست مشترک تغییر کرده؛ صفحه را دوباره باز کنید.')
   before=self.owner.common(db);s=self.owner.merge(db,state,'save' if operation=='save' else 'restore');validate(s)
   if before!=self.owner.common(db):db.execute('UPDATE clinics SET revision=revision+1')
   else:db.execute('UPDATE clinics SET revision=revision+1 WHERE id=?',(self.id,))
   db.execute('UPDATE clinics SET name=?,state_json=? WHERE id=?',(s['clinic'],self.owner.encode(s),self.id))
   for event in imported_history or []:self.owner.import_event(db,self.id,event)
   audit.record_changes(db,old,s,operation,self.id);revision=db.execute('SELECT revision FROM clinics WHERE id=?',(self.id,)).fetchone()[0];db.commit();return {'revision':revision,'state':s}
 def history(self,filters=None):
  with self.owner.lock,closing(self.owner.connect()) as db:return audit.history(db,filters,clinic_id=self.id)
 def releases(self):
  with closing(self.owner.connect()) as db:return audit.release_history(db)
 def backup(self,scope='full'):
  with self.owner.lock,closing(self.owner.connect()) as db:db.execute('BEGIN');return self.owner.envelope(db,self.id,scope)
 def backup_event(self,scope,destination):
  if scope not in ('full','settings') or destination not in ('local','drive'):raise ValueError('رویداد معتبر نیست.')
  with self.owner.lock,closing(self.owner.connect()) as db:audit.add(db,'export','backup','فایل پشتیبان '+scope,details={'scope':scope,'destination':destination},clinic_id=self.id);db.commit()
