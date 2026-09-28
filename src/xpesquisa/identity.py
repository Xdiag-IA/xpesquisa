"""Resolução independente de DOI/PMID.

Complementa EuropePMC.check_identifier, que reconfirma id/título/DOI apenas
dentro da própria base Europe PMC (ver docs/adr/0010-independent-identity.md).
Aqui a checagem consulta duas fontes fora do Europe PMC:

- DOI.org (negociação de conteúdo CSL-JSON, mantida pela Crossref/DataCite);
- NCBI E-utilities `esummary` (PubMed), para PMID.

Ambas são APIs públicas, sem chave obrigatória. Seguimos as políticas de uso
publicadas: identificação da ferramenta e limite de requisições.
- NCBI: no máximo 3 requisições/segundo sem chave de API.
  https://www.ncbi.nlm.nih.gov/books/NBK25497/#chapter2.Usage_Guidelines_and_Requiremen
- Crossref/DOI.org: recomenda identificar a ferramenta e o contato ("polite
  pool"); não publica um limite numérico fixo para doi.org, então adotamos um
  espaçamento cortês (1 req/s) por conta própria.
  https://api.crossref.org/swagger-ui/index.html#/Works
"""
import asyncio
import re
import unicodedata

import httpx

from .models import Source

DOI_ENDPOINT = "https://doi.org/{doi}"
PUBMED_ENDPOINT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
USER_AGENT = "XPesquisa/0.3 (https://github.com/Xdiag-IA/xpesquisa; independent identity check)"
TOOL_NAME = "xpesquisa"


def normalized_title(value: str) -> str:
    """Minúsculas, sem acento, sem pontuação, espaços colapsados — só para comparar títulos."""
    text = unicodedata.normalize("NFKD", value.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


class RateLimiter:
    """Espaçamento mínimo entre chamadas ao mesmo host; cortesia e conformidade com limites publicados."""

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._lock = asyncio.Lock()
        self._last = None

    async def wait(self):
        async with self._lock:
            loop = asyncio.get_event_loop()
            now = loop.time()
            if self._last is not None:
                delta = now - self._last
                if delta < self.min_interval:
                    await asyncio.sleep(self.min_interval - delta)
            self._last = loop.time()


class IndependentIdentity:
    """Resolução independente de DOI (doi.org) e PMID (NCBI E-utilities esummary)."""

    def __init__(self, client: httpx.AsyncClient, doi_limiter: RateLimiter | None = None,
                 pubmed_limiter: RateLimiter | None = None):
        self.client = client
        self.doi_limiter = doi_limiter or RateLimiter(1.0)
        self.pubmed_limiter = pubmed_limiter or RateLimiter(1 / 3)

    async def resolve_doi(self, doi: str, title: str) -> dict:
        await self.doi_limiter.wait()
        try:
            response = await self.client.get(
                DOI_ENDPOINT.format(doi=doi),
                headers={"Accept": "application/vnd.citationstyles.csl+json", "User-Agent": USER_AGENT},
                follow_redirects=True, timeout=20)
            if response.status_code == 404:
                return {"status": "mismatch", "checked_title": None}
            response.raise_for_status()
            data = response.json()
            remote_title = data.get("title", "") if isinstance(data, dict) else ""
            ok = bool(remote_title) and normalized_title(remote_title) == normalized_title(title)
            return {"status": "matched" if ok else "mismatch", "checked_title": remote_title or None}
        except (httpx.HTTPError, ValueError):
            return {"status": "unavailable", "checked_title": None}

    async def resolve_pmid(self, pmid: str, title: str) -> dict:
        await self.pubmed_limiter.wait()
        try:
            params = {"db": "pubmed", "id": pmid, "format": "json", "tool": TOOL_NAME}
            response = await self.client.get(PUBMED_ENDPOINT, params=params,
                                              headers={"User-Agent": USER_AGENT}, timeout=20)
            response.raise_for_status()
            data = response.json()
            record = data.get("result", {}).get(pmid) if isinstance(data, dict) else None
            if not isinstance(record, dict) or str(record.get("uid")) != str(pmid):
                return {"status": "mismatch", "checked_title": None}
            remote_title = record.get("title", "")
            ok = bool(remote_title) and normalized_title(remote_title) == normalized_title(title)
            return {"status": "matched" if ok else "mismatch", "checked_title": remote_title or None}
        except (httpx.HTTPError, ValueError):
            return {"status": "unavailable", "checked_title": None}

    async def check(self, source: Source) -> dict:
        detail = {"source_id": source.id,
                   "scope": "Resolução independente via DOI.org e/ou NCBI PubMed; fora da base Europe PMC."}
        if source.doi:
            result = await self.resolve_doi(source.doi, source.title)
            source.independent_doi_status = result["status"]
            detail["doi_status"] = result["status"]
        if source.pmid:
            result = await self.resolve_pmid(source.pmid, source.title)
            source.independent_pmid_status = result["status"]
            detail["pmid_status"] = result["status"]
        if not source.doi and not source.pmid:
            detail["status"] = "not_checked"
        return detail
