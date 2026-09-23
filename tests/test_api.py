import time

import httpx
from fastapi.testclient import TestClient

from xpesquisa.api import create_app


def wait(client, run_id):
    for _ in range(100):
        run = client.get('/api/research/' + run_id).json()
        if run['status'] in {'completed', 'failed'}:
            return run
        time.sleep(.01)
    raise AssertionError('Task did not complete')


def test_local_skeleton(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get('/api/health').json()['status'] == 'ok'
        assert 'XPesquisa' in client.get('/').text
        assert client.get('/assets/app.js').status_code == 200
        assert 'OpenAPI JSON' in client.get('/docs').text
        assert '/api/research' in client.get('/openapi.json').json()['paths']


def test_pipeline_end_to_end(tmp_path, payload):
    app = create_app(tmp_path, transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)))
    with TestClient(app) as client:
        response = client.post('/api/research', json={'question': 'Pergunta sintética de teste'})
        assert response.status_code == 202
        run = wait(client, response.json()['id'])
        assert run['status'] == 'completed'
        assert len(run['claims']) == len(run['evidence']) == 1
        assert run['sources'][0]['identifier_status'] == 'matched'
        assert run['claims'][0]['verification_status'] == 'excerpt_only'
        assert run['events'][-1]['stage'] == 'completed'
        assert len(client.get('/api/research').json()) == 1
        exported = client.get('/api/research/' + run['id'] + '/export').json()
        assert 'abstract' not in exported['sources'][0]
        assert 'supporting_excerpt' not in exported['evidence'][0]
        assert 'text' not in exported['claims'][0]
    with TestClient(create_app(tmp_path)) as client:
        assert client.get('/api/research/' + run['id']).json()['status'] == 'completed'


def test_no_results_not_absence(tmp_path):
    transport = httpx.MockTransport(lambda r: httpx.Response(200,json={'hitCount':0,'resultList':{'result':[]}}))
    with TestClient(create_app(tmp_path, transport=transport)) as client:
        run = wait(client, client.post('/api/research',json={'question':'Pergunta sem resultados'}).json()['id'])
        assert run['status'] == 'completed'
        assert 'não demonstra ausência' in run['summary']
        assert run['claims'] == []


def test_failed_search_is_persisted(tmp_path):
    transport = httpx.MockTransport(lambda r: httpx.Response(403))
    with TestClient(create_app(tmp_path, transport=transport)) as client:
        run = wait(client, client.post('/api/research',json={'question':'Pergunta com falha'}).json()['id'])
        assert run['status'] == 'failed'
        assert run['events'][-1]['stage'] == 'failed'
        assert run['plan']['query'] == 'Pergunta com falha'


def test_local_security_and_validation(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.post('/api/research', json={'question':'too tiny'} ,headers={'Origin':'https://evil.example'}).status_code == 403
        assert client.post('/api/research', content='x'*20000,headers={'Content-Type':'application/json'}).status_code == 413
        assert client.post('/api/research', json={'question':'  '}).status_code == 422
        assert client.post('/api/research', content='{}').status_code == 415
        assert client.get('/api/health',headers={'Host':'evil.example'}).status_code == 400
        assert client.get('/api/research/not-a-uuid').status_code == 422
