"""杆侧停测申报与待核分钟。

停测只是申报，不是观测结论。对每一泊位分钟按以下次序划定：

1. 该分钟有任一被采信的杆侧检测覆盖 → 已核实，随实际停靠正常结案出账；
2. 该分钟落在停测申报内且没有任何检测 → 待核，既不算空闲也不出账；
3. 其余分钟才是真正的空闲。

同一泊位若还有另一根杆报了部分停靠，只有它实际覆盖到的停测分钟会被认作
已核实；申报内的其余分钟仍留在待核。因此既不会把缺测整段当成空位，也不
用一个泊位的待核拖住其余泊位或整批结案。
"""

from collections import defaultdict

from app.curb.timeaxis import M, count, minute


def _iso(value):
    return value.isoformat() if hasattr(value,'isoformat') else str(value)


def ranges(minutes):
    """把无序分钟集合压成半开区间，供页面和证据复核。"""
    blocks=[]
    for when in sorted(minutes):
        if blocks and blocks[-1]['_end']==when:
            blocks[-1]['_end']=when+M
        else:
            blocks.append({'_start':when,'_end':when+M})
    return [{'start':_iso(block['_start']),'end':_iso(block['_end']),
             'minutes':count(block['_start'],block['_end'])} for block in blocks]


def prepare(rows,survey):
    """校验停测申报并按 (sensor,berth,start,end) 去重。

    申报可来自 ``survey.outages`` 或可选的 ``outages.csv``；``sensor`` 留空
    表示整泊位停测。同一申报只保留最小行号，其余记 ``DUPLICATE``。未知
    泊位、倒置区间和窗外申报按原码隔离。
    """
    usable,rejects=[],[]
    for row in rows:
        fields=row['fields']
        try:
            start,end=(minute(fields[key]) for key in ('start','end'))
            if fields['berth'] not in survey.berths:
                raise ValueError('UNKNOWN_BERTH')
            if end<=start:
                raise ValueError('INTERVAL')
            if not survey.start<=start<end<=survey.end:
                raise ValueError('RANGE')
        except ValueError as error:
            rejects.append(row | {'code':str(error)})
            continue
        usable.append(row | {'start':start,'end':end,'berth':fields['berth'],
                             'sensor':(fields.get('sensor') or '').strip()})
    chosen,duplicates,seen=[],[],set()
    for row in sorted(usable,key=lambda r:(r['line'],r['source'])):
        key=(row['sensor'],row['berth'],row['start'],row['end'])
        if key in seen:
            duplicates.append(row | {'code':'DUPLICATE'})
        else:
            seen.add(key)
            chosen.append(row)
    return chosen,rejects+duplicates


def declared_rows(survey):
    """把 ``survey.outages`` 展开成与 CSV 同构的原始行。"""
    return [{'line':index,'source':'survey','fields':dict(entry)}
            for index,entry in enumerate(survey.outages,start=1)]


def readings(stops):
    """逐泊位分钟收集检测来源，作为停测分钟能否结案的证据。"""
    sources=defaultdict(set)
    for stop in stops:
        for detection in stop['detections']:
            sensor=(detection['fields'].get('sensor') or '').strip()
            for offset in range(count(detection['start'],detection['end'])):
                sources[detection['berth'],detection['start']+offset*M].add(sensor)
    return sources


def review(declarations,stops):
    """按泊位划定停测、已核实与待核分钟。

    结论只依赖被采信的检测：停测申报不会吞掉已观测的分钟，检测也不会被
    申报扩大成整段占用。``pending_by_berth`` 供对账从空闲中扣除待核分钟。
    """
    sources=readings(stops)
    declared=defaultdict(set)
    sensors=defaultdict(set)
    for row in declarations:
        for offset in range(count(row['start'],row['end'])):
            when=row['start']+offset*M
            declared[row['berth']].add(when)
            sensors[row['berth'],when].add(row['sensor'])

    def other_pole(berth,when):
        """申报了某根杆停测、却由另一根杆记到该分钟。"""
        if not sources.get((berth,when)):
            return False
        declared_here=sensors[berth,when]
        if '' in declared_here:
            return False
        return bool(sources[berth,when]-declared_here)

    details=[]
    for row in sorted(declarations,key=lambda r:(r['berth'],r['start'],r['sensor'],r['line'])):
        minutes={row['start']+offset*M for offset in range(count(row['start'],row['end']))}
        verified={when for when in minutes if sources.get((row['berth'],when))}
        others={when for when in verified if other_pole(row['berth'],when)}
        details.append({'sensor':row['sensor'],'berth':row['berth'],
                        'start':_iso(row['start']),'end':_iso(row['end']),
                        'declared_minutes':len(minutes),'covered_minutes':len(verified),
                        'other_pole_minutes':len(others),
                        'pending_minutes':len(minutes-verified),
                        'pending_ranges':ranges(minutes-verified),
                        'covered_ranges':ranges(verified),
                        'other_pole_ranges':ranges(others)})

    berths=[]
    for berth in sorted(declared):
        minutes=declared[berth]
        verified={when for when in minutes if sources.get((berth,when))}
        others={when for when in verified if other_pole(berth,when)}
        berths.append({'berth':berth,'outage_minutes':len(minutes),
                       'covered_minutes':len(verified),'other_pole_minutes':len(others),
                       'pending_minutes':len(minutes-verified),
                       'pending_ranges':ranges(minutes-verified),
                       'covered_ranges':ranges(verified),
                       'other_pole_ranges':ranges(others)})

    total=lambda key:sum(row[key] for row in berths)
    return {'declared':details,'berths':berths,
            'outage_minutes':total('outage_minutes'),'covered_minutes':total('covered_minutes'),
            'other_pole_minutes':total('other_pole_minutes'),'pending_minutes':total('pending_minutes'),
            'pending_by_berth':{row['berth']:row['pending_minutes'] for row in berths},
            'other_poles':sorted({row['sensor'] for row in declarations if row['sensor']})}
