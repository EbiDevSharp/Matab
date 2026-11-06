"""Customer registry, doctor and appearance validation for state schema 5."""
import re

def validate_profiles(v):
    def require(ok,message='مشخصات مشتری، پزشک یا تنظیمات معتبر نیست.'):
        if not ok:raise ValueError(message)
    def text(s,n):return isinstance(s,str) and len(s)<=n
    def integer(n,lo,hi):return type(n) is int and lo<=n<=hi
    def mobile(value):return isinstance(value,str) and (value=='' or re.fullmatch(r'09[0-9]{9}',value) is not None)
    def name(p):return ' '.join(s for s in [p['firstName'],p['lastName']] if s).strip() or p['legacyName']
    settings=v.get('settings');require(isinstance(settings,dict) and settings.get('shareMode') in ('divisor','percent') and integer(settings.get('doctorBps'),0,10000))
    appearance=settings.get('appearance');require(isinstance(appearance,dict) and appearance.get('font') in ('vazirmatn','shabnam','sahel','system') and appearance.get('palette') in ('mint','blue','violet','dark','auto') and integer(appearance.get('scale'),80,150))
    doctors={d['id'] for d in v['catalogs']['doctors']};require(settings.get('defaultDoctorId') is None or settings['defaultDoctorId'] in doctors)
    patients=v.get('patients');require(isinstance(patients,list) and len(patients)<=100000);ids=set()
    for p in patients:
        require(isinstance(p,dict) and text(p.get('id'),100) and bool(p['id']) and p['id'] not in ids and integer(p.get('created'),0,9007199254740991) and text(p.get('firstName'),80) and text(p.get('lastName'),80) and text(p.get('legacyName'),161) and mobile(p.get('mobile')))
        require(any(p[k].strip() for k in ('firstName','lastName','legacyName','mobile')));ids.add(p['id'])
    for r in v['records']:
        require(text(r.get('firstName'),80) and text(r.get('lastName'),80) and text(r.get('legacyName'),161) and mobile(r.get('mobile')) and (r.get('patientId') is None or r['patientId'] in ids) and (r.get('doctorId') is None or r['doctorId'] in doctors) and text(r.get('doctorLabel'),80) and r.get('shareMode') in ('divisor','percent') and integer(r.get('doctorBps'),0,10000))
        require((r['doctorId'] is None and r['doctorLabel']=='') or (r['doctorId'] is not None and bool(r['doctorLabel'].strip())))
        require(r['patient']==name(r));require(r['patientId'] is not None or (not name(r) and not r['mobile']))
    owners={}
    for receipt in v.get('receipts',[]):
        if receipt.get('doctorId') is not None:
            require(receipt['doctorId'] in doctors and text(receipt.get('doctorLabel'),80) and bool(receipt['doctorLabel'].strip()));owners[receipt['id']]=receipt['doctorId']
    for record in v['records']:
        for use in record.get('consumptions',[]):require(use['receiptId'] not in owners or owners[use['receiptId']]==record['doctorId'],'پزشک خدمت با پزشک مواد مصرفی یکسان نیست.')
    return v
