package ir.matab.desk;
import android.app.*;
import android.os.*;
import android.content.*;
import android.net.Uri;
import android.webkit.*;
import android.view.*;
import android.widget.*;
import android.print.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {
 private WebView web; private LocalDatabase database; private ValueCallback<Uri[]> chooser;
 private String exportText;private static final int EXPORT=601,IMPORT=602;
 private static final String HOST="appassets.androidplatform.net";
 private static String error(String message){try{return new JSONObject().put("error",message).toString();}catch(Exception e){return "{}";}}
 @Override public void onCreate(Bundle state){super.onCreate(state);try{database=new LocalDatabase(this);database.getWritableDatabase();}catch(Exception e){new AlertDialog.Builder(this).setTitle("دفتر مطب").setMessage("پایگاه داده باز نشد. فضای حافظه دستگاه را بررسی کنید.").setPositiveButton("بستن",(d,w)->finish()).show();return;}
  getWindow().setStatusBarColor(0xff137b68);getWindow().setNavigationBarColor(0xfff6f8fa);getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
  android.widget.FrameLayout root=new android.widget.FrameLayout(this);root.setBackgroundColor(0xfff6f8fa);root.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());return insets.consumeSystemWindowInsets();});
  web=new WebView(this);root.addView(web,new android.widget.FrameLayout.LayoutParams(-1,-1));setContentView(root);
  WebSettings settings=web.getSettings();settings.setJavaScriptEnabled(true);settings.setDomStorageEnabled(false);settings.setAllowFileAccess(false);settings.setAllowContentAccess(true);settings.setAllowFileAccessFromFileURLs(false);settings.setAllowUniversalAccessFromFileURLs(false);settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);settings.setJavaScriptCanOpenWindowsAutomatically(false);settings.setSupportMultipleWindows(false);settings.setGeolocationEnabled(false);settings.setMediaPlaybackRequiresUserGesture(true);
  web.addJavascriptInterface(new Bridge(),"MatabNative");
  web.setWebViewClient(new WebViewClient(){
   @Override public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){return !owned(r.getUrl());}
   @Override public WebResourceResponse shouldInterceptRequest(WebView v,WebResourceRequest r){Uri u=r.getUrl();if(!owned(u))return denied();String name=u.getPath();if(name==null||name.equals("/"))name="/index.html";name=name.substring(1);if(name.contains("..")||!name.matches("[A-Za-z0-9_./-]+"))return denied();try{String mime=name.endsWith(".js")?"text/javascript":name.endsWith(".css")?"text/css":name.endsWith(".html")?"text/html":name.endsWith(".png")?"image/png":name.endsWith(".svg")?"image/svg+xml":name.endsWith(".ttf")?"font/ttf":"application/octet-stream";return new WebResourceResponse(mime,"UTF-8",getAssets().open("www/"+name));}catch(Exception e){return denied();}}
  });
  web.setWebChromeClient(new WebChromeClient(){@Override public boolean onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams params){if(chooser!=null)chooser.onReceiveValue(null);chooser=callback;Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("application/json");try{startActivityForResult(i,IMPORT);}catch(Exception e){chooser.onReceiveValue(null);chooser=null;}return true;}});
  web.loadUrl("https://"+HOST+"/index.html");
 }
 private static boolean owned(Uri u){return "https".equals(u.getScheme())&&HOST.equals(u.getHost())&&u.getPort()==-1;}
 private static WebResourceResponse denied(){return new WebResourceResponse("text/plain","UTF-8",new ByteArrayInputStream(new byte[0]));}
 public final class Bridge {
  @JavascriptInterface public String readState(){try{return database.read().toString();}catch(Exception e){return error("خواندن پایگاه داده ممکن نشد.");}}
  @JavascriptInterface public String writeState(String body){try{if(body.length()>20*1024*1024)return error("حجم اطلاعات بیش از حد مجاز است.");return database.write(new JSONObject(body)).toString();}catch(Exception e){return error(e.getMessage()!=null&&e.getMessage().startsWith("اطلاعات")?e.getMessage():"ذخیره در پایگاه داده انجام نشد؛ اطلاعات قبلی حفظ شده است.");}}
  @JavascriptInterface public String readHistory(String query){try{return database.history(new JSONObject(query)).toString();}catch(Exception e){return error("خواندن تاریخچه ممکن نشد.");}}
  @JavascriptInterface public String releaseHistory(){try{return database.releases().toString();}catch(Exception e){return error("خواندن نسخه‌ها ممکن نشد.");}}
  @JavascriptInterface public String backupData(String scope){try{return database.backup(scope).toString();}catch(Exception e){return error("ساخت پشتیبان ممکن نشد.");}}
  @JavascriptInterface public String backupEvent(String scope,String destination){try{database.backupEvent(scope,destination);return "{\"ok\":true}";}catch(Exception e){return error("ثبت رویداد پشتیبان ممکن نشد.");}}
  @JavascriptInterface public String storageInfo(){try{return new JSONObject().put("engine","SQLite").put("location","SQLite · حافظه داخلی برنامه روی گوشی").toString();}catch(Exception e){return "{}";}}
  @JavascriptInterface public void contactEmail(String subject,String body){runOnUiThread(()->{try{Intent mail=new Intent(Intent.ACTION_SENDTO,Uri.parse("mailto:ebrahim.13631119@gmail.com?subject="+Uri.encode(subject)+"&body="+Uri.encode(body)));mail.putExtra(Intent.EXTRA_SUBJECT,subject);mail.putExtra(Intent.EXTRA_TEXT,body);startActivity(mail);}catch(Exception e){Toast.makeText(MainActivity.this,"برنامه ایمیل نصب نیست؛ متن را به ایمیل نمایش‌داده‌شده ارسال کنید.",Toast.LENGTH_LONG).show();}});}
  @JavascriptInterface public void exportFile(String text,String type,String name){runOnUiThread(()->{if(exportText!=null){Toast.makeText(MainActivity.this,"ابتدا ذخیره فایل قبلی را تمام کنید.",Toast.LENGTH_SHORT).show();return;}exportText=text;Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType(type.startsWith("text/csv")?"text/csv":"application/json");i.putExtra(Intent.EXTRA_TITLE,name.replaceAll("[/\\\\]","_"));try{startActivityForResult(i,EXPORT);}catch(Exception e){exportText=null;fileResult(false);}});}
  @JavascriptInterface public void printPage(){runOnUiThread(()->{PrintManager manager=(PrintManager)getSystemService(PRINT_SERVICE);manager.print("دفتر مطب",web.createPrintDocumentAdapter("دفتر مطب"),new PrintAttributes.Builder().build());});}
 }
 private void fileResult(boolean ok){if(web!=null)web.evaluateJavascript("window.MatabExportResult&&window.MatabExportResult("+ok+")",null);}
 @Override protected void onActivityResult(int request,int result,Intent intent){super.onActivityResult(request,result,intent);if(request==IMPORT){if(chooser!=null){chooser.onReceiveValue(result==RESULT_OK&&intent!=null&&intent.getData()!=null?new Uri[]{intent.getData()}:null);chooser=null;}return;}if(request==EXPORT){boolean ok=false;try{if(result==RESULT_OK&&intent!=null&&intent.getData()!=null&&exportText!=null){try(OutputStream out=getContentResolver().openOutputStream(intent.getData(),"wt")){if(out==null)throw new IOException();out.write(exportText.getBytes(StandardCharsets.UTF_8));ok=true;}}}catch(Exception e){}finally{exportText=null;fileResult(ok);}}}
 @Override public void onBackPressed(){if(web==null){finish();return;}web.evaluateJavascript("(()=>{let d=[...document.querySelectorAll('dialog[open]')];if(d.length){d[d.length-1].close();return true}if(location.hash&&location.hash!=='#overview'){location.hash='overview';return true}return false})()",value->{if(!"true".equals(value))finish();});}
 @Override protected void onDestroy(){if(chooser!=null)chooser.onReceiveValue(null);if(web!=null){web.removeJavascriptInterface("MatabNative");web.destroy();}if(database!=null)database.close();super.onDestroy();}
}
