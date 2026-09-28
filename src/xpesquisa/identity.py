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

Quatro pontos de revisão, aplicados aqui:

1. Títulos comparados após `plain_text` (mesmo parser HTML do
   connectors.py), não só normalizados: uma tag como `<i>` deixaria uma
   letra solta ("i") no texto e produziria mismatch falso.
2. Fontes cujo DOI já veio do próprio Crossref (collection CROSSREF_SCIELO)
   não passam pela checagem de DOI: doi.org resolveria a mesma origem, não
   seria uma segunda fonte independente. Ficam `not_checked`.
3. Circuito por pesquisa: assim que doi.org ou o NCBI falhar uma vez dentro
   da mesma pesquisa, as fontes seguintes do mesmo serviço são marcadas
   `unavailable` sem nova tentativa de rede.
4. O cliente do projeto não segue redirecionamentos por padrão (mesmo
   princípio de crossref.py/brazil.py). A checagem de DOI segue, no máximo,
   um redirecionamento do doi.org, e só quando o destino é um servidor de
   metadados conhecido do Crossref ou da DataCite; qualquer outro destino é
   tratado como `unavailable`, sem seguir.
"""
import asyncio
import re
import unicodedata

import httpx

from .connectors import plain_text
from .models import Source

DOI_ENDPOINT = "https://doi.org/{doi}"
PUBMED_ENDPOINT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
USER_AGENT = "XPesquisa/0.3 (https://github.com/Xdiag-IA/xpesquisa; independent identity check)"
TOOL_NAME = "xpesquisa"
# Servidores de metadados oficiais para os quais um redirecionamento do
# doi.org é seguido. Qualquer outro destino (ex.: página do editor) é
# tratado como unavailable, sem seguir.
ALLOWED_METADATA_HOSTS = {"api.crossref.org", "data.crosscite.org", "api.datacite.org"}
SCOPE_NOTE = ("Resolução independente via DOI.org e/ou NCBI PubMed, fora da base Europe PMC. "
              "DOI do próprio depósito Crossref/SciELO não é verificado por não ser fonte independente. "
              "Redirecionamento do doi.org só é seguido para servidores de metadados Crossref/DataCite.")


def normalized_title(value: str) -> str:
    """Minúsculas, sem acento, sem pontuação, espaços colapsados — só para comparar títulos."""
    text = unicodedata.normalize("NFKD", value.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def comparable_title(value: str) -> str:
    """Remove marcação HTML antes de normalizar, para tag não virar texto (ex.: <i> não vira "i")."""
    return normalized_title(plain_text(value))


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
        headers = {"Accept": "application/vnd.citationstyles.csl+json", "User-Agent": USER_AGENT}
        try:
            response = await self.client.get(DOI_ENDPOINT.format(doi=doi), headers=headers,
                                              follow_redirects=False, timeout=20)
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location", "")
                host = httpx.URL(location).host if location else None
                if host not in ALLOWED_METADATA_HOSTS:
                    return {"status": "unavailable", "checked_title": None}
                response = await self.client.get(location, headers=headers, timeout=20)
            if response.status_code == 404:
                return {"status": "mismatch", "checked_title": None}
            response.raise_for_status()
            data = response.json()
            remote_title = data.get("title", "") if isinstance(data, dict) else ""
            ok = bool(remote_title) and comparable_title(remote_title) == comparable_title(title)
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
            ok = bool(remote_title) and comparable_title(remote_title) == comparable_title(title)
            return {"status": "matched" if ok else "mismatch", "checked_title": remote_title or None}
        except (httpx.HTTPError, ValueError):
            return {"status": "unavailable", "checked_title": None}

    async def check_sources(self, sources: list[Source]) -> list[dict]:
        """Verifica DOI/PMID independentes para as fontes de UMA pesquisa.

        Assim que doi.org ou o NCBI falhar (rede/HTTP indisponível) uma vez
        nesta chamada, as fontes seguintes do mesmo serviço são marcadas
        unavailable sem nova tentativa de rede.
        """
        doi_broken = pmid_broken = False
        details = []
        for source in sources:
            detail = {"source_id": source.id, "scope": SCOPE_NOTE}
            checked_any = False
            if source.doi:
                checked_any = True
                if source.collection == "CROSSREF_SCIELO":
                    source.independent_doi_status = "not_checked"
                    detail["doi_status"] = "not_checked"
                    detail["doi_note"] = ("DOI do próprio depósito Crossref/SciELO; doi.org resolveria a "
                                           "mesma origem, não é uma segunda fonte independente.")
                elif doi_broken:
                    source.independent_doi_status = "unavailable"
                    detail["doi_status"] = "unavailable"
                    detail["doi_note"] = "doi.org já falhou nesta pesquisa; sem nova tentativa."
                else:
                    result = await self.resolve_doi(source.doi, source.title)
                    source.independent_doi_status = result["status"]
                    detail["doi_status"] = result["status"]
                    if result["status"] == "unavailable":
                        doi_broken = True
            if source.pmid:
                checked_any = True
                if pmid_broken:
                    source.independent_pmid_status = "unavailable"
                    detail["pmid_status"] = "unavailable"
                    detail["pmid_note"] = "NCBI já falhou nesta pesquisa; sem nova tentativa."
                else:
                    result = await self.resolve_pmid(source.pmid, source.title)
                    source.independent_pmid_status = result["status"]
                    detail["pmid_status"] = result["status"]
                    if result["status"] == "unavailable":
                        pmid_broken = True
            if not checked_any:
                detail["status"] = "not_checked"
            details.append(detail)
        return details

    async def check(self, source: Source) -> dict:
        """Conveniência para uma única fonte; sem estado de circuito entre chamadas."""
        return (await self.check_sources([source]))[0]
