from app.curb.timeaxis import minute
from app.source.dedup import resolve


def prepare(rows,survey):
    usable,rejects=[],[]
    for row in rows:
        fields=row['fields']
        try:
            start,end=(minute(fields[k]) for k in ('start','end'))
            if fields['berth'] not in survey.berths:
                raise ValueError('UNKNOWN_BERTH')
            if not fields['event'].strip():
                raise ValueError('UNSET')
            if not fields['sensor'].strip():
                raise ValueError('UNKNOWN_SENSOR')
            if end<=start:
                raise ValueError('INTERVAL')
            if not survey.start<=start<end<=survey.end:
                raise ValueError('RANGE')
        except ValueError as error:
            rejects.append(row | {'code':str(error)})
            continue
        usable.append(row | {'start':start,'end':end,'berth':fields['berth']})
    active,duplicates=resolve(usable,lambda row:row['fields']['event'],
                               lambda r:(r['vehicle'],r['berth'],r['fields']['sensor'],r['start'],r['end']))
    return active,rejects+duplicates
