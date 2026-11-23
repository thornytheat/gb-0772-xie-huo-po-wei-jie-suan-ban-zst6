from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.archive.docket import Docket
from app.archive.rerun import run
from app.main import create_app
from app.source.packet import bundle


def test_replay_has_one_manifest(client):
    a,b=[client.post('/api/dockets',json={'sample':'dirty'}).json() for _ in range(2)]
    assert (a['reused'],b['reused'],a['manifest']==b['manifest'])==(False,True,True)
    assert [r['key'] for r in client.get('/api/dockets').json()['dockets']]==[a['key']]


def test_invalid_sheet_rolls_back(client):
    files=bundle('dirty') | {'bookings':'invalid,csv'}
    result=client.post('/api/dockets',json={'bundle':files})
    assert (result.status_code,result.json()['code'])==(422,'SCHEMA_BAD')
    assert client.get('/api/dockets').json()=={'dockets':[]}


def test_two_writers_publish_same_evidence(tmp_path):
    docket=Docket(tmp_path/'parallel.sqlite')
    with ThreadPoolExecutor(2) as workers:
        results=list(workers.map(lambda _:run(docket,{'sample':'dirty'}),range(2)))
    assert sorted(val for _,val in results)==[False,True] and results[0][0]==results[1][0]


def test_restart_persists_results_and_vehicle_salt(client,tmp_path):
    key=client.post('/api/dockets',json={'sample':'dirty'}).json()['key']
    archived='/api/dockets/'+key
    preview='/api/cases/dirty/identity'
    with TestClient(create_app(tmp_path/'clearing.sqlite')) as again:
        assert again.get(archived).content==client.get(archived).content
        assert again.get(preview).content==client.get(preview).content


def test_changed_inputs_produce_new_key(client):
    plain=bundle('clean')
    first=client.post('/api/dockets',json={'bundle':plain}).json()
    second=client.post('/api/dockets',json={'bundle':plain | {'payments':plain['payments']+'\r\n'}}).json()
    assert first['key']!=second['key']
    assert first['money']==second['money']


def test_invalid_bundle_recovers(client):
    result=client.post('/api/dockets',json={'bundle':{}})
    assert (result.status_code,result.json()['code'])==(422,'BUNDLE_BAD')
    assert client.post('/api/dockets',json={'sample':'clean'}).json()['money']['due_cents']==2100
