from app.curb.bookings import at_arrival,revisions
from app.source.plates import token


def test_normalized_plate_links_all_sources(dirty):
    stop=dirty.identity['stays'][0]
    assert len({row['vehicle'] for row in stop['detections']})==1
    assert stop['vehicle']==stop['booking']['vehicle']==token('粤Ｂ ０１２３４',dirty.secret)
    assert stop['booking']['reservation']=='BK-07'


def test_salt_is_site_specific():
    assert token('粤B01234',b'a')!=token('粤B01234',b'b')
    assert len(token('粤B01234',b'a'))==64


def test_cancel_before_arrival(dirty):
    stop=dirty.identity['stays'][1]
    assert (stop['association'],stop['booking'],[r['line'] for r in stop['candidates']])==('CANCELLED',None,[5])


def test_cancel_after_arrival_does_not_reprice(dirty):
    r=dirty.identity['stays'][0]
    assert (r['association'],r['booking']['state'],r['booking']['line'])==('BOOKED','ACTIVE',2)


def test_conflicting_same_effective_time_blocks_entitlement(clean):
    source=clean.anonymous['bookings'][0][0]
    dupe=source | {'line':77,'fields':source['fields'] | {'state':'CANCEL'}}
    candidates,rejects=revisions([source,dupe],clean.survey)
    booking,code,rows=at_arrival(clean.occupancy['stays'][0],candidates)
    assert (booking,code,[r['line'] for r in rows])==(None,'ATTACH_CONFLICT',[2,77])
    assert [r['code'] for r in rejects]==['ID_CONFLICT','ID_CONFLICT']


def test_invalid_plate_data_is_scrubbed(dirty):
    row=dirty.intake['sheets'][0]['bad_plates'][0]
    assert (row['code'],row['line'])==('PLATE',25)
    assert 'plate' not in row['fields'] and 'vehicle' not in row
