import pytest

from app.problems import DocketError
from app.source.csvscan import scan


def test_started_with_bom(dirty):
    # TRAP-02
    assert dirty.sheets['sensors'][0][0]['fields']['event']=='0003'


def test_repeated_header_and_physical_count(dirty):
    # TRAP-04
    rows=dirty.intake['sheets'][0]
    assert (rows['submitted'],rows['parsed'],rows['headers'],len(rows['isolation']))==(27,25,1,1)


def test_ragged_row_keeps_hash_not_plaintext(dirty):
    # TRAP-05
    issue=dirty.intake['sheets'][0]['isolation'][0]
    assert (issue['line'],issue['code'],issue['cells'])==(21,'WIDTH',3)
    assert len(issue['row_sha256'])==64 and 'raw' not in issue


def test_conflicting_sensor_event_never_last_wins(dirty):
    # TRAP-14
    conflicts=[r for r in dirty.intake['sensor_issues'] if r['code']=='ID_CONFLICT']
    assert [(r['line'],r['fields']['event']) for r in conflicts]==[(27,'0016'),(28,'0016')]
    assert dirty.intake['kept_sensors']==20


def test_empty_and_corrupt_are_distinct():
    with pytest.raises(DocketError) as missing:
        scan('','payments')
    assert missing.value.code=='SHEET_EMPTY'
    with pytest.raises(DocketError) as corrupt:
        scan('receipt,berth,plate,arrival,cents\n"not closed','payments')
    assert corrupt.value.code=='CSV_BAD'
    assert scan('receipt,berth,plate,arrival,cents','payments')[1]['state']=='header_only'


def test_front_zero_id_survives_intake(dirty):
    # TRAP-08
    issue=next(x for x in dirty.intake['sensor_issues'] if x['code']=='DUPLICATE')
    assert (issue['fields']['event'],issue['line'])==('0001',22)
