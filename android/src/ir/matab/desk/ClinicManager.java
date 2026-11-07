package ir.matab.desk;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import org.json.*;
import java.util.*;
final class ClinicManager{
 final Context context;final SQLiteDatabase registry;final Map<String,LocalDatabase> banks=new HashMap<>();
 ClinicManager(Context context,LocalDatabase primary)throws Exception{this.context=context;registry=context.openOrCreateDatabase("clinics.sqlite3",0,null);registry.execSQL("CREATE TABLE IF NOT EXISTS clinics(id TEXT PRIMARY KEY,name TEXT NOT NULL)");registry.execSQL("INSERT OR IGNORE INTO clinics VALUES(?,?)",new Object[]{"main","مطب من"});banks.put("main",primary);}
 LocalDatabase get(String id)throws Exception{try(Cursor c=registry.rawQuery("SELECT name FROM clinics WHERE id=?",new String[]{id})){if(!c.moveToFirst())throw new Exception("مطب انتخاب‌شده وجود ندارد.");}LocalDatabase db=banks.get(id);if(db==null){db=new LocalDatabase(context,"clinic-"+id+".sqlite3");banks.put(id,db);}return db;}
 JSONArray list()throws Exception{JSONArray out=new JSONArray();try(Cursor c=registry.rawQuery("SELECT id,name FROM clinics ORDER BY rowid",null)){while(c.moveToNext()){String id=c.getString(0),name=c.getString(1);JSONObject state=get(id).read().optJSONObject("state");out.put(new JSONObject().put("id",id).put("name",state==null?name:state.getString("clinic")));}}return out;}
 synchronized void close(){for(LocalDatabase db:banks.values())db.close();registry.close();}
 synchronized JSONObject request(String id,String action,JSONObject p)throws Exception{
  LocalDatabase db=get(id);
  if(action.equals("list"))return new JSONObject().put("clinics",list());
  if(action.equals("create")){String name=p.getString("name").trim();if(name.isEmpty()||name.length()>80)throw new Exception("نام مطب باید بین ۱ تا ۸۰ حرف باشد.");JSONArray rows=list();if(rows.length()>=100)throw new Exception("حداکثر ۱۰۰ مطب قابل تعریف است.");for(int i=0;i<rows.length();i++)if(rows.getJSONObject(i).getString("name").trim().equalsIgnoreCase(name))throw new Exception("مطب هم‌نام وجود دارد.");String key=UUID.randomUUID().toString().replace("-","");registry.execSQL("INSERT INTO clinics VALUES(?,?)",new Object[]{key,name});return new JSONObject().put("id",key).put("name",name);}
  if(action.equals("load"))return db.read();if(action.equals("save"))return db.write(p);if(action.equals("history"))return db.history(p);if(action.equals("releases"))return db.releases();if(action.equals("backup"))return db.backup(p.getString("scope"));if(action.equals("backupEvent")){db.backupEvent(p.getString("scope"),p.getString("destination"));return new JSONObject().put("ok",true);}if(action.equals("info"))return new JSONObject().put("location","SQLite · اطلاعات مستقل مطب انتخاب‌شده");throw new Exception("عملیات مطب معتبر نیست.");
 }
}
