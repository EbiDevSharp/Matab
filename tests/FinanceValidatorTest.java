package ir.matab.desk;
import org.json.*;
import java.nio.file.*;
public class FinanceValidatorTest{
 public static void main(String[] args)throws Exception{
  JSONObject s=new JSONObject(new String(Files.readAllBytes(Paths.get(args[0])),java.nio.charset.StandardCharsets.UTF_8));FinanceValidator.validate(s,date->date.matches("[0-9]{4}/[0-9]{2}/[0-9]{2}"));
  if(FinanceValidator.ratio(5000000,1320,10000)!=660000||FinanceValidator.ratio(5000000-660000-1000000,1000,2000)!=1670000)throw new AssertionError();
  JSONObject bad=new JSONObject(s.toString());bad.getJSONArray("records").getJSONObject(0).getJSONArray("consumptions").getJSONObject(0).put("quantityMilli",11000);boolean rejected=false;try{FinanceValidator.validate(bad,date->true);}catch(Exception expected){rejected=true;}if(!rejected)throw new AssertionError("overdraw accepted");
  System.out.println("PASS: Android finance validator JVM parity, 13.2% commission, share and overdraw protection.");
 }
}
