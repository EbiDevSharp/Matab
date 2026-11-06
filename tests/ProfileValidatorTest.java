package ir.matab.desk;
import org.json.*;
import java.nio.file.*;
public class ProfileValidatorTest{
 public static void main(String[] args)throws Exception{
  JSONObject s=new JSONObject(new String(Files.readAllBytes(Paths.get(args[0])),java.nio.charset.StandardCharsets.UTF_8));ProfileValidator.validate(s);FinanceValidator.validate(s,date->true);
  for(String phone:new String[]{"0912345678","08123456789","091234567890","0912345678x"}){JSONObject bad=new JSONObject(s.toString());bad.getJSONArray("patients").getJSONObject(0).put("mobile",phone);boolean rejected=false;try{ProfileValidator.validate(bad);}catch(Exception expected){rejected=true;}if(!rejected)throw new AssertionError("bad mobile");}
  JSONObject invalid=new JSONObject(s.toString());invalid.getJSONObject("settings").put("doctorBps",10001);boolean rejected=false;try{ProfileValidator.validate(invalid);}catch(Exception expected){rejected=true;}if(!rejected)throw new AssertionError("bad share");
  if(FinanceValidator.ratio(3340000,6000,10000)!=2004000)throw new AssertionError("percentage");System.out.println("PASS: native customer profiles, strict mobile validation, doctor references, appearance and percentage share.");
 }
}
