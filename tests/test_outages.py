import json

import pytest

from app.clearing import Clearing
from app.problems import DocketError
from app.source.packet import bundle

BERTH='B-02'
GAP_START='2026-12-01T01:10+08:00'
GAP_END='2026-12-01T01:30+08:00'


def with_outages(*windows):
    files=bundle('dirty')
    survey=json.loads(files['survey'])
    survey['outages']=[{'berth':berth,'sensor':sensor,'start':start,'end':end}
                       for berth,sensor,start,end in windows]
    files['survey']=json.dumps(survey,ensure_ascii=False)
    return files


def clearing(files):
    return Clearing(files,b'fixture-2026')


def berth_row(result,berth):
    return next(row for row in result['berths'] if row['berth']==berth)


def test_no_declaration_keeps_vacant_and_totals(dirty):
    assert dirty.settlement['pending']=={'total':0,'by_berth':{'B-01':0,'B-02':0}}
    assert dirty.settlement['totals']=={'scheduled':240,'vacant':133,'disputed':7,'free':10,'base':68,'upgrade':22}


def test_undeclared_gap_is_pending_not_vacant():
    # B-02 在 01:10–01:30 没有任何检测：申报后这 20 分钟待核，不再算空闲
    c=clearing(with_outages((BERTH,'',GAP_START,GAP_END)))
    review=c.outage_review
    assert (review['outage_minutes'],review['covered_minutes'],review['pending_minutes'])==(20,0,20)
    assert c.settlement['pending']['by_berth'][BERTH]==20
    assert c.settlement['totals']['vacant']==133-20
    assert c.settlement['totals']['base']==68 and c.settlement['totals']['upgrade']==22


def test_pending_is_neither_vacant_nor_billed():
    c=clearing(with_outages((BERTH,'',GAP_START,GAP_END)))
    row=berth_row(c.settlement,BERTH)
    assert row['scheduled']==row['vacant']+row['pending']+row['disputed']+row['free']+row['base']+row['upgrade']
    assert (row['pending'],row['vacant'],row['base'],row['upgrade'])==(20,56,25,17)


def test_other_pole_partial_stop_verifies_only_its_minutes():
    # 整泊位申报 00:20–01:30；他杆只在 00:28–00:33 报了部分停靠
    files=with_outages((BERTH,'side-2','2026-12-01T00:20+08:00','2026-12-01T01:30+08:00'))
    files['sensors']+=('X01,B-02,粤B11111,side-9,2026-12-01T00:28+08:00,2026-12-01T00:33+08:00\n')
    c=clearing(files)
    row=c.outage_review['berths'][0]
    assert (row['outage_minutes'],row['other_pole_minutes'],row['pending_minutes'])==(70,5,46)
    assert row['other_pole_ranges']==[{'start':'2026-11-30T16:28:00+00:00',
                                       'end':'2026-11-30T16:33:00+00:00','minutes':5}]
    assert c.settlement['pending']['by_berth'][BERTH]==46


def test_other_berth_bills_while_one_berth_waits():
    c=clearing(with_outages((BERTH,'',GAP_START,GAP_END)))
    other=berth_row(c.settlement,'B-01')
    assert (other['pending'],other['base'],other['upgrade'],other['scheduled'])==(0,43,5,120)


def test_declaration_ranges_are_half_open():
    c=clearing(with_outages(('B-01','north-loop','2026-12-01T01:10+08:00','2026-12-01T01:20+08:00')))
    row=c.outage_review['berths'][0]
    assert row['pending_ranges']==[{'start':'2026-11-30T17:10:00+00:00',
                                    'end':'2026-11-30T17:20:00+00:00','minutes':10}]


def test_declaration_outside_berth_or_window_is_rejected():
    files=bundle('dirty')
    survey=json.loads(files['survey'])
    survey['outages']=[{'berth':'B-99','start':GAP_START,'end':GAP_END}]
    files['survey']=json.dumps(survey,ensure_ascii=False)
    with pytest.raises(DocketError) as err:
        clearing(files)
    assert err.value.code=='SURVEY_BAD'


def test_duplicate_declaration_is_isolated_once():
    files=with_outages((BERTH,'side-2',GAP_START,GAP_END),(BERTH,'side-2',GAP_START,GAP_END))
    c=clearing(files)
    assert c.intake['outage_windows']==1
    assert [row['code'] for row in c.intake['outage_issues']]==['DUPLICATE']
    assert c.outage_review['outage_minutes']==20


def test_pages_show_pending_and_scheduled(client):
    files=with_outages((BERTH,'',GAP_START,GAP_END))
    key=client.post('/api/dockets',json={'bundle':files}).json()['key']
    for slug in ('/','/clearing/settlement'):
        page=client.get(slug,params={'key':key})
        assert page.status_code==200 and '待核' in page.text and '应管' in page.text
    preview=client.get('/api/cases/dirty/settlement')
    assert preview.status_code==200 and preview.json()['pending']['total']==0


def test_outages_can_arrive_as_csv_sheet():
    files=bundle('dirty')
    files['outages']=('berth,sensor,start,end\n'
                      f'{BERTH},side-2,{GAP_START},{GAP_END}\n')
    c=clearing(files)
    assert c.settlement['pending']['by_berth'][BERTH]==20
    assert c.intake['outage_windows']==1


def test_survey_and_sheet_declarations_are_deduplicated_together():
    files=with_outages((BERTH,'side-2',GAP_START,GAP_END))
    files['outages']=('berth,sensor,start,end\n'
                      f'{BERTH},side-2,{GAP_START},{GAP_END}\n')
    c=clearing(files)
    assert c.intake['outage_windows']==1
    assert [row['code'] for row in c.intake['outage_issues']]==['DUPLICATE']
    assert c.outage_review['outage_minutes']==20


def test_batch_without_declarations_keeps_legacy_evidence(dirty):
    assert 'pending' not in dirty.settlement['totals']
    assert dirty.report()['outages']['berths']==[]
    for row in dirty.settlement['berths']:
        assert row['pending']==0
        assert row['scheduled']==row['vacant']+row['disputed']+row['free']+row['base']+row['upgrade']
