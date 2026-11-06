"""Append-only local activity history, release notes and portable backup envelopes."""
import datetime,json,uuid
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent.parent
with (ROOT/'timezone-Tehran.tzif').open('rb') as f:TEHRAN=ZoneInfo.from_file(f,key='Asia/Tehran')
ACTIONS=('add','update','delete','restore','export','migrate','install')
TYPES=('service','payment','material_receipt','material_use','customer','doctor','service_type','product','area','payment_method','settings','appearance','application','backup')
SCHEMA='''CREATE TABLE IF NOT EXISTS activity_log(id INTEGER PRIMARY KEY AUTOINCREMENT,occurred_at TEXT NOT NULL,local_day TEXT NOT NULL,action TEXT NOT NULL,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,label TEXT NOT NULL,details_json TEXT NOT NULL,imported INTEGER NOT NULL DEFAULT 0,source_key TEXT UNIQUE);
CREATE INDEX IF NOT EXISTS idx_log_day ON activity_log(local_day,id);
CREATE INDEX IF NOT EXISTS idx_log_action ON activity_log(action,entity_type,id);
CREATE TABLE IF NOT EXISTS app_releases(version_code INTEGER PRIMARY KEY,version_name TEXT NOT NULL,release_date TEXT NOT NULL,changes_json TEXT NOT NULL);'''
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def local_day(timestamp):return datetime.datetime.fromisoformat(timestamp.replace('Z','+00:00')).astimezone(TEHRAN).date().isoformat()
def add(db,action,kind,label,entity_id='',details=None,stamp=None,imported=False,source=None):
    stamp=stamp or now()
    if source is None:
        instance=db.execute("SELECT value FROM meta WHERE key='instanceId'").fetchone()[0];source=instance+':'+str(uuid.uuid4())
    db.execute('INSERT OR IGNORE INTO activity_log(occurred_at,local_day,action,entity_type,entity_id,label,details_json,imported,source_key) VALUES(?,?,?,?,?,?,?,?,?)',(stamp,local_day(stamp),action,kind,str(entity_id),str(label)[:320],json.dumps(details or {},ensure_ascii=False),int(imported),source))
def initialize(db):
    db.executescript(SCHEMA)
    row=db.execute("SELECT value FROM meta WHERE key='instanceId'").fetchone()
    if not row:db.execute('INSERT INTO meta VALUES(?,?)',('instanceId',str(uuid.uuid4())))
    package=json.loads((ROOT/'releases.json').read_text('utf-8'))
    for r in package['releases']:db.execute('INSERT OR IGNORE INTO app_releases VALUES(?,?,?,?)',(r['versionCode'],r['versionName'],r['date'],json.dumps(r['changes'],ensure_ascii=False)))
    current=str(package['current']['versionCode']);old=db.execute("SELECT value FROM meta WHERE key='installedVersionCode'").fetchone()
    if not old or old[0]!=current:
        installed=db.execute("SELECT value FROM meta WHERE key='clinic'").fetchone() is not None
        add(db,'update' if installed else 'install','application','نسخه '+package['current']['versionName'],details={'version':package['current']['versionName']})
        db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',('installedVersionCode',current))
    db.commit()
def release_history(db):
    package=json.loads((ROOT/'releases.json').read_text('utf-8'))
    return {'current':package['current'],'releases':[{'versionCode':r['version_code'],'versionName':r['version_name'],'date':r['release_date'],'changes':json.loads(r['changes_json'])} for r in db.execute('SELECT * FROM app_releases ORDER BY version_code DESC')]}
def log_json(db,row):
    instance=db.execute("SELECT value FROM meta WHERE key='instanceId'").fetchone()[0]
    return {'id':row['id'],'timestamp':row['occurred_at'],'action':row['action'],'entityType':row['entity_type'],'entityId':row['entity_id'],'label':row['label'],'details':json.loads(row['details_json']),'imported':bool(row['imported']),'sourceKey':row['source_key'] or instance+':'+str(row['id'])}
