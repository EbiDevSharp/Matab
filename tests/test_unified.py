import copy,json,sqlite3,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from database import Database,Conflict
from clinics import Clinics
from legacy_clinics import Clinics as Legacy
FIXTURE=json.loads((Path(__file__).parent/'profiles-fixture.json').read_text('utf-8'))
class UnifiedTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'matab.sqlite3';self.legacy=Database(self.path);self.legacy.write(0,FIXTURE)
 def tearDown(self):self.temp.cleanup()
 def test_migrate_two_banks_deduplicates_and_preserves_snapshots(self):
  old=Legacy(self.legacy);second=old.create('مطب دوم');s=copy.deepcopy(FIXTURE);s['clinic']='مطب دوم';product=s['receipts'][0]['productId'];method=s['records'][0]['payments'][0]['method']
  for c in s['catalogs']['products']:
   if c['id']==product:c['id']='other-product';c['name']='  '+c['name']+'  '
  for c in s['catalogs']['methods']:
   if c['id']==method:c['id']='other-method';c['feeBps']=7777
  for r in s['receipts']:
   if r['productId']==product:r['productId']='other-product'
  for r in s['records']:
   for p in r['payments']:
    if p['method']==method:p['method']='other-method'
  old.get(second['id']).write(0,s);store=Clinics(self.legacy);a=store.get('main').read()['state'];b=store.get(second['id']).read()['state'];self.assertEqual(a['catalogs']['products'],b['catalogs']['products']);self.assertEqual(b['receipts'][0]['productId'],product);self.assertEqual(b['records'][0]['payments'][0]['method'],method);self.assertEqual(b['records'][0]['payments'][0]['feeBps'],FIXTURE['records'][0]['payments'][0]['feeBps']);self.assertEqual(b['records'][0]['patient'],FIXTURE['records'][0]['patient']);self.assertEqual(store.path.name,'matab-unified.sqlite3');self.assertTrue(self.path.exists());self.assertEqual(Clinics(self.path).list(),store.list())
 def test_common_catalog_edit_shared_and_stale_other_window_rejected(self):
  store=Clinics(self.legacy);id=store.create('مطب دوم')['id'];other=store.get(id);state=copy.deepcopy(FIXTURE);state['clinic']='مطب دوم';other.write(0,state);first=store.get('main');base=first.read();stale=other.read();changed=copy.deepcopy(base['state']);changed['catalogs']['areas'].append({'id':'new-area','name':'ناحیه مشترک جدید','active':True});first.write(base['revision'],changed);self.assertTrue(any(c['id']=='new-area' for c in other.read()['state']['catalogs']['areas']));
  with self.assertRaises(Conflict):other.write(stale['revision'],stale['state'])
  self.assertTrue(any(r['entityId']=='new-area' for r in other.history({'entityType':'area'})['rows']))
 def test_delete_update_snapshots_and_scope(self):
  store=Clinics(self.legacy);bank=store.get('main');read=bank.read();state=copy.deepcopy(read['state']);state['records'][0]['note']='قبل حذف';bank.write(read['revision'],state);revision=bank.read()['revision'];record=copy.deepcopy(state['records'][0]);state['records']=state['records'][1:];bank.write(revision,state);event=bank.history({'action':'delete','entityType':'service'})['rows'][0];self.assertEqual(event['details']['before'],record);self.assertIsNone(event['details']['after']);self.assertEqual(event['details']['before']['payments'][0]['amount'],record['payments'][0]['amount']);id=store.create('مطب دوم')['id'];self.assertEqual(store.get(id).history({'entityType':'service'})['total'],0)
 def test_failed_migration_rolls_back_and_can_retry(self):
  from unittest.mock import patch
  old=Legacy(self.legacy);second=old.create('مطب دوم');state=copy.deepcopy(FIXTURE);state['clinic']='مطب دوم';old.get(second['id']).write(0,state);merge=Clinics.merge;calls=[]
  def fail(owner,db,state,mode):
   calls.append(mode)
   if len(calls)==2:raise OSError('synthetic migration failure')
   return merge(owner,db,state,mode)
  with patch.object(Clinics,'merge',fail):
   with self.assertRaises(OSError):Clinics(self.legacy)
  with sqlite3.connect(self.path.parent/'matab-unified.sqlite3') as db:
   self.assertEqual(db.execute('SELECT count(*) FROM clinics').fetchone()[0],0);self.assertEqual(db.execute('SELECT count(*) FROM shared_catalogs').fetchone()[0],0)
  self.assertEqual(self.legacy.read()['state'],FIXTURE);store=Clinics(self.legacy);self.assertEqual(len(store.list()['clinics']),2);self.assertEqual(store.get(second['id']).read()['state']['records'],FIXTURE['records'])
 def test_restore_catalog_id_collision_keeps_old_references(self):
  store=Clinics(self.legacy);bank=store.get('main');original=bank.read();incoming=copy.deepcopy(original['state']);item=incoming['catalogs']['products'][0];item['name']='محصول جدید با شناسه قدیمی';oldid=item['id'];incoming['records']=[];incoming['receipts']=[];bank.write(original['revision'],incoming,'restore',[]);products=bank.read()['state']['catalogs']['products'];self.assertTrue(any(c['id']==oldid and c['name']!=item['name'] for c in products));self.assertTrue(any(c['id']!=oldid and c['name']==item['name'] for c in products))
if __name__=='__main__':unittest.main()
