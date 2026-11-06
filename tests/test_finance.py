import copy,json,sqlite3,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from database import Database,validate
from finance import inventory,ratio
FIXTURE=json.loads((Path(__file__).parent/'finance-fixture.json').read_text('utf-8'))
class FinanceTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'matab.sqlite3';self.db=Database(self.path)
 def tearDown(self):self.temp.cleanup()
 def test_roundtrip_finance_and_reopen(self):
  self.db.write(0,FIXTURE);state=Database(self.path).read()['state'];self.assertEqual(state,FIXTURE);lots,costs=inventory(state);self.assertEqual(costs['r1'],1000000);self.assertEqual(ratio(5000000,1320,10000),660000);self.assertEqual(ratio(5000000-660000-costs['r1'],1000,2000),1670000);self.assertEqual(costs['r2'],200000)
 def test_failed_overdraw_is_atomic(self):
  self.db.write(0,FIXTURE);bad=copy.deepcopy(FIXTURE);bad['records'][0]['consumptions'][0]['quantityMilli']=11000
  with self.assertRaises(ValueError):self.db.write(1,bad)
  self.assertEqual(self.db.read()['state'],FIXTURE)
 def test_delete_service_returns_material(self):
  self.db.write(0,FIXTURE);state=copy.deepcopy(FIXTURE);state['records']=[];self.db.write(1,state);self.assertEqual(inventory(self.db.read()['state'])[0]['lot-gel']['usedMilli'],0)
 def test_invalid_fee_divisor_date_and_missing_lot(self):
  for key,value in [('divisorMilli',0),('date','1405/07/01')]:
   bad=copy.deepcopy(FIXTURE);bad['records'][0][key]=value
   with self.assertRaises(ValueError):validate(bad)
  bad=copy.deepcopy(FIXTURE);bad['records'][0]['payments'][0]['feeBps']=10001
  with self.assertRaises(ValueError):validate(bad)
  bad=copy.deepcopy(FIXTURE);bad['receipts']=[]
  with self.assertRaises(ValueError):validate(bad)
 def test_upgrade_keeps_old_rows_and_backup(self):
  legacy_path=Path(self.temp.name)/'legacy.sqlite3';legacy=copy.deepcopy(FIXTURE)
  with sqlite3.connect(legacy_path) as db:
   db.executescript((Path(__file__).parent/'legacy_schema.sql').read_text('utf-8'))
   db.executemany('INSERT OR REPLACE INTO meta VALUES(?,?)',[('clinic','مطب قبلی'),('revision','7')])
   for kind,entries in legacy['catalogs'].items():db.executemany('INSERT INTO catalogs VALUES(?,?,?,?,?)',[(kind,c['id'],c['name'],int(c['active']),i) for i,c in enumerate(entries)])
   for r in legacy['records']:
    db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',tuple(r[k] for k in ['id','created','date','patient','service','product','area','volume','unit','price','amount','note']))
    db.executemany('INSERT INTO payments VALUES(?,?,?,?,?,?,?,?,?,?)',[(r['id'],p['id'],p['amount'],p['date'],p['method'],p['methodLabel'],p['stage'],p['note'],int(p['legacy']),i) for i,p in enumerate(r['payments'])])
  upgraded=Database(legacy_path);read=upgraded.read();self.assertEqual(read['revision'],7);self.assertEqual(read['state']['version'],3);self.assertEqual(len(read['state']['records']),2);self.assertIsNone(read['state']['records'][0]['payments'][0]['feeBps']);self.assertTrue((Path(self.temp.name)/'matab-before-v2.sqlite3.bak').exists());upgraded.write(7,FIXTURE);self.assertEqual(upgraded.read()['state'],FIXTURE)
if __name__=='__main__':unittest.main()
