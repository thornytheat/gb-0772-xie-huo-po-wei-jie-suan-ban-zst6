from app.curb.detections import prepare
from app.curb.merge import stays
from app.curb.timeaxis import minute


def test_mixed_offsets_share_minute(dirty):
    # TRAP-11
    assert minute('2026-11-30T23:53+08:00')==minute('2026-11-30T15:53Z')
    r=dirty.occupancy['stays'][0]
    assert r['minutes']==45 and len(r['detections'])==3
    assert r['observed_minutes']==50


def test_touching_scans_single_stay(clean):
    # TRAP-23
    s=clean.occupancy['stays'][0]
    assert [r['fields']['event'] for r in s['detections']]==['0001','0002','0003']
    assert s['detections'][1]['end']==s['detections'][2]['start']
    assert s['minutes']==45


def test_overlap_is_removed_per_vehicle(clean):
    assert clean.occupancy['removed_overlap_minutes']==17
    assert [r['minutes'] for r in clean.occupancy['stays']]==[45,25,15,15]


def test_collision_priority_matches_both_berths(dirty):
    # TRAP-19
    at=minute('2026-12-01T00:23+08:00')
    disputes={(r['berth'],r['at']):r['code'] for r in dirty.occupancy['disputes']}
    assert disputes['B-01',at]=='PLATE_OVERLAP' and disputes['B-02',at]=='BERTH_OVERLAP'
    assert len(disputes)==7


def test_order_independent_union(dirty):
    entries,_=prepare(dirty.anonymous['sensors'][0],dirty.survey)
    assert stays(entries)==stays(entries[::-1])


def test_no_clipping_without_arrival_evidence(clean):
    row=clean.anonymous['sensors'][0][0]
    start='2026-11-30T23:25+08:00'
    entries,isolated=prepare([row | {'fields':row['fields'] | {'start':start}}],clean.survey)
    assert entries==[] and [(r['line'],r['code']) for r in isolated]==[(2,'RANGE')]
