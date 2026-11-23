from copy import deepcopy

import pytest

from app.archive.appeal import issue
from app.archive.canonical import digest
from app.problems import DocketError


@pytest.fixture
def exported(client):
    key=client.post('/api/dockets',json={'sample':'dirty'}).json()['key']
    return client.get('/api/export/'+key)


def test_attachment_includes_evidence_and_manifest(exported):
    doc=exported.json()
    assert exported.headers['Content-Disposition'].startswith('attachment; filename="appeal-')
    assert (doc['document'],doc['minutes_balance'])==('泊位理赔证据',0)
    assert digest(doc['evidence'])==doc['manifest']['evidence_sha256']


def test_export_hides_input_plates(exported):
    assert all(plate not in exported.text for plate in ('粤B01234','粤ｂ ０１２３４','粤B11111','粤B22222','"plate"'))
    assert len(exported.json()['evidence']['identity']['stays'][0]['vehicle'])==64


def test_tampered_attachment_cannot_be_issued(exported):
    doc=deepcopy(exported.json()); doc['evidence']['pricing']['due_cents']+=1
    with pytest.raises(DocketError) as err:
        issue(doc)
    assert err.value.code=='DIGEST_BAD'


def test_berth_invariant_before_signing(exported):
    doc=deepcopy(exported.json()); doc['evidence']['settlement']['berths'][0]['vacant']+=1
    doc['manifest']['evidence_sha256']=digest(doc['evidence'])
    with pytest.raises(DocketError) as err:
        issue(doc)
    assert err.value.code=='BERTH_UNBALANCED'


def test_money_invariant_before_signing(exported):
    doc=deepcopy(exported.json()); doc['evidence']['settlement']['lines'][0]['difference_cents']+=1
    doc['manifest']['evidence_sha256']=digest(doc['evidence'])
    with pytest.raises(DocketError) as err:
        issue(doc)
    assert err.value.code=='MONEY_UNBALANCED'


def test_missing_batch_is_not_downloaded(client):
    r=client.get('/api/export/unknown')
    assert (r.status_code,r.json()['code'],r.headers.get('Content-Disposition'))==(404,'DOCKET_MISSING',None)
