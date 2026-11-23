from app.archive.canonical import digest
from app.problems import DocketError


def issue(packet):
    evidence=packet['evidence']
    if digest(evidence)!=packet['manifest']['evidence_sha256']:
        raise DocketError('DIGEST_BAD','证据内容与留档摘要不同',409)
    account=evidence['settlement']
    for row in account['berths']:
        remainder=row['scheduled']-sum(row[key] for key in ('vacant','disputed','free','base','upgrade'))
        if remainder:
            raise DocketError('BERTH_UNBALANCED','泊位分钟勾稽未平',409)
    money=account['money']
    if money['paid_cents']-money['due_cents']!=money['difference_cents'] or any(
        r['paid_cents']-r['due_cents']!=r['difference_cents'] for r in account['lines']
    ):
        raise DocketError('MONEY_UNBALANCED','收费差价勾稽未平',409)
    return {'document':'泊位理赔证据','minutes_balance':0,'sha256':digest(packet),**packet}
