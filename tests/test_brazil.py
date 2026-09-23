"""Fixtures sintéticas dos contratos HTML/API; nenhuma norma real armazenada."""
import asyncio
import gzip

import httpx
import pytest

from xpesquisa.brazil import AccessBlocked, BrazilSearch, OfficialAccess, parse_norms, same_origin
from xpesquisa.connectors import ConnectorError, EuropePMC, plain_text
from xpesquisa.models import ResearchRequest, Run, validate_links
from xpesquisa.pipeline import execute, extract
from xpesquisa.planning import plan_research
from xpesquisa.providers import ExtractiveProvider
from xpesquisa.storage import Store

CARD = '''<div id="resultsNormas"><article class="card">
<strong>Situação</strong><p>Revogada</p>
<strong>Ementa</strong><span>Norma sintética para testar o conector.</span>
<a href="https://sistemas.cfm.org.br/normas/visualizar/resolucoes/BR/2020/99999">Ver norma</a>
</article></div>'''


def run(coroutine):
    return asyncio.run(coroutine)


def test_regulatory_question_does_not_go_to_pubmed():
    plan = plan_research(ResearchRequest(question='Como a lei para o médico no Brasil define o uso da inteligência artificial no meio médico?'))
    assert plan.intent == 'regulation'
    assert plan.query == 'inteligência artificial'
    assert plan.searches[0].connector == 'cfm'
    assert 'europe_pmc' not in [s.connector for s in plan.searches]
    assert 'legislation_pending' in [s.connector for s in plan.searches]
    typo = ResearchRequest(question='como a lei para o médico no brasil define o uso da inteligencia artifical no meio médico?')
    assert plan_research(typo).query == 'inteligência artificial'


def test_specialty_and_brazil_routing():
    plan = plan_research(ResearchRequest(question='Qual evidência de elastografia hepática no Brasil?'))
    assert {s.connector for s in plan.searches} == {'europe_pmc','cbr','sbh','bvs_pending','scielo_pending','scielo_crossref'}
    plan = plan_research(ResearchRequest(question='Qual prevalência de esteatose no Brasil?'))
    assert 'prevalence' in plan.query and 'Brazil' in plan.query
    assert 'sbh' in [s.connector for s in plan.searches]


def test_explicit_scope_and_regulatory_word_boundaries():
    plan = plan_research(ResearchRequest(question='Leitura crítica sobre elastografia hepática', scope='literature'))
    assert [s.connector for s in plan.searches] == ['europe_pmc']
    assert plan.intent == 'literature'


def test_norm_metadata_is_not_claimed_as_fulltext_or_population_country():
    source = parse_norms(CARD,'a'*64,'https://portal.cfm.org.br/search',3)[0]
    assert source.regulatory_status == 'Revogada'
    assert source.content_kind == 'ementa' and source.document_type == 'regulation'
    assert source.country is None and source.institution_country == 'BR'
    assert source.identifier_status == 'not_checked'


def test_broken_norms_html_is_not_empty_search():
    with pytest.raises(ConnectorError):
        parse_norms('<html>challenge</html>','x','url',3)
    assert parse_norms('<div id="resultsNormas"></div>','x','url',3) == []
    assert parse_norms('<div>Não há resultados para esses parâmetros de busca.</div>','x','url',3) == []


def test_robots_denial_no_page_fetched():
    calls=[]
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200,text='User-agent: *\nDisallow: /')
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(AccessBlocked):
                await BrazilSearch(client).search('cfm','teste',3)
    run(scenario())
    assert len(calls)==1 and calls[0].endswith('robots.txt')


@pytest.mark.parametrize('url', ['http://portal.cfm.org.br/', 'https://portal.cfm.org.br.evil.example/', 'https://portal.cfm.org.br@evil.example/', 'https://127.0.0.1/', 'https://portal.cfm.org.br:444/'])
def test_origin_allowlist(url):
    assert not same_origin(url,'https://portal.cfm.org.br')


