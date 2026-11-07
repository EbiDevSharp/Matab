"""Run the independent local website: python desktop/server.py"""
import argparse, json, mimetypes, os, re, secrets, sys, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,unquote,parse_qs
from database import Database,Conflict
from clinics import Clinics
ROOT=Path(__file__).resolve().parent.parent
WEB=ROOT/'web'
class Handler(BaseHTTPRequestHandler):
    server_version='MatabDesk/1.2.0'
    def log_message(self,*args):pass
    def send(self,status,body,kind='application/json; charset=utf-8'):
        if not isinstance(body,bytes):body=body.encode('utf-8')
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cross-Origin-Resource-Policy','same-origin');self.send_header('X-Frame-Options','SAMEORIGIN')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'")
        self.end_headers();self.wfile.write(body)
    def jsend(self,status,obj):self.send(status,json.dumps(obj,ensure_ascii=False))
    def boundary(self,token=False):
        host=self.headers.get('Host','')
        if not re.fullmatch(r'(?:127\.0\.0\.1|localhost):\d{1,5}',host):self.jsend(403,{'error':'دسترسی فقط از روی همین سیستم مجاز است.'});return False
        origin=self.headers.get('Origin')
        if origin and origin!='http://'+host:self.jsend(403,{'error':'درخواست از مبدا دیگری ارسال شده است.'});return False
        if self.headers.get('Sec-Fetch-Site') not in (None,'none','same-origin'):self.jsend(403,{'error':'درخواست از مبدا دیگری ارسال شده است.'});return False
        if token and not secrets.compare_digest(self.headers.get('X-Matab-Token',''),self.server.token):self.jsend(403,{'error':'صفحه را از طریق میان‌بر برنامه باز کنید.'});return False
        return True
    def clinic_database(self):
        if not hasattr(self.server,"clinics"):self.server.clinics=Clinics(self.server.database)
        return self.server.clinics.get(self.headers.get("X-Matab-Clinic","main"))
    def do_GET(self):
        if not self.boundary():return
        path=urlsplit(self.path).path
        if path=='/runtime.js':self.send(200,'window.MATAB_TOKEN='+json.dumps(self.server.token)+';','text/javascript; charset=utf-8');return
        if path=='/api/ping':self.jsend(200,{'app':'matab-desk-independent','version':3});return
        if path.startswith('/api/'):
            if not self.boundary(True):return
            try:
                database=self.clinic_database()
                if path=='/api/clinics':self.jsend(200,self.server.clinics.list())
                elif path=='/api/state':self.jsend(200,database.read())
                elif path=='/api/history':self.jsend(200,database.history({k:v[0] for k,v in parse_qs(urlsplit(self.path).query).items()}))
                elif path=='/api/releases':self.jsend(200,database.releases())
                elif path=='/api/backup':self.jsend(200,database.backup(parse_qs(urlsplit(self.path).query).get('scope',['full'])[0]))
                elif path=='/api/info':self.jsend(200,{'location':str(database.path),'engine':'SQLite'})
                else:self.jsend(404,{'error':'مسیر پیدا نشد.'})
            except Exception:self.jsend(500,{'error':'خواندن پایگاه داده ممکن نشد. برنامه را دوباره اجرا کنید.'})
            return
        if path=='/':path='/index.html'
        target=(WEB/unquote(path).lstrip('/')).resolve()
        if WEB.resolve() not in target.parents or not target.is_file():self.jsend(404,{'error':'فایل پیدا نشد.'});return
        mime=mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
        if target.suffix=='.js':mime='text/javascript'
        self.send(200,target.read_bytes(),mime+('; charset=utf-8' if mime.startswith('text/') else ''))
    def do_POST(self):
        if not self.boundary(True):return
        if urlsplit(self.path).path not in ('/api/state','/api/backup-event','/api/clinics'):self.jsend(404,{'error':'مسیر پیدا نشد.'});return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>20*1024*1024:raise ValueError('حجم اطلاعات معتبر نیست.')
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('قالب درخواست معتبر نیست.')
            body=json.loads(self.rfile.read(length))
            database=self.clinic_database()
            if urlsplit(self.path).path=='/api/clinics':self.jsend(200,self.server.clinics.create(body.get('name')))
            elif urlsplit(self.path).path=='/api/backup-event':
                database.backup_event(body.get('scope'),body.get('destination'));self.jsend(200,{'ok':True})
            else:self.jsend(200,database.write(body.get('revision'),body.get('state'),body.get('operation','save'),body.get('history')))
        except Conflict as e:self.jsend(409,{'error':str(e)})
        except (ValueError,TypeError,AttributeError,KeyError) as e:self.jsend(400,{'error':'اطلاعات معتبر نیست یا قالب درخواست اشتباه است.'})
        except Exception:self.jsend(500,{'error':'ذخیره در پایگاه داده انجام نشد. اطلاعات قبلی حفظ شده است.'})
    def do_OPTIONS(self):self.jsend(403,{'error':'مجاز نیست.'})
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--host',choices=['127.0.0.1','localhost'],default='127.0.0.1');parser.add_argument('--strictPort',action='store_true');parser.add_argument('--port',type=int,default=int(os.environ.get('PORT','8765')));parser.add_argument('--no-browser',action='store_true');parser.add_argument('--data-dir');args=parser.parse_args()
    base=Path(args.data_dir) if args.data_dir else Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local'/'share'))/'MatabDesk'
    database=Database(base/'matab.sqlite3')
    try:server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    except OSError:
        print('The local port is already in use. Close the previous Matab window, or use --port with a different port.');return 1
    server.token=secrets.token_urlsafe(32);server.database=database;server.clinics=Clinics(database)
    address='http://127.0.0.1:'+str(server.server_port)
    print('Matab Desk: '+address+'\nSQLite: '+str(database.path)+'\nKeep this window open. Press Ctrl+C to stop.',flush=True)
    if not args.no_browser:threading.Timer(.4,lambda:webbrowser.open(address)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
    return 0
if __name__=='__main__':raise SystemExit(main())
