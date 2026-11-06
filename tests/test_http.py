import http.client,json,secrets,sys,tempfile,threading,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from server import Handler,ThreadingHTTPServer
from database import Database
FIXTURE=json.loads((Path(__file__).parent/'fixture.json').read_text('utf-8'))
class HttpTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.http=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.http.database=Database(Path(self.temp.name)/'test.sqlite3');self.http.token=secrets.token_urlsafe(32);self.port=self.http.server_port;self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
 def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.temp.cleanup()
 def request(self,path='/',method='GET',body=None,headers=None):
  c=http.client.HTTPConnection('127.0.0.1',self.port);c.request(method,path,body=body,headers=headers or {});r=c.getresponse();status=r.status;data=r.read();c.close();return status,data
 def test_local_session_and_csrf(self):
  self.assertEqual(self.request('/api/state')[0],403)
  self.assertEqual(self.request('/runtime.js',headers={'Sec-Fetch-Site':'cross-site'})[0],403)
  self.assertEqual(self.request('/',headers={'Host':'attacker.example'})[0],403)
  self.assertEqual(self.request('/api/state',headers={'X-Matab-Token':self.http.token,'Origin':'https://attacker.example'})[0],403)
  status,body=self.request('/api/state',headers={'X-Matab-Token':self.http.token});self.assertEqual(status,200);self.assertIsNone(json.loads(body)['state'])
 def test_save_and_stale_revision(self):
  h={'X-Matab-Token':self.http.token,'Content-Type':'application/json','Origin':f'http://127.0.0.1:{self.port}'};body=json.dumps({'revision':0,'state':FIXTURE})
  self.assertEqual(self.request('/api/state','POST',body,h)[0],200);self.assertEqual(self.request('/api/state','POST',body,h)[0],409)
 def test_no_arbitrary_file_serving(self):
  self.assertEqual(self.request('/../schema.sql')[0],404);self.assertEqual(self.request('/')[0],200)
 def test_history_release_backup_and_boundary(self):
  h={'X-Matab-Token':self.http.token,'Content-Type':'application/json'}
  self.request('/api/state','POST',json.dumps({'revision':0,'state':FIXTURE}),h)
  for path in ['/api/history','/api/releases','/api/backup?scope=settings']:
   self.assertEqual(self.request(path)[0],403);self.assertEqual(self.request(path,headers=h)[0],200)
  status,body=self.request('/api/backup?scope=full',headers=h);self.assertEqual(json.loads(body)['state'],FIXTURE)
  self.assertEqual(self.request('/api/backup-event','POST',json.dumps({'scope':'full','destination':'drive'}),h)[0],200)
  status,body=self.request('/api/history?action=export',headers=h);self.assertEqual(json.loads(body)['total'],1)
if __name__=='__main__':unittest.main()
