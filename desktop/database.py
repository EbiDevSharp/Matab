"""Transactional SQLite store for the local edition. No third-party packages."""
import datetime, json, math, sqlite3, threading, unicodedata, re
from contextlib import closing
from pathlib import Path
from finance import validate_finance
from profiles import validate_profiles
import audit
ROOT=Path(__file__).resolve().parent.parent
YEARS=json.loads((ROOT/'calendar-years.json').read_text('utf-8'))
KINDS=('services','products','areas','methods','doctors')
MAX_SAFE=9007199254740991

def norm(s):
    return ' '.join(unicodedata.normalize('NFKC',s).replace('ي','ی').replace('ك','ک').replace('\u200c',' ').replace('\u200d',' ').split()).lower()
def isint(n): return isinstance(n,int) and not isinstance(n,bool)
def date_ok(s):
    if not isinstance(s,str) or not re.fullmatch(r'1[34]\d\d/\d\d/\d\d|1500/\d\d/\d\d',s):return False
    y,m,d=map(int,s.split('/'))
    if not 1300<=y<=1500 or not 1<=m<=12:return False
    leap=(datetime.date.fromisoformat(YEARS[str(y+1)])-datetime.date.fromisoformat(YEARS[str(y)])).days==366
    return 1<=d<=(31 if m<=6 else 30 if m<12 or leap else 29)
def validate_base(v):
    def require(ok):
        if not ok:raise ValueError('اطلاعات معتبر نیست؛ فایل پشتیبان یا مقادیر فرم را بررسی کنید.')
    def text(s,n,required=False):return isinstance(s,str) and len(s)<=n and (not required or bool(s.strip()))
    def money(n):return isint(n) and 0<=n<=10**12
    require(isinstance(v,dict) and v.get('version')==3 and text(v.get('clinic'),80,True))
    cats=v.get('catalogs');require(isinstance(cats,dict));method_ids=set()
    for kind in KINDS:
        entries=cats.get(kind);require(isinstance(entries,list) and len(entries)<=1000);ids=set();names=set()
        for c in entries:
            require(isinstance(c,dict) and text(c.get('id'),100,True) and c['id']!='unknown' and c['id'] not in ids and text(c.get('name'),80,True) and norm(c['name']) not in names and type(c.get('active')) is bool)
            ids.add(c['id']);names.add(norm(c['name']))
        if kind=='methods':method_ids=ids
    records=v.get('records');require(isinstance(records,list) and len(records)<=100000);ids=set();total=0
    for r in records:
        require(isinstance(r,dict) and text(r.get('id'),100,True) and r['id'] not in ids and isint(r.get('created')) and r['created']>=0 and date_ok(r.get('date')) and money(r.get('price')) and money(r.get('amount')) and isinstance(r.get('volume'),(int,float)) and not isinstance(r['volume'],bool) and math.isfinite(r['volume']) and 0<r['volume']<=100000 and r.get('unit') in ('cc','unit','session'))
        ids.add(r['id']);total+=r['amount'];require(total<=MAX_SAFE)
        for k,n in {'patient':161,'service':80,'product':80,'area':80,'note':500}.items():require(text(r.get(k),n,k in ('service','area')))
        ps=r.get('payments');require(isinstance(ps,list) and len(ps)<=1000);payment_ids=set();paid=0
        for p in ps:
            require(isinstance(p,dict) and text(p.get('id'),120,True) and p['id'] not in payment_ids and money(p.get('amount')) and p['amount']>0 and text(p.get('note'),200) and text(p.get('methodLabel'),80,True) and type(p.get('legacy')) is bool and p.get('stage') in ('deposit','payment','settlement','legacy'))
            require((p.get('date') is None and p['legacy']) or date_ok(p.get('date')))
            require(p.get('method') in method_ids or (p['legacy'] and p.get('method')=='unknown'))
            require(p['legacy'] or (p['method']!='unknown' and p['stage']!='legacy'))
            payment_ids.add(p['id']);paid+=p['amount']
        require(paid<=r['amount'])
    require(v.get('lastBackup') is None or date_ok(v['lastBackup']))
    return v

def validate(v):
    if not isinstance(v,dict) or v.get('version')!=5:raise ValueError('نسخه اطلاعات معتبر نیست.')
    validate_base({**v,'version':3});validate_profiles(v);return validate_finance(v,date_ok)

