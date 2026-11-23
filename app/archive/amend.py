"""晚到记录补齐后的更正留档。

更正引用原留档编号，在原记录上重算，不新增历史：

- 留档编号不变，原 manifest 的落档时间与摘要进入 ``history``；
- 同一份补齐输入重复提交得到相同证据摘要，直接复用，不重复更正；
- 更正前后各泊位的待核、空闲、争议与金额变化完整留痕，供交班结清。

待核分钟只有在补齐后仍无任何被采信检测覆盖时才继续保留；因此晚到记录
越多，可结案的分钟越多，其余泊位不必整批等待。
"""

from app.problems import DocketError
from app.setup import POLICY


def snapshot(record):
    """从留档中取可比的结算快照，缺项时按空处理。"""
    evidence=record.get('evidence') or {}
    account=evidence.get('settlement') or {}
    return {'berths':{row['berth']:row for row in account.get('berths') or []},
            'money':account.get('money') or {},
            'pending':(account.get('pending') or {}).get('by_berth') or {}}


def changes(before,after):
    """列出更正前后各泊位的待核、空闲、争议与分钟变化。"""
    lines=[]
    for berth in sorted(set(before['berths'])|set(after['berths'])):
        old=before['berths'].get(berth) or {}
        new=after['berths'].get(berth) or {}
        line={'berth':berth,
              'pending_before':old.get('pending',before['pending'].get(berth,0)),
              'pending_after':new.get('pending',after['pending'].get(berth,0)),
              'vacant_before':old.get('vacant',0),'vacant_after':new.get('vacant',0),
              'disputed_before':old.get('disputed',0),'disputed_after':new.get('disputed',0),
              'free_before':old.get('free',0),'free_after':new.get('free',0),
              'base_before':old.get('base',0),'base_after':new.get('base',0),
              'upgrade_before':old.get('upgrade',0),'upgrade_after':new.get('upgrade',0)}
        line['pending_delta']=line['pending_after']-line['pending_before']
        line['vacant_delta']=line['vacant_after']-line['vacant_before']
        line['charged_before']=line['free_before']+line['base_before']+line['upgrade_before']
        line['charged_after']=line['free_after']+line['base_after']+line['upgrade_after']
        line['charged_delta']=line['charged_after']-line['charged_before']
        lines.append(line)
    money_before,money_after=before['money'],after['money']
    return {'berths':lines,
            'pending_before':sum(row['pending_before'] for row in lines),
            'pending_after':sum(row['pending_after'] for row in lines),
            'due_before':money_before.get('due_cents',0),'due_after':money_after.get('due_cents',0),
            'paid_before':money_before.get('paid_cents',0),'paid_after':money_after.get('paid_cents',0),
            'difference_before':money_before.get('difference_cents',0),
            'difference_after':money_after.get('difference_cents',0)}


def same_window(parent,survey):
    """更正必须沿用原留档的清算窗口与泊位，避免跨窗口改写旧账。"""
    origin=parent.get('manifest') or {}
    fields=origin.get('survey') or {}
    now=(survey.name,survey.start.isoformat(),survey.end.isoformat(),tuple(survey.berths))
    before=(fields.get('name'),fields.get('start'),fields.get('end'),tuple(fields.get('berths') or ()))
    return before==now


def correction(parent,record,survey=None):
    """把补齐后的证据与更正差异挂到原留档编号上。

    原留档不存在、规则版本不一致或清算窗口不同时拒绝，避免用不同口径改写
    旧账。留档编号保持原编号，原摘要追加到 ``history``。
    """
    if parent is None:
        raise DocketError('PARENT_BAD','找不到引用的原清算批次',404)
    origin=parent.get('manifest') or {}
    if origin.get('rule')!=POLICY:
        raise DocketError('PARENT_BAD','原批次规则版本与当前不一致',409)
    if survey is not None and not same_window(parent,survey):
        raise DocketError('PARENT_BAD','更正的清算窗口或泊位与原批次不同',409)
    manifest=dict(record['manifest'])
    manifest['parent']=origin.get('key')
    manifest['original']=origin.get('original',origin.get('key'))
    manifest['original_created_utc']=origin.get('original_created_utc',origin.get('created_utc'))
    manifest['history']=(origin.get('history') or [])+[{
        'evidence_sha256':origin.get('evidence_sha256'),
        'created_utc':origin.get('created_utc'),
        'inputs':origin.get('inputs')}]
    manifest['changes']=changes(snapshot(parent),snapshot(record))
    manifest['changes']['parent']=origin.get('key')
    return {'manifest':manifest,'evidence':record['evidence']}
