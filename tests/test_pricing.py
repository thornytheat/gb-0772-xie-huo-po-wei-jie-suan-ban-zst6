def test_midnight_reset_and_no_reset_on_scan(clean):
    stop=clean.pricing['stays'][0]
    assert [(s['day'],s['code'],s['minutes'],s['cents']) for s in stop['segments']]==[
        ('2026-11-30','FREE',10,0),('2026-11-30','BASE',10,200),
        ('2026-12-01','BASE',15,300),('2026-12-01','UPGRADE',10,400)]
    assert stop['due_cents']==900


def test_new_stop_same_day_cross_berth_reuses_tier(clean):
    stop=clean.pricing['stays'][2]
    assert stop['berth']=='B-02'
    assert [(x['code'],x['cents']) for x in stop['segments']]==[('UPGRADE',600)]


def test_deleted_appointment_never_spends_free_minutes(dirty):
    stop=dirty.pricing['stays'][1]
    assert stop['due_cents']==500
    assert [(s['day'],s['minutes']) for s in stop['segments']]==[('2026-11-30',14),('2026-12-01',11)]
    assert all(s['code']=='BASE' for s in stop['segments'])


def test_disputed_time_is_not_charged(dirty):
    stop=dirty.pricing['stays'][3]
    assert [(x['code'],x['minutes'],x['cents']) for x in stop['segments']]==[('BERTH_OVERLAP',2,0),('UPGRADE',2,80)]


def test_zero_charge_for_all_reserved_ten_minutes(clean):
    from app.billing.rates import price
    from app.curb.timeaxis import M
    stop=clean.identity['stays'][0]
    r=price([stop | {'end':stop['start']+10*M}],{})[0]
    assert (r['due_cents'],r['segments'][0]['minutes'])==(0,10)


def test_stay_segment_split_conserves_minutes_and_cost(dirty):
    for line in dirty.pricing['stays']:
        assert line['minutes']==sum(x['minutes'] for x in line['segments'])
        assert line['due_cents']==sum(x['rate_cents']*x['minutes'] for x in line['segments'])
