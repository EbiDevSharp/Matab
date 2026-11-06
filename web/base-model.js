(function(root,factory){const model=factory();if(typeof module==='object'&&module.exports)module.exports=model;else root.MatabBaseModel=model})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const methodDefaults={card:'کارت',cash:'نقدی',transfer:'انتقال بانکی',snapppay:'اسنپ‌پی',digipay:'دیجی‌پی',other:'سایر'};
const normalize=s=>s.normalize('NFKC').replace(/ي/g,'ی').replace(/ك/g,'ک').replace(/[\u200c\u200d]/g,' ').trim().replace(/\s+/g,' ').toLocaleLowerCase('fa');
const entries=(kind,names)=>names.map((name,i)=>({id:kind+'-'+(i+1),name,active:true}));
function defaults(){return {services:entries('service',['تزریق ژل','تزریق بوتاکس','مزوتراپی','اسکین‌بوستر','تزریق عضلانی','سایر خدمات']),products:[],areas:entries('area',['لب','خط خنده','پیشانی','دور چشم','چانه','گونه','صورت','بدن']),methods:Object.entries(methodDefaults).map(([id,name])=>({id,name,active:true}))}}
function fresh(){return {version:3,clinic:'مطب من',catalogs:defaults(),records:[],lastBackup:null}}
function validate(v,parseDate){
 const bad=()=>{throw Error('invalid')},money=n=>Number.isSafeInteger(n)&&n>=0&&n<=1e12,text=(s,max)=>typeof s==='string'&&s.length<=max,id=(s,max)=>text(s,max)&&!!s&&!/[\u0000-\u001f]/.test(s);
 if(!v||![1,2,3].includes(v.version)||!Array.isArray(v.records)||!text(v.clinic,80)||v.records.length>100000)bad();
 let catalogs=defaults();
 if(v.version===3){if(!v.catalogs||typeof v.catalogs!=='object')bad();catalogs={};for(const kind of ['services','products','areas','methods']){const list=v.catalogs[kind];if(!Array.isArray(list)||list.length>1000)bad();const ids=new Set(),names=new Set();catalogs[kind]=list.map(c=>{if(!c||!id(c.id,100)||c.id==='unknown'||ids.has(c.id)||!text(c.name,80)||!normalize(c.name)||names.has(normalize(c.name))||typeof c.active!=='boolean')bad();ids.add(c.id);names.add(normalize(c.name));return {id:c.id,name:c.name.trim(),active:c.active}})}}
 const records=[],ids=new Set();let total=0;
 for(const r of v.records){if(!r||!id(r.id,100)||ids.has(r.id)||!Number.isSafeInteger(r.created)||r.created<0||!parseDate(r.date)||parseDate(r.date).key!==r.date||!money(r.price)||!money(r.amount)||!Number.isFinite(r.volume)||r.volume<=0||r.volume>100000||!['cc','unit','session'].includes(r.unit))bad();ids.add(r.id);
 for(const [key,max] of Object.entries({patient:161,service:80,product:80,area:80,note:500}))if(!text(r[key],max))bad();if(!r.service.trim()||!r.area.trim())bad();
 if(v.version<3){for(const [kind,value] of [['services',r.service],['products',r.product],['areas',r.area]])if(value&&!catalogs[kind].some(c=>normalize(c.name)===normalize(value)))catalogs[kind].push({id:'import-'+kind+'-'+catalogs[kind].length,name:value,active:true})}
 let source=r.payments;
 if(v.version===1){if(!money(r.paid)||r.paid>r.amount)bad();source=r.paid?[{id:'legacy-'+r.id,amount:r.paid,date:null,method:'unknown',stage:'legacy',note:'مبلغ تجمیعی نسخه قبلی؛ تاریخ و روش پرداخت ثبت نشده است.',legacy:true}]:[]}
 if(!Array.isArray(source)||source.length>1000)bad();const paymentIds=new Set();let paid=0;
 const payments=source.map(p=>{if(!p||!id(p.id,120)||paymentIds.has(p.id)||!money(p.amount)||p.amount===0||!text(p.note,200)||typeof p.legacy!=='boolean'||!['deposit','payment','settlement','legacy'].includes(p.stage)||(p.date===null?!p.legacy:!parseDate(p.date)||parseDate(p.date).key!==p.date)||(!p.legacy&&(p.method==='unknown'||p.stage==='legacy')))bad();paymentIds.add(p.id);const method=catalogs.methods.find(c=>c.id===p.method);if(!method&&!(p.legacy&&p.method==='unknown'))bad();const methodLabel=v.version===3?p.methodLabel:method?.name||'نامشخص (ثبت قبلی)';if(!text(methodLabel,80)||!methodLabel.trim())bad();paid+=p.amount;return {id:p.id,amount:p.amount,date:p.date,method:p.method,methodLabel,stage:p.stage,note:p.note,legacy:p.legacy}});
 if(!Number.isSafeInteger(paid)||paid>r.amount)bad();total+=r.amount;if(!Number.isSafeInteger(total))bad();
 records.push({...Object.fromEntries(['id','created','date','patient','service','product','area','note','volume','unit','price','amount'].map(k=>[k,r[k]])),paid,payments});
 }
 for(const list of Object.values(catalogs))if(list.length>1000)bad();
 return {version:3,clinic:v.clinic.trim()||'مطب من',catalogs,records,lastBackup:typeof v.lastBackup==='string'&&parseDate(v.lastBackup)?v.lastBackup:null};
}
return {normalize,defaults,fresh,validate};
});
