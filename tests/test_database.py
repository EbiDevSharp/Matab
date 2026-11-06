import copy,json,sys,tempfile,unittest,sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from database import Database,Conflict,validate,date_ok
FIXTURE=json.loads((Path(__file__).parent/'fixture.json').read_text('utf-8'))
class StoreTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'matab.sqlite3';self.db=Database(self.path)
 def tearDown(self):self.temp.cleanup()
 def test_roundtrip_and_restart(self):
  self.assertIsNone(self.db.read()['state']);self.db.write(0,FIXTURE);self.db=Database(self.path);result=self.db.read();self.assertEqual(result['revision'],1);self.assertEqual(result['state'],FIXTURE)
  with sqlite3.connect(self.path) as db:self.assertEqual(db.execute('SELECT count(*) FROM payments').fetchone()[0],2);self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
 def test_stale_writer_keeps_previous_data(self):
  self.db.write(0,FIXTURE)
  with self.assertRaises(Conflict):self.db.write(0,{**FIXTURE,'clinic':'stale'})
  self.assertEqual(self.db.read()['state']['clinic'],FIXTURE['clinic'])
 def test_invalid_payment_is_atomic(self):
  self.db.write(0,FIXTURE);bad=copy.deepcopy(FIXTURE);bad['records'][0]['payments'][0]['amount']=10000000
  with self.assertRaises(ValueError):self.db.write(1,bad)
  self.assertEqual(self.db.read()['state'],FIXTURE)
 def test_restore_replaces_all_tables(self):
  self.db.write(0,FIXTURE);empty=copy.deepcopy(FIXTURE);empty['records']=[];self.db.write(1,empty);self.assertEqual(self.db.read()['state']['records'],[])
 def test_catalog_rename_preserves_snapshot(self):
  state=copy.deepcopy(FIXTURE);state['catalogs']['methods'][-1]['name']='نام جدید';self.db.write(0,state);self.assertEqual(self.db.read()['state']['records'][0]['payments'][0]['methodLabel'],'کارت‌خوان دوم')
 def test_duplicate_catalog_and_invalid_date(self):
  bad=copy.deepcopy(FIXTURE);bad['catalogs']['areas'].append({**bad['catalogs']['areas'][0],'id':'duplicate'})
  with self.assertRaises(ValueError):validate(bad)
  self.assertFalse(date_ok('1404/12/30'));self.assertTrue(date_ok('1403/12/30'));self.assertFalse(date_ok('1405/07/31'))
if __name__=='__main__':unittest.main()
