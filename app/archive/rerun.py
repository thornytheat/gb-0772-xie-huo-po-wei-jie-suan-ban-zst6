from datetime import UTC,datetime
from time import perf_counter

from app.archive.amend import correction
from app.archive.canonical import digest
from app.clearing import Clearing
from app.problems import DocketError
from app.setup import POLICY
from app.source.packet import decode,fingerprint


def run(docket,payload):
    started=perf_counter()
    original,source,parent_key=decode(payload)
    hashes=fingerprint(original)
    parent=docket.find(parent_key) if parent_key else None
    if parent_key and parent is None:
        raise DocketError('PARENT_BAD','找不到引用的原清算批次',404)
    if parent_key:
        key=parent_key
    else:
        key=digest({'files':hashes,'policy':POLICY})
        existing=docket.find(key)
        if existing:
            return existing,True
    clearing=Clearing(original,docket.secret,parent)
    report=clearing.report()
    manifest={'key':key,'source':source,'rule':POLICY,'inputs':hashes,'evidence_sha256':digest(report),
              'survey':vars(clearing.survey),'created_utc':datetime.now(UTC).isoformat(timespec='seconds'),
              'elapsed_ms':round((perf_counter()-started)*1000)}
    record={'manifest':manifest,'evidence':report}
    if parent is not None:
        return docket.amend(key,correction(parent,record,clearing.survey))
    return docket.publish(key,record)
