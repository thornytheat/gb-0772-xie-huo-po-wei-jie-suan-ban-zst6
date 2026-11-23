from collections import Counter

from app.billing.payments import index
from app.curb.timeaxis import count


def accounting(prices,payments,survey,coverage,disputes):
    notes,isolated=index(payments,survey)
    lines=[]
    for stay in prices:
        matches=notes.pop((stay['berth'],stay['vehicle'],stay['start']),[])
        paid=sum(r['cents'] for r in matches)
        delta=paid-stay['due_cents']
        code='NO_PAYMENT' if not matches else 'MATCH' if delta==0 else 'GAP'
        lines.append({'stay':stay['stay'],'berth':stay['berth'],'vehicle':stay['vehicle'],'arrival':stay['start'],
                      'due_cents':stay['due_cents'],'paid_cents':paid,'difference_cents':delta,'code':code,'receipts':matches})
    orphans=[row | {'code':'ORPHAN'} for matches in notes.values() for row in matches]
    duration=count(survey.start,survey.end)
    categories=Counter()
    for row in prices:
        for segment in row['segments']:
            if segment['code'] in {'FREE','BASE','UPGRADE'}:
                categories[row['berth'],segment['code']]+=segment['minutes']
    occupied_by_berth=Counter(berth for berth,_ in coverage)
    disputed_by_berth=Counter(berth for berth,_ in disputes)
    balance=[]
    for berth in survey.berths:
        balance.append({'berth':berth,'scheduled':duration,'vacant':duration-occupied_by_berth[berth],
                        'disputed':disputed_by_berth[berth],'free':categories[berth,'FREE'],
                        'base':categories[berth,'BASE'],'upgrade':categories[berth,'UPGRADE']})
    totals={key:sum(r[key] for r in balance) for key in ('scheduled','vacant','disputed','free','base','upgrade')}
    money={key:sum(r[key] for r in lines) for key in ('due_cents','paid_cents','difference_cents')}
    money['orphan_cents']=sum(row['cents'] for row in orphans)
    return {'lines':lines,'isolated':isolated,'orphans':orphans,'berths':balance,'totals':totals,'money':money}
