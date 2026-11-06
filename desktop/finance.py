"""Integer-only inventory, processor-fee and share calculations."""
MAX_SAFE=9007199254740991
BASE_UNITS=('cc','unit','item')
PACK_UNITS=BASE_UNITS+('vial','box')
def ratio(amount,multiplier,denominator):
    if denominator<=0:raise ValueError('عدد تقسیم معتبر نیست.')
    value=amount*multiplier;sign=-1 if value<0 else 1
    result=sign*((abs(value)+denominator//2)//denominator)
    if abs(result)>MAX_SAFE:raise ValueError('مبلغ محاسباتی بیش از محدوده مجاز است.')
    return result
def inventory(state):
    lots={r['id']:{'receipt':r,'usedMilli':0,'costUsed':0} for r in state['receipts']};costs={}
    for r in sorted(state['records'],key=lambda r:(r['date'],r['created'],r['id'])):
        cost=0
        for c in r['consumptions']:
            lot=lots.get(c['receiptId'])
            if lot is None:raise ValueError('محموله مصرفی پیدا نشد.')
            receipt=lot['receipt']
            if receipt['date']>r['date']:raise ValueError('تاریخ مصرف نباید پیش از تاریخ تحویل ماده باشد.')
            used=lot['usedMilli']+c['quantityMilli']
            if used>receipt['receivedMilli']:raise ValueError('مقدار مصرف از موجودی محموله بیشتر است.')
            after=ratio(receipt['totalCost'],used,receipt['receivedMilli']);cost+=after-lot['costUsed'];lot['costUsed']=after;lot['usedMilli']=used
        if cost>MAX_SAFE:raise ValueError('مبلغ مصرفی بیش از محدوده مجاز است.')
        costs[r['id']]=cost
    return lots,costs
def validate_finance(v,date_ok):
    def require(ok,message='اطلاعات مالی یا موجودی معتبر نیست.'):
        if not ok:raise ValueError(message)
    def integer(n,lo,hi):return type(n) is int and lo<=n<=hi
    def text(s,n,needed=False):return isinstance(s,str) and len(s)<=n and (not needed or bool(s.strip()))
    settings=v.get('settings');require(isinstance(settings,dict) and integer(settings.get('divisorMilli'),1,1000000))
    for m in v['catalogs']['methods']:require(integer(m.get('feeBps'),0,10000))
    products={p['id'] for p in v['catalogs']['products']};ids=set();purchases=0;receipts=v.get('receipts');require(isinstance(receipts,list) and len(receipts)<=10000)
    for r in receipts:
        require(isinstance(r,dict) and text(r.get('id'),100,True) and r['id'] not in ids and integer(r.get('created'),0,MAX_SAFE) and date_ok(r.get('date')) and r.get('productId') in products and text(r.get('productLabel'),80,True) and integer(r.get('quantityMilli'),1,100000000) and integer(r.get('contentsMilli'),1,100000000) and r.get('packUnit') in PACK_UNITS and r.get('baseUnit') in BASE_UNITS and integer(r.get('unitPrice'),0,10**12) and text(r.get('note'),500));ids.add(r['id'])
        if r['packUnit'] in BASE_UNITS:require(r['packUnit']==r['baseUnit'] and r['contentsMilli']==1000)
        raw=r['quantityMilli']*r['contentsMilli'];require(raw<=MAX_SAFE and raw%1000==0)
        received=raw//1000;total=ratio(r['unitPrice'],r['quantityMilli'],1000)
        require(integer(received,1,100000000) and integer(total,0,10**12) and r.get('receivedMilli')==received and r.get('totalCost')==total);purchases+=total;require(purchases<=MAX_SAFE)
    for r in v['records']:
        require(type(r.get('costReviewed')) is bool and integer(r.get('divisorMilli'),1,1000000));cs=r.get('consumptions');require(isinstance(cs,list) and len(cs)<=1000 and (not cs or r['costReviewed']));cids=set()
        for c in cs:require(isinstance(c,dict) and text(c.get('id'),100,True) and c['id'] not in cids and c.get('receiptId') in ids and integer(c.get('quantityMilli'),1,100000000));cids.add(c['id'])
        for p in r['payments']:require('feeBps' in p and (p['feeBps'] is None or integer(p['feeBps'],0,10000)))
    _,costs=inventory(v)
    share_sum=0;clinic_sum=0
    for r in v['records']:
        fees=sum(ratio(p['amount'],p['feeBps'],10000) for p in r['payments'] if p['feeBps'] is not None)
        if r['costReviewed'] and all(p['feeBps'] is not None for p in r['payments']):
            base=sum(p['amount'] for p in r['payments'])-fees-costs[r['id']]
            share=ratio(base,r['doctorBps'],10000) if r['shareMode']=='percent' else ratio(base,1000,r['divisorMilli'])
            share_sum+=share;clinic_sum+=base-share;require(abs(share_sum)<=MAX_SAFE and abs(clinic_sum)<=MAX_SAFE)
    return v
