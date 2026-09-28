import asyncio

import httpx

from xpesquisa.identity import IndependentIdentity, RateLimiter, normalized_title
from xpesquisa.models import Source


def source(**extra):
    base = dict(id="s", title="Synthetic Test Study", source_url="https://example.org",
                external_id="123", collection="MED", response_sha256="a" * 64)
    base.update(extra)
    return Source(**base)


def test_normalized_title_ignores_formatting_differences():
    a = "Estudo Sintético: Título — Teste!"
    b = "estudo sintetico titulo teste"
    assert normalized_title(a) == normalized_title(b)


def test_doi_matched_despite_formatting_difference():
    src = source(doi="10.1234/synthetic")

    def handler(request):
        assert "doi.org" in str(request.url)
        assert request.headers["User-Agent"].startswith("XPesquisa/")
        return httpx.Response(200, json={"title": "  Synthetic   Test Study! "})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            detail = await identity.check(src)
            assert detail["doi_status"] == "matched"
            assert src.independent_doi_status == "matched"
    asyncio.run(scenario())


def test_doi_mismatch_when_titles_differ():
    src = source(doi="10.1234/synthetic")

    def handler(request):
        return httpx.Response(200, json={"title": "Completely different title"})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            detail = await identity.check(src)
            assert detail["doi_status"] == "mismatch"
            assert src.independent_doi_status == "mismatch"
    asyncio.run(scenario())


def test_doi_not_found_is_mismatch():
    src = source(doi="10.1234/missing")

    def handler(request):
        return httpx.Response(404)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            detail = await identity.check(src)
            assert detail["doi_status"] == "mismatch"
    asyncio.run(scenario())


def test_doi_unavailable_on_network_failure_does_not_raise():
    src = source(doi="10.1234/synthetic")

    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            detail = await identity.check(src)
            assert detail["doi_status"] == "unavailable"
            assert src.independent_doi_status == "unavailable"
    asyncio.run(scenario())


def test_pmid_matched_and_tool_param_sent():
    src = source(pmid="123")

    def handler(request):
        assert "eutils.ncbi.nlm.nih.gov" in str(request.url)
        assert request.url.params["tool"] == "xpesquisa"
        return httpx.Response(200, json={"result": {"123": {"uid": "123", "title": "Synthetic Test Study"}}})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            detail = await identity.check(src)
            assert detail["pmid_status"] == "matched"
            assert src.independent_pmid_status == "matched"
    asyncio.run(scenario())


def test_pmid_mismatch_when_uid_absent():
    src = source(pmid="999")

    def handler(request):
        return httpx.Response(200, json={"result": {"uids": []}})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            detail = await identity.check(src)
            assert detail["pmid_status"] == "mismatch"
    asyncio.run(scenario())


def test_doi_and_pmid_checked_independently_together():
    src = source(doi="10.1234/synthetic", pmid="123")

    def handler(request):
        if "doi.org" in str(request.url):
            return httpx.Response(200, json={"title": "Synthetic Test Study"})
        return httpx.Response(200, json={"result": {"123": {"uid": "123", "title": "Different title here"}}})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            detail = await identity.check(src)
            assert detail["doi_status"] == "matched"
            assert detail["pmid_status"] == "mismatch"
            assert src.independent_doi_status == "matched"
            assert src.independent_pmid_status == "mismatch"
    asyncio.run(scenario())


def test_source_without_doi_or_pmid_is_not_checked():
    src = source()

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            detail = await identity.check(src)
            assert detail.get("status") == "not_checked"
            assert src.independent_doi_status == "not_checked"
            assert src.independent_pmid_status == "not_checked"
    asyncio.run(scenario())


def test_old_source_json_without_new_fields_loads_with_default():
    # Registro antigo persistido antes deste incremento, sem os campos novos.
    old = {"id": "old", "title": "Registro anterior", "source_url": "https://example.org",
           "external_id": "1", "collection": "MED", "response_sha256": "a" * 64}
    src = Source.model_validate(old)
    assert src.independent_doi_status == "not_checked"
    assert src.independent_pmid_status == "not_checked"


