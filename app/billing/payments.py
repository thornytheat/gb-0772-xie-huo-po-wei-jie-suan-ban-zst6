from collections import defaultdict
import re

from app.curb.timeaxis import minute
from app.source.dedup import resolve


def index(rows,survey):
    ready,isolated=[],[]
    for row in rows:
        fields=row['fields']
        try:
            at=minute(fields['arrival'])
            if fields['berth'] not in survey.berths:
                raise ValueError('UNKNOWN_BERTH')
            if not fields['receipt'].strip():
                raise ValueError('UNSET')
            if not re.fullmatch(r'[0-9]{1,9}',fields['cents']):
                raise ValueError('AMOUNT')
        except ValueError as error:
            isolated.append(row | {'code':str(error)})
            continue
        ready.append(row | {'arrival':at,'berth':fields['berth'],'cents':int(fields['cents'])})
    chosen,rejected=resolve(ready,lambda r:r['fields']['receipt'],lambda r:(r['arrival'],r['vehicle'],r['berth'],r['cents']))
    attached=defaultdict(list)
    for row in chosen:
        attached[row['berth'],row['vehicle'],row['arrival']].append(row)
    return attached,isolated+rejected
