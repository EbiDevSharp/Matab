package ir.matab.desk;
import org.json.*;
import java.util.*;
final class ProfileValidator {
 static void require(boolean value)throws Exception{if(!value)throw new Exception("اطلاعات مشتری، پزشک یا تنظیمات معتبر نیست.");}
 static String text(JSONObject o,String key,int max)throws Exception{Object raw=o.get(key);require(raw instanceof String);String s=(String)raw;require(s.length()<=max);return s;}
 static void mobile(String s)throws Exception{require(s.isEmpty()||s.matches("09[0-9]{9}"));}
 static String name(JSONObject p)throws Exception{String first=text(p,"firstName",80),last=text(p,"lastName",80),legacy=text(p,"legacyName",161);String result=((first.isEmpty()?"":first)+(first.isEmpty()||last.isEmpty()?"":" ")+last).trim();return result.isEmpty()?legacy:result;}
 static void validate(JSONObject s)throws Exception{
  JSONObject settings=s.getJSONObject("settings");require(Arrays.asList("divisor","percent").contains(settings.getString("shareMode")));FinanceValidator.integer(settings,"doctorBps",0,10000);
  JSONObject appearance=settings.getJSONObject("appearance");require(Arrays.asList("vazirmatn","shabnam","sahel","system").contains(appearance.getString("font"))&&Arrays.asList("mint","blue","violet","dark","auto").contains(appearance.getString("palette")));FinanceValidator.integer(appearance,"scale",80,150);
  Set<String> doctors=new HashSet<>();JSONArray ds=s.getJSONObject("catalogs").getJSONArray("doctors");for(int i=0;i<ds.length();i++)doctors.add(ds.getJSONObject(i).getString("id"));require(settings.isNull("defaultDoctorId")||doctors.contains(settings.getString("defaultDoctorId")));
  JSONArray patients=s.getJSONArray("patients");require(patients.length()<=100000);Set<String> ids=new HashSet<>();for(int i=0;i<patients.length();i++){JSONObject p=patients.getJSONObject(i);String id=text(p,"id",100);require(!id.isEmpty()&&ids.add(id));FinanceValidator.integer(p,"created",0,FinanceValidator.MAX);String phone=text(p,"mobile",11);mobile(phone);String display=name(p);require(!display.trim().isEmpty()||!phone.isEmpty());}
  JSONArray rs=s.getJSONArray("records");for(int i=0;i<rs.length();i++){JSONObject r=rs.getJSONObject(i);String phone=text(r,"mobile",11);mobile(phone);require(r.isNull("patientId")||ids.contains(r.getString("patientId")));require(r.isNull("doctorId")||doctors.contains(r.getString("doctorId")));String doctor=text(r,"doctorLabel",80);require(r.isNull("doctorId")?doctor.isEmpty():!doctor.trim().isEmpty());require(Arrays.asList("divisor","percent").contains(r.getString("shareMode")));FinanceValidator.integer(r,"doctorBps",0,10000);String display=name(r);require(display.equals(r.getString("patient")));require(!r.isNull("patientId")||(display.isEmpty()&&phone.isEmpty()));}
 }
}