def test_rate_limiter_spaces_calls():
    async def scenario():
        limiter = RateLimiter(0.05)
        loop = asyncio.get_event_loop()
        start = loop.time()
        await limiter.wait()
        await limiter.wait()
        elapsed = loop.time() - start
        assert elapsed >= 0.05
    asyncio.run(scenario())


def test_html_markup_in_title_does_not_cause_false_mismatch():
    # "Effects of <i>Helicobacter pylori</i>..." deve bater com o mesmo
    # título sem a tag: plain_text remove a marcação antes de normalizar.
    src = source(doi="10.1234/synthetic",
                 title="Effects of <i>Helicobacter pylori</i> eradication on synthetic outcomes")

    def handler(request):
        return httpx.Response(200, json={"title": "Effects of Helicobacter pylori eradication on synthetic outcomes"})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            detail = await identity.check(src)
            assert detail["doi_status"] == "matched"
            assert src.independent_doi_status == "matched"
    asyncio.run(scenario())


def test_crossref_scielo_doi_is_not_checked_not_independent():
    # DOI já veio do próprio Crossref (depositante SciELO); doi.org
    # resolveria a mesma origem, então não é checado.
    src = source(doi="10.1234/synthetic", collection="CROSSREF_SCIELO")
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"title": "Synthetic Test Study"})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            detail = await identity.check(src)
            assert detail["doi_status"] == "not_checked"
            assert src.independent_doi_status == "not_checked"
    asyncio.run(scenario())
    assert calls == []


def test_after_first_doi_failure_remaining_sources_skip_network_in_same_search():
    sources = [source(id="s1", doi="10.1234/one"), source(id="s2", doi="10.1234/two"),
               source(id="s3", doi="10.1234/three")]
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ConnectError("offline", request=request)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            details = await identity.check_sources(sources)
            assert [d["doi_status"] for d in details] == ["unavailable", "unavailable", "unavailable"]
            assert [s.independent_doi_status for s in sources] == ["unavailable"] * 3
    asyncio.run(scenario())
    # Só a primeira fonte de fato tentou a rede; as seguintes foram puladas pelo circuito.
    assert len(calls) == 1


def test_after_first_pmid_failure_remaining_sources_skip_network_in_same_search():
    sources = [source(id="s1", pmid="1"), source(id="s2", pmid="2")]
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ConnectError("offline", request=request)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            details = await identity.check_sources(sources)
            assert [d["pmid_status"] for d in details] == ["unavailable", "unavailable"]
    asyncio.run(scenario())
    assert len(calls) == 1


def test_doi_and_pmid_circuits_are_independent():
    # Falha no DOI não deve acionar o circuito do PMID e vice-versa.
    sources = [source(id="s1", doi="10.1234/one"), source(id="s2", pmid="2")]

    def handler(request):
        if "doi.org" in str(request.url):
            raise httpx.ConnectError("offline", request=request)
        return httpx.Response(200, json={"result": {"2": {"uid": "2", "title": "Synthetic Test Study"}}})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            details = await identity.check_sources(sources)
            assert details[0]["doi_status"] == "unavailable"
            assert details[1]["pmid_status"] == "matched"
    asyncio.run(scenario())


def test_doi_redirect_to_allowed_metadata_host_is_followed():
    src = source(doi="10.1234/synthetic")

    def handler(request):
        if str(request.url) == "https://doi.org/10.1234/synthetic":
            return httpx.Response(302, headers={"Location": "https://api.crossref.org/works/10.1234/synthetic"})
        assert request.url.host == "api.crossref.org"
        return httpx.Response(200, json={"title": "Synthetic Test Study"})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            detail = await identity.check(src)
            assert detail["doi_status"] == "matched"
    asyncio.run(scenario())


def test_doi_redirect_to_untrusted_host_is_not_followed():
    src = source(doi="10.1234/synthetic")
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={"Location": "https://publisher.example/paper/123"})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            identity = IndependentIdentity(client, doi_limiter=RateLimiter(0), pubmed_limiter=RateLimiter(0))
            detail = await identity.check(src)
            assert detail["doi_status"] == "unavailable"
            assert src.independent_doi_status == "unavailable"
    asyncio.run(scenario())
    # Nenhuma segunda chamada foi feita ao destino não confiável.
    assert len(calls) == 1
