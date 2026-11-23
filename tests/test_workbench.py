from app.web import STEPS


def test_each_page_returns_rendered_evidence(client):
    home=client.get('/')
    assert home.status_code==200 and '泊位占位阶段流' in home.text
    for slug,label in STEPS.items():
        response=client.get('/clearing/'+slug)
        assert response.status_code==200 and f'<h1>{label}</h1>' in response.text


def test_sealed_flow_links_to_evidence(client):
    key=client.post('/api/dockets',json={'sample':'dirty'}).json()['key']
    result=client.get('/clearing/appeal',params={'key':key})
    assert f'href="/api/export/{key}"' in result.text
    assert '泊位分钟勾稽差额 <b>0</b>' in result.text


def test_sample_error_has_recovery_code(client):
    r=client.get('/api/cases/not-found/intake')
    assert (r.status_code,r.json()['code'])==(404,'SAMPLE_BAD')