def history(db,filters=None,all_rows=False):
    f=filters or {};clauses=[];args=[]
    for key,column,allowed in [('action','action',ACTIONS),('entityType','entity_type',TYPES)]:
        value=f.get(key,'')
        if value:
            if value not in allowed:raise ValueError('فیلتر عملیات معتبر نیست.')
            clauses.append(column+'=?');args.append(value)
    for key,operator in [('from','>='),('to','<=')]:
        value=f.get(key,'')
        if value:
            datetime.date.fromisoformat(value);clauses.append('local_day'+operator+'?');args.append(value)
            clock=f.get(key+'Time','')
            if clock:
                if not __import__('re').fullmatch(r'[0-2][0-9]:[0-5][0-9]',clock):raise ValueError('ساعت معتبر نیست.')
                hour,minute=map(int,clock.split(':'))
                if hour>23:raise ValueError('ساعت معتبر نیست.')
                point=datetime.datetime.fromisoformat(value+'T'+clock+(':00' if key=='from' else ':59.999999')).replace(tzinfo=TEHRAN).astimezone(datetime.timezone.utc)
                clauses.append('julianday(occurred_at)'+operator+'julianday(?)');args.append(point.isoformat())
        elif f.get(key+'Time'):raise ValueError('برای ساعت، تاریخ لازم است.')
    if f.get('q'):clauses.append('(label LIKE ? OR entity_id LIKE ?)');args.extend(['%'+str(f['q'])[:100]+'%']*2)
    where=' WHERE '+' AND '.join(clauses) if clauses else '';total=db.execute('SELECT count(*) FROM activity_log'+where,args).fetchone()[0]
    limit=min(100,max(1,int(f.get('limit',50))));offset=max(0,int(f.get('offset',0)))
    sql='SELECT * FROM activity_log'+where+' ORDER BY id DESC'
    rows=db.execute(sql if all_rows else sql+' LIMIT ? OFFSET ?',args if all_rows else args+[limit,offset])
    return {'total':total,'rows':[log_json(db,r) for r in rows]}
def validate_import(rows):
    if rows is None:return
    if not isinstance(rows,list) or len(rows)>100000:raise ValueError('تاریخچه پشتیبان معتبر نیست.')
    for r in rows:
        if not isinstance(r,dict) or r.get('action') not in ACTIONS or r.get('entityType') not in TYPES:raise ValueError('تاریخچه پشتیبان معتبر نیست.')
        for k,n in [('timestamp',40),('entityId',250),('label',320),('sourceKey',200)]:
            if not isinstance(r.get(k),str) or len(r[k])>n:raise ValueError('تاریخچه پشتیبان معتبر نیست.')
        dt=datetime.datetime.fromisoformat(r['timestamp'].replace('Z','+00:00'))
        if dt.tzinfo is None or not isinstance(r.get('details'),dict) or len(json.dumps(r['details'],ensure_ascii=False))>5000:raise ValueError('تاریخچه پشتیبان معتبر نیست.')
def import_rows(db,rows):
    for r in rows or []:add(db,r['action'],r['entityType'],r['label'],r['entityId'],r['details'],r['timestamp'],True,r['sourceKey'])
def collections(s):
    out={}
    def put(kind,id,row,label):out[(kind,str(id))]=(row,str(label))
    for p in s['patients']:put('customer',p['id'],p,' '.join([p['firstName'],p['lastName']]).strip() or p['legacyName'] or 'مشتری بدون نام')
    names={'services':'service_type','products':'product','areas':'area','methods':'payment_method','doctors':'doctor'}
    for kind,items in s['catalogs'].items():
        for c in items:put(names[kind],c['id'],c,c['name'])
    for r in s['records']:
        put('service',r['id'],r,r['service']+' · '+(r['patient'] or 'بدون نام'))
        for p in r['payments']:put('payment',r['id']+'/'+p['id'],p,p['methodLabel']+' · '+r['service'])
        for c in r['consumptions']:put('material_use',r['id']+'/'+c['id'],c,'مصرف ماده · '+r['service'])
    for r in s['receipts']:put('material_receipt',r['id'],r,r['productLabel'])
    return out
def record_changes(db,old,new,operation):
    if operation in ('restore','restore-settings'):
        add(db,'restore','backup','بازیابی '+('تنظیمات' if operation=='restore-settings' else 'بانک کامل'),details={'services':len(new['records']),'receipts':len(new['receipts'])});return
    if old is None:add(db,'add','settings','ایجاد بانک اطلاعات');return
    if old.get('version',0)<5:add(db,'migrate','application','به‌روزرسانی ساختار اطلاعات با حفظ سوابق');return
    before,after=collections(old),collections(new)
    for key in before.keys()|after.keys():
        a=before.get(key);b=after.get(key)
        if a and b and a[0]==b[0]:continue
        fields=[k for k in set(a[0] if a else {})|set(b[0] if b else {}) if (a[0] if a else {}).get(k)!=(b[0] if b else {}).get(k)]
        add(db,'update' if a and b else 'add' if b else 'delete',key[0],(b or a)[1],key[1],{'fields':sorted(fields)[:40]})
    if old['clinic']!=new['clinic']:add(db,'update','settings','تغییر نام مطب',details={'fields':['clinic']})
    if old['settings']!=new['settings']:
        keys=[k for k in set(old['settings'])|set(new['settings']) if old['settings'].get(k)!=new['settings'].get(k)]
        add(db,'update','appearance' if keys==['appearance'] else 'settings','تغییر تنظیمات برنامه',details={'fields':keys})
