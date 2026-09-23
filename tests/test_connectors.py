import asyncio

import httpx
import pytest

from xpesquisa.connectors import ConnectorError, EuropePMC, plain_text


def test_markup_preserves_scientific_comparisons():
    assert plain_text('<p><i>P</i> < 0.05 and n &gt; 100.</p>') == 'P < 0.05 and n > 100.'
    assert plain_text('AUROC 0.85 < 0.90; CI &lt; 1.') == 'AUROC 0.85 < 0.90; CI < 1.'


def test_search_and_identifier(payload):
    async def scenario():
        seen = []
        def handler(request):
            seen.append(request)
            return httpx.Response(200, json=payload)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            connector = EuropePMC(client)
            sources, detail = await connector.search("test & query", 5)
            assert len(sources) == 1 and sources[0].pmid == "123"
            assert "<h4>" not in sources[0].abstract
            assert len(detail["response_sha256"]) == 64
            assert seen[0].url.params["query"] == "test & query"
            check = await connector.check_identifier(sources[0])
            assert check["status"] == "matched"
            assert "EXT_ID:123" in seen[1].url.params["query"]
    asyncio.run(scenario())


def test_empty_is_distinct_from_invalid():
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"version":"6.9"}))) as client:
            with pytest.raises(ConnectorError, match="incompleta"):
                await EuropePMC(client).search("test", 5)
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"hitCount":0,"resultList":{"result":[]}}))) as client:
            sources, detail = await EuropePMC(client).search("test", 5)
            assert sources == [] and detail["hit_count"] == 0
    asyncio.run(scenario())


def test_mismatch(payload):
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))) as client:
            connector = EuropePMC(client)
            sources, _ = await connector.search("test", 1)
            sources[0].doi = "10.0000/wrong"
            assert (await connector.check_identifier(sources[0]))["status"] == "mismatch"
    asyncio.run(scenario())


def test_network_failure_retries():
    async def scenario():
        calls = []
        def handler(request):
            calls.append(request)
            raise httpx.ConnectError("offline", request=request)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(ConnectorError):
                await EuropePMC(client).search("test", 1)
        assert len(calls) == 3
    asyncio.run(scenario())


def test_deduplicate_and_skip_invalid(payload, article):
    payload["resultList"]["result"] = [article, article, {"title":"missing id"}]
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200,json=payload))) as client:
            sources, detail = await EuropePMC(client).search("test", 3)
            assert len(sources) == 1
            assert detail["skipped_records"] == 1
    asyncio.run(scenario())
