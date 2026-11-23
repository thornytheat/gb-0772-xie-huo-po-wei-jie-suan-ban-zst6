from app.billing.payments import index


def test_mixed_conflicts_conserve_berth_time(dirty):
    result=dirty.settlement
    assert result['totals']=={'scheduled':240,'vacant':133,'disputed':7,'free':10,'base':68,'upgrade':22}
    assert all(b['scheduled']==b['vacant']+b['disputed']+b['free']+b['base']+b['upgrade'] for b in result['berths'])


def test_individual_signed_payment_deltas(dirty):
    assert [line['difference_cents'] for line in dirty.settlement['lines']]==[150,20,-60,-40,0,0]
    assert dirty.settlement['money']=={'due_cents':2240,'paid_cents':2310,'difference_cents':70,'orphan_cents':140}


def test_null_amount_never_looks_like_paid_zero(dirty):
    # TRAP-07
    r=dirty.settlement
    assert (r['isolated'][0]['fields']['cents'],r['isolated'][0]['code'])==('NULL','AMOUNT')
    assert r['lines'][2]['code']=='NO_PAYMENT' and r['lines'][2]['receipts']==[]


def test_orphan_payment_is_traceable(dirty):
    r=dirty.settlement['orphans'][0]
    assert (r['line'],r['fields']['receipt'],r['cents'],r['code'])==(6,'0011',140,'ORPHAN')


def test_identical_clean_payments_match_all_stops(clean):
    assert [r['code'] for r in clean.settlement['lines']]==['MATCH']*4
    assert clean.settlement['money']['paid_cents']==2100


def test_conflicting_payment_excludes_all_candidates(clean):
    row=clean.anonymous['payments'][0][0]
    by_slot,issues=index([row,row | {'line':900,'fields':row['fields'] | {'cents':'899'}}],clean.survey)
    assert not by_slot and [r['cents'] for r in issues]==[900,899]
    assert [r['code'] for r in issues]==['ID_CONFLICT','ID_CONFLICT']
