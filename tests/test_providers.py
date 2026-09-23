import asyncio
import json

import httpx
import pytest

from xpesquisa.models import Claim
from xpesquisa.pipeline import execute
from xpesquisa.providers import OllamaProvider
from xpesquisa.connectors import EuropePMC
from xpesquisa.storage import Store
from test_domain import sample_run


@pytest.mark.parametrize('text,refs', [('Rascunho', ['invented']), ('Fonte https://fake.example', None), ('DOI 10.0000/fake', None)])
def test_provider_rejects_free_references(text, refs):
    async def scenario():
        run = sample_run()
        response = {'response':json.dumps({'claims':[{'text':text,'evidence_ids':refs or [run.evidence[0].id]}]})}
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200,json=response))) as client:
            with pytest.raises(ValueError):
                await OllamaProvider(client,'test','http://127.0.0.1:11434').synthesize(run)
    asyncio.run(scenario())


def test_local_provider_never_marks_semantic_verification():
    async def scenario():
        run = sample_run()
        def handler(request):
            data = json.loads(request.content)
            assert data['stream'] is False and data['options']['temperature'] == 0
            return httpx.Response(200,json={'model':'test','response':json.dumps({'claims':[{'text':'Rascunho sintético', 'evidence_ids':[run.evidence[0].id]}]})})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            claims, meta = await OllamaProvider(client,'test','http://localhost:11434').synthesize(run)
            assert claims[0].verification_status == 'not_verified'
            assert meta['semantic_verification'] == 'not_evaluated'
    asyncio.run(scenario())


def test_bad_provider_falls_back_without_fake_claim(tmp_path, payload):
    class FakeProvider:
        name, model = 'test', 'test'
        async def synthesize(self, run):
            return [Claim(text='Invented clinical claim', evidence_ids=['fake'], kind='draft')], {}
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200,json=payload))) as client:
            run = await execute(sample_run(),Store(tmp_path/'test.db'),EuropePMC(client),FakeProvider())
            assert run.status == 'completed' and run.provider == 'extractive'
            assert all(c.text != 'Invented clinical claim' for c in run.claims)
            assert any(e.stage == 'provider_fallback' for e in run.events)
    asyncio.run(scenario())


def test_remote_ollama_rejected():
    with pytest.raises(ValueError, match='local'):
        OllamaProvider(None,'test','https://external.example')
