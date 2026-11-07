import copy,json,sqlite3,sys,tempfile,unittest
from contextlib import closing
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from database import Database,Conflict,validate
import audit
FIXTURE=json.loads((Path(__file__).parent/'profiles-fixture.json').read_text('utf-8'))
class HistoryTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.db=Database(Path(self.temp.name)/'test.sqlite3');self.db.write(0,FIXTURE)
 def tearDown(self):self.temp.cleanup()
 def test_release_seed_once_and_noop_write(self):
  initial=self.db.history()['total'];self.assertEqual(len(self.db.releases()['releases']),6);self.assertEqual(self.db.releases()['current']['versionName'],'1.3.0');self.db.write(1,FIXTURE);self.assertEqual(self.db.history()['total'],initial);again=Database(self.db.path);self.assertEqual(again.history()['total'],initial)
 def test_changed_fields_and_crud(self):
  next=copy.deepcopy(FIXTURE);next['records'][0]['note']='اصلاح آزمایشی';self.db.write(1,next);rows=self.db.history({'entityType':'service','action':'update'})['rows'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['details']['fields'],['note']);next['records']=[];self.db.write(2,next);self.assertEqual(self.db.history({'action':'delete','entityType':'service'})['total'],2);self.assertGreater(self.db.history({'action':'delete','entityType':'payment'})['total'],0)
 def test_restore_keeps_current_and_deduplicates_history(self):
  backup=self.db.backup();self.assertEqual(backup['state'],FIXTURE);before=self.db.history()['total'];self.db.write(1,FIXTURE,'restore',backup['history']);self.assertEqual(self.db.history()['total'],before+1);self.db.write(2,FIXTURE,'restore',backup['history']);self.assertEqual(self.db.history()['total'],before+2)
  other=Database(Path(self.temp.name)/'other.sqlite3');other.write(0,FIXTURE,'restore',backup['history']);rows=other.history()['rows'];self.assertEqual(sum(r['imported'] for r in rows),len(backup['history']))
 def test_bad_restore_and_stale_writer_are_atomic(self):
  before=self.db.history()['total'];bad=[{'action':'hack'}]
  with self.assertRaises(ValueError):self.db.write(1,FIXTURE,'restore',bad)
  with self.assertRaises(Conflict):self.db.write(0,FIXTURE)
  self.assertEqual(self.db.history()['total'],before);self.assertEqual(self.db.read()['revision'],1)
 def test_filters_date_time_and_paging(self):
  with closing(self.db.connect()) as db:
   audit.add(db,'add','service','صبح آزمایشی','am',stamp='2026-11-05T05:29:59.000Z');audit.add(db,'add','service','ظهر آزمایشی','pm',stamp='2026-11-05T05:30:00.000Z');audit.add(db,'delete','service','عصر آزمایشی','end',stamp='2026-11-05T15:30:00.000Z');db.commit()
  f={'from':'2026-11-05','to':'2026-11-05','fromTime':'09:00','toTime':'18:59','entityType':'service'};rows=self.db.history(f)['rows'];self.assertEqual([r['entityId'] for r in rows],['pm']);self.assertEqual(self.db.history({'q':'آزمایشی','action':'delete'})['total'],1);self.assertEqual(len(self.db.history({'limit':1,'offset':1})['rows']),1)
  with self.assertRaises(ValueError):self.db.history({'fromTime':'09:00'})
 def test_settings_backup_omits_patient_data_and_export_logged(self):
  settings=self.db.backup('settings');self.assertEqual(set(settings),{'format','formatVersion','clinic','settings','catalogs'});self.db.backup_event('settings','drive');self.assertEqual(self.db.history({'action':'export'})['rows'][0]['details'],{'scope':'settings','destination':'drive'})
 def test_profile_guards_and_negative_share(self):
  for value in ['0912345678','08123456789','091234567890']:
   bad=copy.deepcopy(FIXTURE);bad['patients'][0]['mobile']=value
   with self.assertRaises(ValueError):validate(bad)
  with sqlite3.connect(self.db.path) as db:self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
 def test_upgrade_v11_preserves_finance_before_profile_migration(self):
  source=self.db.path;legacy=Path(self.temp.name)/'v11.sqlite3'
  with closing(sqlite3.connect(legacy)) as old,closing(sqlite3.connect(source)) as current:
   old.executescript((Path(__file__).parent/'legacy_v2_schema.sql').read_text('utf-8'))
   for table in ['catalogs','receipts','records','payments','consumptions']:
    cols=[r[1] for r in old.execute('PRAGMA table_info('+table+')')];rows=current.execute('SELECT '+','.join(cols)+' FROM '+table).fetchall();old.executemany('INSERT INTO '+table+' VALUES('+','.join('?' for _ in cols)+')',rows)
   old.executemany('INSERT OR REPLACE INTO meta VALUES(?,?)',[('clinic','مطب قبلی'),('revision','7'),('stateVersion','4'),('financeSettings','{"divisorMilli":2000}')]);old.commit()
  upgraded=Database(legacy);before=upgraded.read();self.assertEqual(before['revision'],7);self.assertEqual(before['state']['version'],4);self.assertEqual(before['state']['records'][0]['payments'][0]['feeBps'],1320);self.assertEqual(len(before['state']['receipts']),2);self.assertTrue((Path(self.temp.name)/'matab-before-v3.sqlite3.bak').exists());upgraded.write(7,FIXTURE);self.assertEqual(upgraded.read()['state'],FIXTURE);self.assertEqual(upgraded.history({'action':'migrate'})['total'],1)
 def test_doctor_owned_material_roundtrip_and_guard(self):
  state=copy.deepcopy(FIXTURE);state['receipts'][0].update(doctorId='doc1',doctorLabel='پزشک آزمایشی');self.db.write(1,state);self.assertEqual(self.db.read()['state']['receipts'][0]['doctorId'],'doc1')
  wrong=copy.deepcopy(state);wrong['records'][0]['doctorId']=None;wrong['records'][0]['doctorLabel']=''
  with self.assertRaises(ValueError):self.db.write(2,wrong)
  self.assertEqual(self.db.read()['revision'],2)
if __name__=='__main__':unittest.main()
