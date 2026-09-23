import asyncio

import httpx
import pytest

from xpesquisa.connectors import ConnectorError, EuropePMC
from xpesquisa.crossref import SciELODeposits
from xpesquisa.models import ResearchRequest, Run, Source
from xpesquisa.pipeline import extract
from xpesquisa.planning import plan_research


def test_wrist_question_uses_concepts_and_brazil_sources():
    plan = plan_research(ResearchRequest(question="Quero investigar medidas chave em ultrassom de punho"))
    tasks = {t.connector: t for t in plan.searches}
    assert 'wrist OR carpal' in plan.query and 'measurement' in plan.query
    assert 'quero' not in plan.query.lower()
    assert tasks['sbus'].query == tasks['cbr'].query == 'punho'
    assert tasks['scielo_crossref'].query == 'ultrassonografia punho'
    assert 'bvs_pending' in tasks


def test_other_anatomy_does_not_silently_become_wrist():
    plan = plan_research(ResearchRequest(question="Quero investigar ultrassom de ombro"))
    assert '(shoulder)' in plan.query and 'carpal' not in plan.query
    assert 'measurement' not in plan.query


def test_custom_query_is_preserved_and_explicit_literature_is_respected():
    plan = plan_research(ResearchRequest(question="Ultrassom de punho", query="custom terms", scope="literature"))
    assert plan.query == 'custom terms'
    assert [t.connector for t in plan.searches] == ['europe_pmc']


def item(doi='10.1234/test', title='Ultrassonografia do punho', **extra):
    return {'DOI': doi, 'title': [title], 'member': '530', 'type': 'journal-article', **extra}


def search(payload):
    async def scenario():
        def handler(request):
            assert request.url.host == 'api.crossref.org'
            assert request.url.params['rows'] == '20'
            return httpx.Response(200, json=payload)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await SciELODeposits(client).search('ultrassonografia punho', 8)
    return asyncio.run(scenario())


def test_crossref_fuzzy_results_are_filtered_and_missing_abstract_not_invented():
    sources, detail = search({'status': 'ok', 'message': {'total-results': 2, 'items': [
        item(), item('10.1234/other', 'Ultrassonografia do fígado')]}})
    assert len(sources) == 1 and sources[0].abstract == ''
    assert sources[0].institution_country is None and sources[0].country is None
    assert sources[0].identifier_status == 'not_checked'
    assert 'Crossref' in sources[0].source
    assert detail['excluded_dois'] == ['10.1234/other']
    assert extract(Run(request=ResearchRequest(question='Ultrassom de punho'), sources=sources)) == []


def test_crossref_english_synonyms_and_literal_abstract():
    sources, _ = search({'status': 'ok', 'message': {'total-results': 1, 'items': [
        item(title='Wrist sonography', abstract='<jats:p>Synthetic abstract.</jats:p>')]}})
    assert sources[0].abstract == 'Synthetic abstract.'


@pytest.mark.parametrize('payload', [
    {}, {'status': 'ok', 'message': {'items': []}},
    {'status': 'ok', 'message': {'total-results': 1, 'items': [item(member='999')]}}
])
def test_crossref_bad_response_is_not_empty(payload):
    with pytest.raises(ConnectorError):
        search(payload)


def test_crossref_valid_empty():
    assert search({'status': 'ok', 'message': {'items': [], 'total-results': 0}})[0] == []


def test_crossref_redirect_not_followed():
    calls = []
    def handler(request):
        calls.append(request.url.host)
        return httpx.Response(302, headers={'Location': 'http://127.0.0.1/private'})
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await SciELODeposits(client).search('punho', 8)
    asyncio.run(scenario())
    assert calls == ['api.crossref.org']


def test_same_doi_does_not_duplicate_claims_across_sources():
    source = Source(id='one', title='Synthetic', source_url='https://example.org', external_id='1',
                    collection='MED', doi='10.1234/same', response_sha256='a', abstract='Synthetic text.')
    other = source.model_copy(update={'id': 'two', 'collection': 'CROSSREF_SCIELO'})
    result = extract(Run(request=ResearchRequest(question='Ultrassom de punho'), sources=[source, other]))
    assert len(result) == 1 and other.selection_note


def test_institutional_application_letter_is_not_wrist_evidence():
    research = Run(request=ResearchRequest(question='Quero investigar medidas chave em ultrassom de punho'))
    research.plan = plan_research(research.request)
    source = Source(id='sbus:1', title='Inscrição em curso de ultrassonografia',
                    source_url='https://example.org', external_id='1', collection='SBUS',
                    document_type='institutional', content_kind='institutional_text',
                    abstract='Enviar uma carta escrita de próprio punho.', response_sha256='a')
    research.sources = [source]
    assert extract(research) == [] and source.selection_note


def test_incomplete_upstream_recovers_with_bounded_retry(monkeypatch):
    calls = []
    async def no_delay(_):
        pass
    monkeypatch.setattr(asyncio, 'sleep', no_delay)
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={} if len(calls) == 1 else {'hitCount': 0, 'resultList': {'result': []}})
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            sources, detail = await EuropePMC(client).search('wrist', 8)
            assert sources == [] and detail['attempts'] == 2
    asyncio.run(scenario())
    assert len(calls) == 2
