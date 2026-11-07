import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from database import Database,Conflict
from clinics import Clinics
FIXTURE=json.loads((Path(__file__).parent/'profiles-fixture.json').read_text('utf-8'))
class ClinicTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.primary=Database(Path(self.temp.name)/'matab.sqlite3');self.primary.write(0,FIXTURE);self.registry=Clinics(self.primary)
 def tearDown(self):self.temp.cleanup()
 def test_legacy_bank_preserved_and_new_bank_empty(self):
  clinic=self.registry.create('مطب دوم');other=self.registry.get(clinic['id']);self.assertIsNone(other.read()['state']);self.assertEqual(self.primary.read()['state'],FIXTURE);self.assertEqual(self.registry.list()['clinics'][0]['name'],FIXTURE['clinic'])
 def test_isolation_reopen_and_restore(self):
  clinic=self.registry.create('مطب دوم');other=self.registry.get(clinic['id']);state=copy.deepcopy(FIXTURE);state['clinic']='مطب دوم';state['records']=[];other.write(0,state);other.backup_event('full','local');before=self.primary.read();other.write(1,state,'restore',[]);self.assertEqual(self.primary.read(),before);self.assertEqual(self.primary.history({'action':'export'})['total'],0);again=Clinics(Database(self.primary.path));self.assertEqual(again.get(clinic['id']).read()['state']['records'],[])
 def test_unknown_scope_and_duplicate_names(self):
  for id in ['../matab','missing','',None]:
   with self.assertRaises(ValueError):self.registry.get(id)
  with self.assertRaises(ValueError):self.registry.create(' ')
  with self.assertRaises(ValueError):self.registry.create(FIXTURE['clinic'])
 def test_stale_writer_and_settings_scope(self):
  clinic=self.registry.create('مطب دوم');other=self.registry.get(clinic['id']);other.write(0,FIXTURE)
  with self.assertRaises(Conflict):other.write(0,FIXTURE)
  self.assertEqual(self.primary.read()['revision'],1);self.assertEqual(other.backup('settings')['format'],'matab-settings')
 def test_global_backup_restore_keeps_existing_and_copies_every_bank(self):
  second=self.registry.create('مطب دوم');bank=self.registry.get(second['id']);other=copy.deepcopy(FIXTURE);other['clinic']='مطب دوم';other['records']=[];bank.write(0,other)
  payload=self.registry.backup_all();self.assertEqual(len(payload['clinics']),2);before=self.primary.read();result=self.registry.restore_all(payload);self.assertEqual(result['count'],2);self.assertEqual(len(self.registry.list()['clinics']),4);self.assertEqual(self.primary.read(),before)
  restored=self.registry.get(result['firstId']).read()['state'];self.assertEqual(restored['records'],FIXTURE['records']);self.assertIn('بازیابی',restored['clinic']);self.assertTrue(any(r['imported'] for r in self.registry.get(result['firstId']).history()['rows']))
 def test_invalid_global_file_is_atomic(self):
  payload=self.registry.backup_all();payload['clinics'].append(copy.deepcopy(payload['clinics'][0]));payload['clinics'][1]['backup']['state']['records'][0]['amount']=-1
  before=self.registry.list()
  with self.assertRaises(ValueError):self.registry.restore_all(payload)
  self.assertEqual(self.registry.list(),before);self.assertEqual(self.primary.read()['state'],FIXTURE)
 def test_global_transaction_failure_rolls_back(self):
  from unittest.mock import patch
  payload=self.registry.backup_all();payload['clinics'].append(copy.deepcopy(payload['clinics'][0]));before=self.registry.list();merge=self.registry.merge;calls=[]
  def failing(db,state,mode):
   calls.append(1)
   if len(calls)==2:raise RuntimeError('synthetic write failure')
   return merge(db,state,mode)
  with patch.object(self.registry,'merge',side_effect=failing):
   with self.assertRaises(RuntimeError):self.registry.restore_all(payload)
  self.assertEqual(self.registry.list(),before);self.assertEqual(self.registry.get('main').read()['state'],FIXTURE)
if __name__=='__main__':unittest.main()