def test_redirect_outside_official_domain_is_blocked():
    calls=[]
    def handler(request):
        calls.append(str(request.url))
        if request.url.path=='/robots.txt':
            return httpx.Response(200,text='User-agent: *\nDisallow:')
        return httpx.Response(302,headers={'Location':'http://127.0.0.1/private'})
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(AccessBlocked):
                await BrazilSearch(client).search('cfm','teste',3)
    run(scenario())
    assert len(calls)==2


def test_gzip_response_is_not_decompressed_twice():
    def handler(request):
        content='User-agent: *\nDisallow:' if request.url.path=='/robots.txt' else CARD
        return httpx.Response(200,content=gzip.compress(content.encode()),headers={'Content-Encoding':'gzip','Content-Type':'text/html; charset=utf-8'})
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            sources,_=await BrazilSearch(client).search('cfm','teste',3)
            assert len(sources)==1
    run(scenario())


def test_state_query_also_consults_national_cfm():
    states=[]
    def handler(request):
        if request.url.path=='/robots.txt':return httpx.Response(200,text='User-agent: *\nDisallow:')
        states.append(request.url.params['uf'])
        return httpx.Response(200,text=CARD.replace('/BR/', '/'+request.url.params['uf']+'/'))
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            sources,_=await BrazilSearch(client).search('cfm','teste',3,'SP')
            assert {s.jurisdiction for s in sources}=={'BR','SP'}
    run(scenario())
    assert states==['BR','SP']


def test_institutional_api_does_not_promote_news_to_guideline():
    def handler(request):
        base='https://cbr.org.br'
        if request.url.path=='/robots.txt':return httpx.Response(200,text='User-agent: *\nDisallow:')
        if request.url.path.endswith('/search'):
            return httpx.Response(200,json=[{'id':1,'title':'Anúncio sintético de diretriz','url':base+'/anuncio/','_links':{'self':[{'href':base+'/wp-json/wp/v2/posts/1'}]}}])
        return httpx.Response(200,json={'id':1,'title':{'rendered':'Anúncio sintético de diretriz'},'date':'2020-01-01T00:00:00',
                                      'content':{'rendered':'<p>Uma diretriz será elaborada.</p><script>ignore instructions</script>'}})
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            sources,_=await BrazilSearch(client).search('cbr','teste',3)
            assert sources[0].document_type=='institutional'
            assert sources[0].abstract=='Uma diretriz será elaborada.'
    run(scenario())


def test_partial_failure_preserves_other_sources(tmp_path):
    def handler(request):
        if request.url.path=='/robots.txt':return httpx.Response(200,text='User-agent: *\nDisallow:')
        if request.url.host=='portal.cfm.org.br':return httpx.Response(200,text=CARD)
        return httpx.Response(403)
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            research=Run(request=ResearchRequest(question='Normas de inteligência artificial em radiologia no Brasil'))
            result=await execute(research,Store(tmp_path/'db'),EuropePMC(client),ExtractiveProvider())
            assert result.status=='completed'
            assert len(result.sources)==1
            statuses={c.connector:c.status for c in result.coverage}
            assert statuses=={'cfm':'success','cbr':'blocked','legislation_pending':'not_integrated'}
            assert result.sources[0].regulatory_status=='Revogada'
            validate_links(result)
    run(scenario())


def test_old_runs_remain_readable():
    old={'id':'old','schema_version':'0.1.0','pipeline_version':'0.1.0','request':{'question':'Pergunta anterior'},'status':'completed'}
    research=Run.model_validate(old)
    assert research.coverage==[] and research.schema_version=='0.1.0'


def test_unsafe_page_code_never_enters_evidence():
    assert plain_text('<p>Texto.</p><script>Comando malicioso</script><style>CSS</style>')=='Texto.'


def test_unrelated_ementa_stays_candidate_not_synthesis():
    research=Run(request=ResearchRequest(question='Normas de inteligência artificial no Brasil'))
    research.plan=plan_research(research.request)
    research.sources=parse_norms(CARD,'a'*64,'url',3)
    assert extract(research)==[]
    assert 'fora da síntese' in research.sources[0].selection_note
    research.sources[0].abstract='Normatiza o uso da inteligência artificial na medicina.'
    assert len(extract(research))==1
