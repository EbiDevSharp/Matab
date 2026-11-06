#!/usr/bin/env python3
"""Build a standalone, signed APK using Android SDK tools + Eclipse ECJ.
Set ANDROID_BUILD_TOOLS, ANDROID_JAR, ECJ_JAR; java/keytool must be on PATH.
Signing material is created once under signing/ and MUST be retained for updates.
"""
import os,shutil,subprocess,pathlib,secrets,zipfile
ROOT=pathlib.Path(__file__).resolve().parent.parent
TOOLS=pathlib.Path(os.environ['ANDROID_BUILD_TOOLS'])
JAR=pathlib.Path(os.environ['ANDROID_JAR']);ECJ=pathlib.Path(os.environ['ECJ_JAR'])
BUILD=ROOT/'build'/'android';BUILD.mkdir(parents=True,exist_ok=True)
SIGN=ROOT/'signing';SIGN.mkdir(exist_ok=True)
KEY=SIGN/'matab-release.p12';PASSWORD=SIGN/'password.txt'
if not PASSWORD.exists():PASSWORD.write_text(secrets.token_urlsafe(36));PASSWORD.chmod(0o600)
env=os.environ.copy();env['MATAB_SIGN_PASSWORD']=PASSWORD.read_text().strip()
def run(*args):subprocess.run([str(a) for a in args],check=True,env=env)
if not KEY.exists():run('keytool','-genkeypair','-keystore',KEY,'-storetype','PKCS12','-alias','matab','-keyalg','RSA','-keysize','3072','-validity','36500','-dname','CN=Matab Desk, OU=Independent App, O=Matab Desk','-storepass:env','MATAB_SIGN_PASSWORD','-keypass:env','MATAB_SIGN_PASSWORD');KEY.chmod(0o600)
ASSETS=BUILD/'assets';(ASSETS/'www').mkdir(parents=True,exist_ok=True)
for f in (ROOT/'web').rglob('*'):
 if f.is_file() and not any(part.startswith('qa-') for part in f.relative_to(ROOT/'web').parts):
  target=ASSETS/'www'/f.relative_to(ROOT/'web');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
for n in ('schema.sql','calendar-years.json','releases.json'):shutil.copy2(ROOT/n,ASSETS/n)
CLASSES=BUILD/'classes';CLASSES.mkdir(exist_ok=True)
run('java','-jar',ECJ,'-source','8','-target','8','-encoding','UTF-8','-warn:-deprecation','-classpath',JAR,'-d',CLASSES,*sorted((ROOT/'android'/'src').rglob('*.java')))
run(TOOLS/'aapt2','compile','--dir',ROOT/'android'/'res','-o',BUILD/'res.zip')
run(TOOLS/'aapt2','link','--auto-add-overlay','-o',BUILD/'resources.apk','--manifest',ROOT/'android'/'AndroidManifest.xml','-I',JAR,'-A',ASSETS,'-R',BUILD/'res.zip')
DEX=BUILD/'dex';DEX.mkdir(exist_ok=True)
run('java','-cp',TOOLS/'lib'/'d8.jar','com.android.tools.r8.D8','--lib',JAR,'--min-api','26','--output',DEX,*CLASSES.rglob('*.class'))
UNSIGNED=BUILD/'unsigned.apk';shutil.copy2(BUILD/'resources.apk',UNSIGNED)
with zipfile.ZipFile(UNSIGNED,'a',zipfile.ZIP_DEFLATED) as z:
 for dex in DEX.glob('*.dex'):z.write(dex,dex.name)
run(TOOLS/'zipalign','-p','-f','4',UNSIGNED,BUILD/'aligned.apk')
OUT=ROOT/'deliverables';OUT.mkdir(exist_ok=True)
run('java','-jar',TOOLS/'lib'/'apksigner.jar','sign','--ks',KEY,'--ks-type','PKCS12','--ks-key-alias','matab','--ks-pass','env:MATAB_SIGN_PASSWORD','--out',OUT/'MatabDesk-Android.apk',BUILD/'aligned.apk')
run('java','-jar',TOOLS/'lib'/'apksigner.jar','verify','--verbose',OUT/'MatabDesk-Android.apk')
print('APK built and signature verified:',OUT/'MatabDesk-Android.apk')
