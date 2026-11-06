(function(root,factory){const value=factory(typeof module==='object'&&module.exports?require('./model.js'):root.MatabModel);if(typeof module==='object'&&module.exports)module.exports=value;else root.MatabBackup=value})(typeof globalThis!=='undefined'?globalThis:this,function(M){
'use strict';
function restoreSettings(current,file,parseDate){
 if(file?.format!=='matab-settings'||file.formatVersion!==1)throw Error('فایل پشتیبان تنظیمات معتبر نیست.');
 const incoming=M.validate({...M.fresh(),clinic:file.clinic,settings:file.settings,catalogs:file.catalogs},parseDate),next=structuredClone(current),doctorMap=new Map();
 for(const kind of Object.keys(next.catalogs)){
  const existing=next.catalogs[kind],used=new Set();for(const row of existing)row.active=false;
  for(const row of incoming.catalogs[kind]){const byId=existing.find(c=>c.id===row.id),byName=existing.find(c=>M.normalize(c.name)===M.normalize(row.name));
   if(byId&&byName&&byId.id!==byName.id)throw Error('نام‌های فهرست '+kind+' در بانک و پشتیبان با هم تداخل دارند. ابتدا نام‌های مشابه را در تنظیمات اصلاح کنید.');
   const target=byId||byName,targetId=target?.id||row.id;if(used.has(targetId))throw Error('چند گزینه پشتیبان به یک گزینه فعلی اشاره می‌کنند؛ فهرست‌ها را پیش از بازیابی اصلاح کنید.');used.add(targetId);if(target){const id=target.id;Object.assign(target,row,{id});if(kind==='doctors')doctorMap.set(row.id,id)}else{existing.push({...row});if(kind==='doctors')doctorMap.set(row.id,row.id)}
  }
 }
 next.clinic=incoming.clinic;next.settings={...incoming.settings,defaultDoctorId:incoming.settings.defaultDoctorId===null?null:doctorMap.get(incoming.settings.defaultDoctorId)};
 return M.validate(next,parseDate);
}
function decode(current,file,parseDate){
 if(file?.format==='matab-settings')return {state:restoreSettings(current,file,parseDate),operation:'restore-settings',history:null};
 if(file?.format){if(file.format!=='matab-backup'||file.formatVersion!==1||!Array.isArray(file.history))throw Error('قالب فایل پشتیبان پشتیبانی نمی‌شود.');return {state:M.validate(file.state,parseDate),history:file.history,operation:'restore'}}
 return {state:M.validate(file,parseDate),history:null,operation:'restore'};
}
return {restoreSettings,decode};
});
