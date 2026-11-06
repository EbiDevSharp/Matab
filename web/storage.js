/* SQLite is owned by the Android application or the local desktop server. */
(function(){'use strict';let revision=0;
async function api(path,body){const response=await fetch(path,{method:body?'POST':'GET',cache:'no-store',headers:{'Content-Type':'application/json','X-Matab-Token':window.MATAB_TOKEN||''},body:body?JSON.stringify(body):undefined});const result=await response.json();if(!response.ok)throw Error(result.error||'ذخیره‌سازی انجام نشد.');return result}
window.MatabStore={
 async load(){const result=window.MatabNative?JSON.parse(MatabNative.readState()):await api('/api/state');if(result.error)throw Error(result.error);revision=result.revision;return result.state},
 async save(state,operation='save',history=null){const result=window.MatabNative?JSON.parse(MatabNative.writeState(JSON.stringify({revision,state,operation,history}))):await api('/api/state',{revision,state,operation,history});if(result.error)throw Error(result.error);revision=result.revision;return result},
 async history(filters={}){const r=window.MatabNative?JSON.parse(MatabNative.readHistory(JSON.stringify(filters))):await api('/api/history?'+new URLSearchParams(filters));if(r.error)throw Error(r.error);return r},
 async releases(){const r=window.MatabNative?JSON.parse(MatabNative.releaseHistory()):await api('/api/releases');if(r.error)throw Error(r.error);return r},
 async backup(scope='full'){const r=window.MatabNative?JSON.parse(MatabNative.backupData(scope)):await api('/api/backup?scope='+scope);if(r.error)throw Error(r.error);return r},
 async backupEvent(scope,destination){const r=window.MatabNative?JSON.parse(MatabNative.backupEvent(scope,destination)):await api('/api/backup-event',{scope,destination});if(r.error)throw Error(r.error);return r},
 async info(){return window.MatabNative?JSON.parse(MatabNative.storageInfo()):await api('/api/info')}
};
})();
