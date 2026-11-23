from datetime import UTC,datetime
from time import perf_counter

from app.archive.canonical import digest
from app.clearing import Clearing
from app.setup import POLICY
from app.source.packet import decode,fingerprint


def run(docket, payload):
    started=perf_counter()
    original,source=decode(payload)
    hashes=fingerprint(original)
    key=digest({'files':hashes,'policy':POLICY})
    existing=docket.find(key)
    if existing:
        return existing,True
    clearing=Clearing(original,docket.secret)
    report=clearing.report()
    manifest={'key':key,'source':source,'rule':POLICY,'inputs':hashes,'evidence_sha256':digest(report),
              'survey':vars(clearing.survey),'created_utc':datetime.now(UTC).isoformat(timespec='seconds'),
              'elapsed_ms':round((perf_counter()-started)*1000)}
    return docket.publish(key,{'manifest':manifest,'evidence':report})
