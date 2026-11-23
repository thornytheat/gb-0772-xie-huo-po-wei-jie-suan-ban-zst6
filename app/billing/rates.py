from collections import Counter

from app.curb.timeaxis import LOCAL, M, span
from app.setup import BASE_CENTS, FREE_MINUTES, TIER_LIMIT, UPGRADE_CENTS


def price(stops,disputes):
    by_car_day=Counter()
    free_by_stay=Counter()
    by_stay={r['stay']:[] for r in stops}
    ordered=sorted((when,s['berth'],s['stay'],s) for s in stops for when in span(s['start'],s['end']))
    for when,berth,key,s in ordered:
        day=when.astimezone(LOCAL).date().isoformat()
        if (berth,when) in disputes:
            code,cents=disputes[berth,when],0
        elif s['booking'] and when<s['booking']['end'] and free_by_stay[key]<FREE_MINUTES:
            free_by_stay[key]+=1
            code,cents='FREE',0
        else:
            counter=(s['vehicle'],day)
            code,cents=('BASE',BASE_CENTS) if by_car_day[counter]<TIER_LIMIT else ('UPGRADE',UPGRADE_CENTS)
            by_car_day[counter]+=1
        by_stay[key].append((when,day,code,cents))
    output=[]
    for s in stops:
        slices=[]
        for when,day,code,cents in by_stay[s['stay']]:
            if not slices or (slices[-1]['day'],slices[-1]['code'])!=(day,code):
                slices.append({'start':when.isoformat(),'end':(when+M).isoformat(),'day':day,
                               'code':code,'minutes':0,'rate_cents':cents,'cents':0})
            segment=slices[-1]
            segment.update(end=(when+M).isoformat(),minutes=segment['minutes']+1,cents=segment['cents']+cents)
        output.append(s | {'segments':slices,'due_cents':sum(segment['cents'] for segment in slices)})
    return output