class Conflict(Exception):pass
class Database:
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        with closing(self.connect()) as db:
            old=db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='records'").fetchone()
            if old and 'details_json' not in {r[1] for r in db.execute('PRAGMA table_info(records)')}:
                old_columns={r[1] for r in db.execute('PRAGMA table_info(records)')}
                backup=self.path.with_name('matab-before-v2.sqlite3.bak' if 'cost_reviewed' not in old_columns else 'matab-before-v3.sqlite3.bak')
                if not backup.exists():
                    with closing(sqlite3.connect(backup)) as target:db.backup(target)
            db.executescript((ROOT/'schema.sql').read_text('utf-8'))
            for table,column,definition in [('catalogs','fee_bps','INTEGER NOT NULL DEFAULT 0'),('records','cost_reviewed','INTEGER NOT NULL DEFAULT 0'),('records','divisor_milli','INTEGER NOT NULL DEFAULT 2000'),('payments','fee_bps','INTEGER'),('records','patient_id','TEXT REFERENCES patients(id)'),('records','details_json',"TEXT NOT NULL DEFAULT '{}'")]:
                if column not in {r[1] for r in db.execute('PRAGMA table_info('+table+')')}:db.execute('ALTER TABLE '+table+' ADD COLUMN '+column+' '+definition)
            db.commit();db.execute('PRAGMA journal_mode=WAL');audit.initialize(db)
    def connect(self):
        db=sqlite3.connect(self.path,timeout=15);db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON');return db
    def read(self):
        with self.lock,closing(self.connect()) as db:
            db.execute('BEGIN')
            meta=dict(db.execute('SELECT key,value FROM meta'));revision=int(meta['revision'])
            if 'clinic' not in meta:return {'revision':revision,'state':None}
            cats={k:[] for k in KINDS}
            for c in db.execute('SELECT * FROM catalogs ORDER BY sort_order'):cats[c['kind']].append({'id':c['id'],'name':c['name'],'active':bool(c['active']),**({'feeBps':c['fee_bps']} if c['kind']=='methods' else {})})
            records=[]
            for r in db.execute('SELECT * FROM records ORDER BY created'):
                item={k:r[k] for k in ('id','created','patient','service','product','area','volume','unit','price','amount','note')};item['date']=r['service_date'];ps=[]
                for p in db.execute('SELECT * FROM payments WHERE record_id=? ORDER BY sort_order',(r['id'],)):
                    ps.append({'id':p['id'],'amount':p['amount'],'date':p['payment_date'],'method':p['method'],'methodLabel':p['method_label'],'stage':p['stage'],'note':p['note'],'legacy':bool(p['legacy']),'feeBps':p['fee_bps']})
                if int(meta.get('stateVersion','3'))>=5:item.update(json.loads(r['details_json']));item['patientId']=r['patient_id']
                item['costReviewed']=bool(r['cost_reviewed']);item['divisorMilli']=r['divisor_milli'];item['consumptions']=[{'id':c['id'],'receiptId':c['receipt_id'],'quantityMilli':c['quantity_milli']} for c in db.execute('SELECT * FROM consumptions WHERE record_id=? ORDER BY sort_order',(r['id'],))];item['payments']=ps;item['paid']=sum(p['amount'] for p in ps);records.append(item)
            receipts=[]
            for r in db.execute('SELECT * FROM receipts ORDER BY created'):
                receipts.append(dict(zip(['id','created','date','productId','productLabel','quantityMilli','packUnit','contentsMilli','baseUnit','unitPrice','receivedMilli','totalCost','note'],[r[k] for k in ['id','created','receipt_date','product_id','product_label','quantity_milli','pack_unit','contents_milli','base_unit','unit_price','received_milli','total_cost','note']])))
            profiles={r['receipt_id']:r for r in db.execute('SELECT * FROM receipt_profiles')}
            for r in receipts:
                if r['id'] in profiles:r.update(doctorId=profiles[r['id']]['doctor_id'],doctorLabel=profiles[r['id']]['doctor_label'])
            return {'revision':revision,'state':{'version':int(meta.get('stateVersion','3')),'clinic':meta['clinic'],'catalogs':cats,'records':records,'receipts':receipts,'settings':json.loads(meta.get('financeSettings','{"divisorMilli":2000}')),'patients':[{'id':p['id'],'created':p['created'],'firstName':p['first_name'],'lastName':p['last_name'],'mobile':p['mobile'],'legacyName':p['legacy_name']} for p in db.execute('SELECT * FROM patients ORDER BY created,id')],'lastBackup':json.loads(meta.get('lastBackup','null'))}}

    def write(self,expected,state,operation='save',imported_history=None):
        validate(state)
        if operation not in ('save','restore','restore-settings'):raise ValueError('عملیات معتبر نیست.')
        audit.validate_import(imported_history)
        if imported_history and operation!='restore':raise ValueError('تاریخچه فقط در بازیابی کامل وارد می‌شود.')
        if not isint(expected) or expected<0:raise ValueError('نسخه اطلاعات معتبر نیست.')
        with self.lock,closing(self.connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            current=int(db.execute("SELECT value FROM meta WHERE key='revision'").fetchone()[0])
            if current!=expected:raise Conflict('اطلاعات در پنجره دیگری تغییر کرده؛ صفحه را دوباره باز کنید و تغییرات را تکرار کنید.')
            previous=self.read()['state']
            db.execute('DELETE FROM receipt_profiles');db.execute('DELETE FROM consumptions');db.execute('DELETE FROM receipts');db.execute('DELETE FROM payments');db.execute('DELETE FROM records');db.execute('DELETE FROM patients');db.execute('DELETE FROM catalogs')
            for kind in KINDS:
                db.executemany('INSERT INTO catalogs(kind,id,name,active,sort_order,fee_bps) VALUES(?,?,?,?,?,?)',[(kind,c['id'],c['name'],int(c['active']),i,c.get('feeBps',0)) for i,c in enumerate(state['catalogs'][kind])])
            db.executemany('INSERT INTO patients(id,created,first_name,last_name,mobile,legacy_name) VALUES(?,?,?,?,?,?)',[tuple(p[k] for k in ['id','created','firstName','lastName','mobile','legacyName']) for p in state['patients']])
            db.executemany('INSERT INTO receipts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',[tuple(r[k] for k in ['id','created','date','productId','productLabel','quantityMilli','packUnit','contentsMilli','baseUnit','unitPrice','receivedMilli','totalCost','note']) for r in state['receipts']])
            db.executemany('INSERT INTO receipt_profiles VALUES(?,?,?)',[(r['id'],r['doctorId'],r['doctorLabel']) for r in state['receipts'] if r.get('doctorId') is not None])
            for r in state['records']:
                db.execute('INSERT INTO records(id,created,service_date,patient,service,product,area,volume,unit,price,amount,note,cost_reviewed,divisor_milli,patient_id,details_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',tuple(r[k] for k in ('id','created','date','patient','service','product','area','volume','unit','price','amount','note'))+(int(r['costReviewed']),r['divisorMilli'],r['patientId'],json.dumps({k:r[k] for k in ['firstName','lastName','mobile','legacyName','doctorId','doctorLabel','shareMode','doctorBps']},ensure_ascii=False)))
                db.executemany('INSERT INTO payments(record_id,id,amount,payment_date,method,method_label,stage,note,legacy,sort_order,fee_bps) VALUES(?,?,?,?,?,?,?,?,?,?,?)',[(r['id'],p['id'],p['amount'],p['date'],p['method'],p['methodLabel'],p['stage'],p['note'],int(p['legacy']),i,p['feeBps']) for i,p in enumerate(r['payments'])])
                db.executemany('INSERT INTO consumptions VALUES(?,?,?,?,?)',[(r['id'],c['id'],c['receiptId'],c['quantityMilli'],i) for i,c in enumerate(r['consumptions'])])
            db.executemany('INSERT OR REPLACE INTO meta VALUES(?,?)',[('stateVersion','5'),('financeSettings',json.dumps(state['settings'])),('clinic',state['clinic']),('lastBackup',json.dumps(state.get('lastBackup'))),('revision',str(current+1))])
            audit.import_rows(db,imported_history);audit.record_changes(db,previous,state,operation)
            db.commit();return {'revision':current+1}

    def history(self,filters=None):
        with self.lock,closing(self.connect()) as db:return audit.history(db,filters)
    def releases(self):
        with self.lock,closing(self.connect()) as db:return audit.release_history(db)
    def backup(self,scope='full'):
        if scope not in ('full','settings'):raise ValueError('نوع پشتیبان معتبر نیست.')
        with self.lock,closing(self.connect()) as db:
            state=self.read()['state']
            if state is None:raise ValueError('بانک اطلاعات هنوز ایجاد نشده است.')
            if scope=='settings':return {'format':'matab-settings','formatVersion':1,'clinic':state['clinic'],'settings':state['settings'],'catalogs':state['catalogs']}
            return {'format':'matab-backup','formatVersion':1,'state':state,'history':audit.history(db,all_rows=True)['rows'],'releases':audit.release_history(db)['releases']}
    def backup_event(self,scope,destination):
        if scope not in ('full','settings') or destination not in ('local','drive'):raise ValueError('رویداد معتبر نیست.')
        with self.lock,closing(self.connect()) as db:
            audit.add(db,'export','backup','آماده‌سازی یا ذخیره فایل پشتیبان '+('کامل' if scope=='full' else 'تنظیمات'),details={'scope':scope,'destination':destination});db.commit()
