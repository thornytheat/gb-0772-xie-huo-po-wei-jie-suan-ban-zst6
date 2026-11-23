from collections import defaultdict

from app.curb.timeaxis import minute
from app.source.dedup import resolve


def revisions(rows,survey):
    usable,rejected=[],[]
    for row in rows:
        data=row['fields']
        try:
            start,end,at=(minute(data[key]) for key in ('start','end','effective'))
            if data['berth'] not in survey.berths:
                raise ValueError('UNKNOWN_BERTH')
            if end<=start:
                raise ValueError('INTERVAL')
            if data['state'] not in {'ACTIVE','CANCEL'}:
                raise ValueError('BAD_STATUS')
            if not data['reservation'].strip():
                raise ValueError('UNSET')
        except ValueError as error:
            rejected.append(row | {'code':str(error)})
            continue
        usable.append(row | {'start':start,'end':end,'effective':at,'state':data['state'],
                             'berth':data['berth'],'reservation':data['reservation']})
    active,duplicates=resolve(usable,lambda r:(r['reservation'],r['effective']),
                               lambda r:(r['vehicle'],r['berth'],r['start'],r['end'],r['state']))
    histories=defaultdict(list)
    for row in active+[r for r in duplicates if r['code']=='ID_CONFLICT']:
        histories[row['reservation']].append(row)
    return histories,rejected+duplicates


def at_arrival(stop,histories):
    plausible=[]
    for versions in histories.values():
        earlier=[item for item in versions if item['effective']<=stop['start']]
        if not earlier:
            continue
        newest=max(r['effective'] for r in earlier)
        current=[r for r in earlier if r['effective']==newest]
        if not any(r['vehicle']==stop['vehicle'] and r['berth']==stop['berth']
                   and r['start']<=stop['start']<r['end'] for r in current):
            continue
        if len(current)>1:
            plausible.extend((r,'ATTACH_CONFLICT') for r in current)
        else:
            plausible.append((current[0],'CANCELLED' if current[0]['state']=='CANCEL' else 'BOOKED'))
    plausible.sort(key=lambda item:(item[0]['start'],item[0]['reservation'],item[0]['line']))
    selected=next((row for row,code in plausible if code=='BOOKED'),None)
    if selected:
        code='BOOKED'
    elif any(code=='ATTACH_CONFLICT' for _,code in plausible):
        code='ATTACH_CONFLICT'
    else:
        code='CANCELLED' if plausible else 'WALK_IN'
    return selected,code,[r for r,_ in plausible]
