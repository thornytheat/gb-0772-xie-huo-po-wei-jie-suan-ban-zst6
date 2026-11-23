import json

import pytest

from app.source.packet import bundle

BERTH='B-02'
GAP_START='2026-12-01T01:10+08:00'
GAP_END='2026-12-01T01:30+08:00'
LATE='X1,B-02,粤B11111,side-2,2026-12-01T01:10+08:00,2026-12-01T01:25+08:00\n'


def declared(**over):
    files=bundle('dirty')
    survey=json.loads(files['survey'])
    survey['outages']=[{'berth':BERTH,'sensor':'side-2','start':GAP_START,'end':GAP_END}]
    files['survey']=json.dumps(survey,ensure_ascii=False)
    return files | over


def post(client,files,parent=None):
    payload={'bundle':files}
    if parent:
        payload['parent']=parent
    return client.post('/api/dockets',json=payload)


def test_first_batch_keeps_gap_pending(client):
    result=post(client,declared()).json()
    assert result['pending']['by_berth'][BERTH]==20
    assert result['totals']['vacant']==113


def test_late_record_clears_pending_and_amends_same_key(client):
    base=post(client,declared()).json()
    fixed=post(client,declared(sensors=declared()['sensors']+LATE),parent=base['key']).json()
    assert fixed['key']==base['key'] and fixed['reused'] is False
    assert fixed['pending']['by_berth'][BERTH]==5
    assert fixed['totals']['base']==69 and fixed['totals']['upgrade']==36
    amendment=fixed['amendment']
    assert amendment['parent']==base['key']
    row=next(r for r in amendment['berths'] if r['berth']==BERTH)
    assert (row['pending_before'],row['pending_after'])==(20,5)
    assert (row['charged_before'],row['charged_after'],row['charged_delta'])==(42,57,15)


def test_amend_does_not_add_history(client):
    base=post(client,declared()).json()
    post(client,declared(sensors=declared()['sensors']+LATE),parent=base['key'])
    assert len(client.get('/api/dockets').json()['dockets'])==1


def test_same_amendment_is_reused_not_recounted(client):
    base=post(client,declared()).json()
    files=declared(sensors=declared()['sensors']+LATE)
    first=post(client,{**files},parent=base['key']).json()
    second=post(client,{**files},parent=base['key']).json()
    assert (first['reused'],second['reused'],first['key']==second['key'])==(False,True,True)
    assert first['pending']==second['pending'] and first['money']==second['money']
    stored=client.get('/api/dockets/'+base['key']).json()
    assert stored['manifest']['evidence_sha256']==second['manifest']['evidence_sha256']
    assert len(stored['manifest']['history'])==1


def test_amended_evidence_still_signs(client):
    base=post(client,declared()).json()
    post(client,declared(sensors=declared()['sensors']+LATE),parent=base['key'])
    exported=client.get('/api/export/'+base['key'])
    assert exported.status_code==200
    doc=exported.json()
    assert doc['minutes_balance']==0 and doc['sha256']
    assert doc['evidence']['settlement']['pending']['total']==5


def test_parent_must_exist_and_be_text(client):
    missing=post(client,declared(),parent='nope')
    assert (missing.status_code,missing.json()['code'])==(404,'PARENT_BAD')
    wrong=post(client,declared(),parent=7)
    assert (wrong.status_code,wrong.json()['code'])==(422,'PARENT_BAD')


def test_amend_cannot_change_window(client):
    base=post(client,declared()).json()
    changed=declared()
    survey=json.loads(changed['survey'])
    survey['end']='2026-12-01T02:00+08:00'
    changed['survey']=json.dumps(survey,ensure_ascii=False)
    result=post(client,changed,parent=base['key'])
    assert (result.status_code,result.json()['code'])==(409,'PARENT_BAD')


def test_unamended_batch_still_dedupes(client):
    a=post(client,declared()).json()
    b=post(client,declared()).json()
    assert (a['reused'],b['reused'],a['key']==b['key'])==(False,True,True)
    assert len(client.get('/api/dockets').json()['dockets'])==1


def test_pages_show_amendment_diff(client):
    base=post(client,declared()).json()
    post(client,declared(sensors=declared()['sensors']+LATE),parent=base['key'])
    page=client.get('/clearing/settlement',params={'key':base['key']})
    assert page.status_code==200 and '本次更正' in page.text
    assert '20 → 5' in page.text
    preview=client.get('/api/cases/dirty/settlement',params={'parent':base['key']})
    # 预览对照的是该编号当前留档（已被补齐为 5 分钟待核）
    assert preview.status_code==200
    assert preview.json()['amendment']['pending_before']==5
    assert preview.json()['amendment']['pending_after']==0
