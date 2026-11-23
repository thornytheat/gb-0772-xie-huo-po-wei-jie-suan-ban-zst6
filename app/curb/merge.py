from collections import defaultdict
from hashlib import sha256

from app.curb.timeaxis import count


def stays(detections):
    buckets=defaultdict(list)
    for row in detections:
        buckets[(row['berth'],row['vehicle'])].append(row)
    merged=[]
    for (berth,vehicle),rows in sorted(buckets.items()):
        group=None
        for row in sorted(rows,key=lambda r:(r['start'],r['end'],r['line'])):
            if group is None or row['start']>group['end']:
                group={'berth':berth,'vehicle':vehicle,'start':row['start'],'end':row['end'],'detections':[row]}
                merged.append(group)
            else:
                group['end']=max(group['end'],row['end'])
                group['detections'].append(row)
    for s in merged:
        data=f"{s['berth']}|{s['vehicle']}|{s['start'].isoformat()}"
        s['stay']=sha256(data.encode()).hexdigest()[:20]
        s['minutes']=count(s['start'],s['end'])
        s['observed_minutes']=sum(count(r['start'],r['end']) for r in s['detections'])
    return sorted(merged,key=lambda r:(r['start'],r['berth'],r['vehicle']))
