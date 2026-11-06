package ir.matab.desk;
import org.json.*;
import java.util.*;
import java.math.BigInteger;
final class FinanceValidator {
 interface DateCheck{boolean valid(String date);}
 static final long MAX=9007199254740991L;
 static void require(boolean ok)throws Exception{if(!ok)throw new Exception("اطلاعات مالی یا موجودی معتبر نیست.");}
 static long integer(JSONObject o,String k,long min,long max)throws Exception{Object raw=o.get(k);require(raw instanceof Number);Number n=(Number)raw;long v=n.longValue();require(v>=min&&v<=max&&n.doubleValue()==(double)v);return v;}
 static String text(JSONObject o,String k,int max,boolean required)throws Exception{Object raw=o.get(k);require(raw instanceof String);String s=(String)raw;require(s.length()<=max&&(!required||!s.trim().isEmpty()));return s;}
 static long ratio(long a,long b,long d)throws Exception{require(d>0);BigInteger n=BigInteger.valueOf(a).multiply(BigInteger.valueOf(b)),den=BigInteger.valueOf(d);int sign=n.signum();BigInteger result=n.abs().add(den.divide(BigInteger.valueOf(2))).divide(den);require(result.compareTo(BigInteger.valueOf(MAX))<=0);return result.longValue()*sign;}
 static final class Lot{JSONObject r;long used=0,cost=0;Lot(JSONObject r){this.r=r;}}
 static void validate(JSONObject s,DateCheck dates)throws Exception{
  integer(s.getJSONObject("settings"),"divisorMilli",1,1000000);
  JSONArray methods=s.getJSONObject("catalogs").getJSONArray("methods");for(int i=0;i<methods.length();i++)integer(methods.getJSONObject(i),"feeBps",0,10000);
  Set<String> products=new HashSet<>();JSONArray productRows=s.getJSONObject("catalogs").getJSONArray("products");for(int i=0;i<productRows.length();i++)products.add(productRows.getJSONObject(i).getString("id"));
  JSONArray receipts=s.getJSONArray("receipts");require(receipts.length()<=10000);Map<String,Lot> lots=new HashMap<>();long total=0;
  for(int i=0;i<receipts.length();i++){JSONObject r=receipts.getJSONObject(i);String id=text(r,"id",100,true);require(!lots.containsKey(id)&&products.contains(r.getString("productId"))&&dates.valid(r.getString("date")));integer(r,"created",0,MAX);text(r,"productLabel",80,true);text(r,"note",500,false);
   long qty=integer(r,"quantityMilli",1,100000000),contents=integer(r,"contentsMilli",1,100000000),price=integer(r,"unitPrice",0,1000000000000L);String pack=r.getString("packUnit"),base=r.getString("baseUnit");require(Arrays.asList("cc","unit","item").contains(base)&&Arrays.asList("cc","unit","item","vial","box").contains(pack));if(Arrays.asList("cc","unit","item").contains(pack))require(base.equals(pack)&&contents==1000);
   long raw=Math.multiplyExact(qty,contents);require(raw<=MAX&&raw%1000==0);long received=raw/1000,cost=ratio(price,qty,1000);require(received>=1&&received<=100000000&&cost<=1000000000000L&&integer(r,"receivedMilli",1,100000000)==received&&integer(r,"totalCost",0,1000000000000L)==cost);total=Math.addExact(total,cost);require(total<=MAX);lots.put(id,new Lot(r));
  }
  JSONArray input=s.getJSONArray("records");List<JSONObject> records=new ArrayList<>();for(int i=0;i<input.length();i++)records.add(input.getJSONObject(i));Collections.sort(records,(a,b)->{int c=a.optString("date").compareTo(b.optString("date"));if(c!=0)return c;c=Long.compare(a.optLong("created"),b.optLong("created"));return c!=0?c:a.optString("id").compareTo(b.optString("id"));});
  long shareTotal=0,clinicTotal=0;for(JSONObject r:records){require(r.get("costReviewed") instanceof Boolean);long divisor=integer(r,"divisorMilli",1,1000000);JSONArray cs=r.getJSONArray("consumptions");require(cs.length()<=1000&&(cs.length()==0||r.getBoolean("costReviewed")));Set<String> ids=new HashSet<>();long material=0;
   for(int j=0;j<cs.length();j++){JSONObject c=cs.getJSONObject(j);require(ids.add(text(c,"id",100,true)));Lot lot=lots.get(c.getString("receiptId"));require(lot!=null);if(lot.r.getString("date").compareTo(r.getString("date"))>0)throw new Exception("تاریخ مصرف نباید پیش از تاریخ تحویل ماده باشد.");long used=Math.addExact(lot.used,integer(c,"quantityMilli",1,100000000));if(used>lot.r.getLong("receivedMilli"))throw new Exception("مقدار مصرف از موجودی محموله بیشتر است.");long after=ratio(lot.r.getLong("totalCost"),used,lot.r.getLong("receivedMilli"));material=Math.addExact(material,after-lot.cost);require(material<=MAX);lot.used=used;lot.cost=after;}
   long paid=0,fees=0;boolean known=true;JSONArray ps=r.getJSONArray("payments");for(int j=0;j<ps.length();j++){JSONObject p=ps.getJSONObject(j);require(p.has("feeBps"));paid+=p.getLong("amount");if(p.isNull("feeBps"))known=false;else fees+=ratio(p.getLong("amount"),integer(p,"feeBps",0,10000),10000);}
   if(r.getBoolean("costReviewed")&&known){long base=paid-fees-material,share=r.getString("shareMode").equals("percent")?ratio(base,r.getLong("doctorBps"),10000):ratio(base,1000,divisor);shareTotal=Math.addExact(shareTotal,share);clinicTotal=Math.addExact(clinicTotal,base-share);require(Math.abs(shareTotal)<=MAX&&Math.abs(clinicTotal)<=MAX);}
  }
 }
}
