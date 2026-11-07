package ir.matab.desk;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import org.json.*;
import java.util.*;
final class ClinicManager{
 static final String[] COMMON={"services","products","areas","methods"};
 final Context context;final LocalDatabase validator;final SQLiteDatabase db;
 ClinicManager(Context c,LocalDatabase primary)throws Exception{
  context=c;validator=primary;db=c.openOrCreateDatabase("matab-unified.sqlite3",0,null);
  db.execSQL("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)");db.execSQL("CREATE TABLE IF NOT EXISTS clinics(id TEXT PRIMARY KEY,name TEXT NOT NULL,state_json TEXT,revision INTEGER NOT NULL DEFAULT 0)");db.execSQL("CREATE TABLE IF NOT EXISTS shared_catalogs(kind TEXT NOT NULL,id TEXT NOT NULL,entry_json TEXT NOT NULL,position INTEGER NOT NULL,PRIMARY KEY(kind,id))");
  db.execSQL("CREATE TABLE IF NOT EXISTS activity_log(id INTEGER PRIMARY KEY AUTOINCREMENT,occurred_at TEXT NOT NULL,local_day TEXT NOT NULL,action TEXT NOT NULL,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,label TEXT NOT NULL,details_json TEXT NOT NULL,imported INTEGER NOT NULL DEFAULT 0,source_key TEXT,clinic_id TEXT NOT NULL DEFAULT 'main',UNIQUE(clinic_id,source_key))");db.execSQL("CREATE INDEX IF NOT EXISTS idx_clinic_log ON activity_log(clinic_id,id)");HistorySupport.initialize(db,c);
  if(HistorySupport.meta(db,"unifiedMigrated")==null){
   SQLiteDatabase legacy=c.openOrCreateDatabase("clinics.sqlite3",0,null);legacy.execSQL("CREATE TABLE IF NOT EXISTS clinics(id TEXT PRIMARY KEY,name TEXT NOT NULL)");legacy.execSQL("INSERT OR IGNORE INTO clinics VALUES(?,?)",new Object[]{"main","مطب من"});db.beginTransaction();try{
    try(Cursor rows=legacy.rawQuery("SELECT id,name FROM clinics ORDER BY rowid",null)){while(rows.moveToNext()){String id=rows.getString(0),name=rows.getString(1);LocalDatabase bank=id.equals("main")?primary:new LocalDatabase(c,"clinic-"+id+".sqlite3");try{JSONObject read=bank.read(),state=read.optJSONObject("state");if(state!=null){name=state.optString("clinic",name);state=merge(state,"migrate");if(state.optInt("version")==5)validator.validate(state);}db.execSQL("INSERT INTO clinics VALUES(?,?,?,?)",new Object[]{id,name,state==null?null:state.toString(),read.getLong("revision")});JSONArray events=HistorySupport.history(bank.getReadableDatabase(),new JSONObject(),true).getJSONArray("rows");for(int i=0;i<events.length();i++)importEvent(id,events.getJSONObject(i),events.getJSONObject(i).optBoolean("imported"));}finally{if(bank!=primary)bank.close();}}}
    db.execSQL("INSERT INTO meta VALUES(?,?)",new Object[]{"unifiedMigrated","1"});db.setTransactionSuccessful();
   }finally{db.endTransaction();legacy.close();}
  }
 }
 String newId(){return UUID.randomUUID().toString().replace("-","");}
 JSONObject common()throws Exception{JSONObject out=new JSONObject();for(String kind:COMMON){JSONArray items=new JSONArray();try(Cursor c=db.rawQuery("SELECT entry_json FROM shared_catalogs WHERE kind=? ORDER BY position",new String[]{kind})){while(c.moveToNext())items.put(new JSONObject(c.getString(0)));}out.put(kind,items);}return out;}
 JSONObject read(String id)throws Exception{try(Cursor c=db.rawQuery("SELECT state_json,revision FROM clinics WHERE id=?",new String[]{id})){if(!c.moveToFirst())throw new Exception("مطب انتخاب‌شده وجود ندارد.");JSONObject s=c.isNull(0)?null:new JSONObject(c.getString(0)),shared=common();if(s!=null)for(String kind:COMMON)s.getJSONObject("catalogs").put(kind,shared.getJSONArray(kind));return new JSONObject().put("revision",c.getLong(1)).put("state",s==null?JSONObject.NULL:s).put("sharedCatalogs",shared);}}
 JSONObject merge(JSONObject value,String mode)throws Exception{
  JSONObject state=new JSONObject(value.toString()),shared=common();Map<String,Map<String,String>> maps=new HashMap<>();
  for(String kind:COMMON){Map<String,String> aliases=new HashMap<>();maps.put(kind,aliases);JSONArray existing=shared.getJSONArray(kind),incoming=state.getJSONObject("catalogs").getJSONArray(kind);
   for(int i=0;i<incoming.length();i++){JSONObject row=incoming.getJSONObject(i),byId=null,byName=null;for(int j=0;j<existing.length();j++){JSONObject e=existing.getJSONObject(j);if(e.getString("id").equals(row.getString("id")))byId=e;if(LocalDatabase.norm(e.getString("name")).equals(LocalDatabase.norm(row.getString("name"))))byName=e;}JSONObject target=mode.equals("save")?(byId==null?byName:byId):byName;
    if(mode.equals("save")&&byId!=null&&byName!=null&&!byId.getString("id").equals(byName.getString("id")))throw new Exception("گزینه مشترک هم‌نام وجود دارد.");String id;
    if(target!=null){id=target.getString("id");if(mode.equals("save")){Iterator<String> keys=row.keys();while(keys.hasNext()){String key=keys.next();target.put(key,row.get(key));}target.put("id",id);}else if(mode.equals("migrate"))target.put("active",target.getBoolean("active")||row.getBoolean("active"));}
    else{id=byId==null?row.getString("id"):kind+"-"+newId();existing.put(new JSONObject(row.toString()).put("id",id));}aliases.put(row.getString("id"),id);
   }if(existing.length()>1000)throw new Exception("تعداد گزینه‌های مشترک از سقف مجاز بیشتر است.");state.getJSONObject("catalogs").put(kind,new JSONArray(existing.toString()));
  }
  JSONArray receipts=state.optJSONArray("receipts");if(receipts!=null)for(int i=0;i<receipts.length();i++){JSONObject r=receipts.getJSONObject(i);String alias=maps.get("products").get(r.getString("productId"));if(alias!=null)r.put("productId",alias);}
  JSONArray records=state.getJSONArray("records");for(int i=0;i<records.length();i++){JSONArray payments=records.getJSONObject(i).optJSONArray("payments");if(payments!=null)for(int j=0;j<payments.length();j++){JSONObject p=payments.getJSONObject(j);String alias=maps.get("methods").get(p.getString("method"));if(alias!=null)p.put("method",alias);}}
  db.execSQL("DELETE FROM shared_catalogs");for(String kind:COMMON){JSONArray items=shared.getJSONArray(kind);for(int i=0;i<items.length();i++){JSONObject row=items.getJSONObject(i);db.execSQL("INSERT INTO shared_catalogs VALUES(?,?,?,?)",new Object[]{kind,row.getString("id"),row.toString(),i});}}return state;
 }
 JSONArray list()throws Exception{JSONArray out=new JSONArray();try(Cursor c=db.rawQuery("SELECT id,name FROM clinics ORDER BY rowid",null)){while(c.moveToNext())out.put(new JSONObject().put("id",c.getString(0)).put("name",c.getString(1)));}return out;}
 void importEvent(String id,JSONObject e,boolean imported)throws Exception{HistorySupport.add(db,e.getString("action"),e.getString("entityType"),e.getString("label"),e.getString("entityId"),e.getJSONObject("details"),e.getString("timestamp"),imported,e.getString("sourceKey"),id);}
 JSONObject write(String id,JSONObject p)throws Exception{
  JSONObject incoming=p.getJSONObject("state");validator.validate(incoming);String operation=p.optString("operation","save");if(!Arrays.asList("save","restore","restore-settings").contains(operation))throw new Exception("عملیات معتبر نیست.");JSONArray imported=p.optJSONArray("history");HistorySupport.validateHistory(imported);if(imported!=null&&!operation.equals("restore"))throw new Exception("تاریخچه فقط در بازیابی کامل وارد می‌شود.");
  db.beginTransaction();try{JSONObject previous=read(id);long revision=previous.getLong("revision");if(p.getLong("revision")!=revision)throw new Exception("اطلاعات یا فهرست مشترک تغییر کرده؛ صفحه را دوباره باز کنید.");JSONObject before=common(),state=merge(incoming,operation.equals("save")?"save":"restore");validator.validate(state);
   if(!HistorySupport.equal(before,common()))db.execSQL("UPDATE clinics SET revision=revision+1");else db.execSQL("UPDATE clinics SET revision=revision+1 WHERE id=?",new Object[]{id});db.execSQL("UPDATE clinics SET name=?,state_json=? WHERE id=?",new Object[]{state.getString("clinic"),state.toString(),id});if(imported!=null)for(int i=0;i<imported.length();i++)importEvent(id,imported.getJSONObject(i),true);HistorySupport.changes(db,previous.optJSONObject("state"),state,operation,id);db.setTransactionSuccessful();return new JSONObject().put("revision",revision+1).put("state",state);
  }finally{db.endTransaction();}
 }
 JSONObject backup(String id,String scope)throws Exception{JSONObject state=read(id).optJSONObject("state");if(scope.equals("settings")){if(state==null)throw new Exception("ابتدا مطب را باز کنید.");return new JSONObject().put("format","matab-settings").put("formatVersion",1).put("clinic",state.getString("clinic")).put("settings",state.getJSONObject("settings")).put("catalogs",state.getJSONObject("catalogs"));}if(!scope.equals("full"))throw new Exception("نوع پشتیبان معتبر نیست.");return new JSONObject().put("format","matab-backup").put("formatVersion",1).put("state",state==null?JSONObject.NULL:state).put("history",HistorySupport.history(db,new JSONObject(),true,id).getJSONArray("rows")).put("releases",HistorySupport.releaseHistory(db,context).getJSONArray("releases"));}
 JSONObject backupAll()throws Exception{JSONArray all=list(),out=new JSONArray();for(int i=0;i<all.length();i++){JSONObject c=all.getJSONObject(i);out.put(new JSONObject().put("name",c.getString("name")).put("backup",backup(c.getString("id"),"full")));}return new JSONObject().put("format","matab-all-clinics").put("formatVersion",1).put("clinics",out);}
 JSONObject restoreAll(JSONObject payload)throws Exception{
  if(!payload.getString("format").equals("matab-all-clinics")||payload.getInt("formatVersion")!=1)throw new Exception("پشتیبان کلی معتبر نیست.");JSONArray items=payload.getJSONArray("clinics");if(items.length()<1||items.length()>100)throw new Exception("تعداد مطب‌ها معتبر نیست.");for(int i=0;i<items.length();i++){JSONObject item=items.getJSONObject(i),b=item.getJSONObject("backup");String name=item.getString("name").trim();if(name.isEmpty()||name.length()>80||!b.getString("format").equals("matab-backup")||b.getInt("formatVersion")!=1)throw new Exception("پشتیبان معتبر نیست.");if(!b.isNull("state"))validator.validate(b.getJSONObject("state"));HistorySupport.validateHistory(b.optJSONArray("history"));}
  db.beginTransaction();try{JSONArray current=list();if(current.length()+items.length()>100)throw new Exception("تعداد مطب‌ها از سقف مجاز عبور می‌کند.");Set<String> names=new HashSet<>();for(int i=0;i<current.length();i++)names.add(LocalDatabase.norm(current.getJSONObject(i).getString("name")));JSONObject before=common();String first=null;
   for(int i=0;i<items.length();i++){JSONObject item=items.getJSONObject(i),b=item.getJSONObject("backup");String base=item.getString("name").trim(),name=base;int n=1;while(names.contains(LocalDatabase.norm(name)))name=base.substring(0,Math.min(55,base.length()))+" (بازیابی "+(n++)+")";names.add(LocalDatabase.norm(name));String id=newId();if(first==null)first=id;JSONObject state=b.isNull("state")?null:merge(b.getJSONObject("state"),"restore");if(state!=null){state.put("clinic",name);validator.validate(state);}db.execSQL("INSERT INTO clinics VALUES(?,?,?,1)",new Object[]{id,name,state==null?null:state.toString()});JSONArray events=b.optJSONArray("history");if(events!=null)for(int j=0;j<events.length();j++)importEvent(id,events.getJSONObject(j),true);if(state!=null)HistorySupport.changes(db,null,state,"restore",id);}
   if(!HistorySupport.equal(before,common()))db.execSQL("UPDATE clinics SET revision=revision+1");db.setTransactionSuccessful();return new JSONObject().put("count",items.length()).put("firstId",first);
  }finally{db.endTransaction();}
 }
 synchronized void close(){db.close();validator.close();}
 synchronized JSONObject request(String id,String action,JSONObject p)throws Exception{
  if(action.equals("save"))return write(id,p);if(action.equals("restoreAll")){read(id);return restoreAll(p);}
  db.beginTransaction();try{JSONObject active=read(id),result;
   if(action.equals("load"))result=active;
   else if(action.equals("list"))result=new JSONObject().put("clinics",list());
   else if(action.equals("create")){String name=p.getString("name").trim();if(name.isEmpty()||name.length()>80)throw new Exception("نام مطب باید بین ۱ تا ۸۰ حرف باشد.");JSONArray rows=list();if(rows.length()>=100)throw new Exception("حداکثر ۱۰۰ مطب قابل تعریف است.");for(int i=0;i<rows.length();i++)if(LocalDatabase.norm(rows.getJSONObject(i).getString("name")).equals(LocalDatabase.norm(name)))throw new Exception("مطب هم‌نام وجود دارد.");String key=newId();db.execSQL("INSERT INTO clinics(id,name) VALUES(?,?)",new Object[]{key,name});result=new JSONObject().put("id",key).put("name",name);}
   else if(action.equals("history"))result=HistorySupport.history(db,p,false,id);
   else if(action.equals("releases"))result=HistorySupport.releaseHistory(db,context);
   else if(action.equals("backup"))result=backup(id,p.getString("scope"));
   else if(action.equals("backupAll"))result=backupAll();
   else if(action.equals("backupEvent")||action.equals("backupAllEvent")){String destination=p.getString("destination"),scope=action.equals("backupAllEvent")?"all":p.getString("scope");if(!Arrays.asList("local","drive").contains(destination)||!Arrays.asList("all","full","settings").contains(scope))throw new Exception("رویداد معتبر نیست.");JSONArray all=scope.equals("all")?list():new JSONArray().put(new JSONObject().put("id",id));for(int i=0;i<all.length();i++)HistorySupport.add(db,"export","backup","فایل پشتیبان "+scope,"",new JSONObject().put("scope",scope).put("destination",destination),null,false,null,all.getJSONObject(i).getString("id"));result=new JSONObject().put("ok",true);}
   else if(action.equals("info"))result=new JSONObject().put("location","matab-unified.sqlite3 · بانک مشترک با تفکیک مطب‌ها");
   else throw new Exception("عملیات مطب معتبر نیست.");db.setTransactionSuccessful();return result;
  }finally{db.endTransaction();}
 }
}
