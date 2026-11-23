from dataclasses import dataclass
from datetime import datetime
import re

from app.curb.timeaxis import M, minute
from app.problems import DocketError

SCHEMAS={
    'sensors':'event,berth,plate,sensor,start,end',
    'bookings':'reservation,berth,plate,effective,start,end,state',
    'payments':'receipt,berth,plate,arrival,cents',
    'outages':'berth,sensor,start,end',
}
REQUIRED=('survey','sensors','bookings','payments')
NAMES=('survey',*SCHEMAS)


@dataclass(frozen=True)
class Survey:
    name: str
    start: datetime
    end: datetime
    berths: tuple[str,...]
    outages: tuple[dict,...]=()

    @classmethod
    def build(cls,obj):
        try:
            start,end=minute(obj['start']),minute(obj['end'])
            name=obj['name']
            ids=obj['berths']
            if (not isinstance(name,str) or not name.strip() or len(name)>70 or not start<end<=start+2880*M
                or not isinstance(ids,list) or not 1<=len(ids)<=12 or any(
                    not isinstance(x,str) or not re.fullmatch(r'[A-Z0-9-]{1,20}',x) for x in ids)
                or len(set(ids))!=len(ids)):
                raise ValueError
        except (KeyError,TypeError,ValueError):
            raise DocketError('SURVEY_BAD','清算区间或泊位列表错误') from None
        return cls(name,start,end,tuple(ids),declarations(obj.get('outages',[]),start,end,ids))


def declarations(raw,start,end,berths):
    """校验 ``survey.outages`` 里的停测申报。

    条目为 ``{berth,sensor?,start,end}``，``sensor`` 省略表示整泊位停测。
    区间半开且须落在审查窗口内；重复项保留，交由采信阶段按内容去重。
    """
    if not isinstance(raw,list) or len(raw)>500:
        raise DocketError('SURVEY_BAD','停测申报需为至多 500 条的列表')
    output=[]
    for entry in raw:
        if (not isinstance(entry,dict) or not {'berth','start','end'}<=set(entry)
            or any(not isinstance(entry[key],str) for key in ('berth','start','end'))
            or not isinstance(entry.get('sensor',''),str)):
            raise DocketError('SURVEY_BAD','停测申报字段无效')
        try:
            begin,finish=minute(entry['start']),minute(entry['end'])
        except ValueError:
            raise DocketError('SURVEY_BAD','停测申报时间戳无效') from None
        sensor=entry.get('sensor','').strip()
        if entry['berth'] not in berths or finish<=begin or not start<=begin<finish<=end:
            raise DocketError('SURVEY_BAD','停测申报超出清算窗口或泊位')
        output.append({'berth':entry['berth'],'sensor':sensor,
                       'start':entry['start'],'end':entry['end']})
    return tuple(output)
