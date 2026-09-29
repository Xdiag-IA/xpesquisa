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

Pontos de revisão aplicados aqui:

1. Títulos comparados após `plain_text` (mesmo parser HTML do
   connectors.py), não só normalizados: uma tag como `<i>` deixaria uma
   letra solta ("i") no texto e produziria mismatch falso.
2. Fontes cujo DOI já veio do próprio Crossref (collection CROSSREF_SCIELO)
   não passam pela checagem de DOI: doi.org resolveria a mesma origem, não
   seria uma segunda fonte independente. Ficam `not_checked`.
3. Circuito por pesquisa, mas só para problema do SERVIÇO (erro de rede,
   tempo esgotado, HTTP 5xx ou 429): uma vez aberto, as fontes seguintes do
   mesmo serviço na mesma pesquisa são marcadas `unavailable` sem nova
   tentativa. Um problema do REGISTRO (4xx que não seja 429, ou
   redirecionamento para destino fora da lista permitida) marca só aquele
   DOI/PMID e não abre o circuito — o próximo registro ainda é checado.
4. O cliente do projeto não segue redirecionamentos por padrão (mesmo
   princípio de crossref.py/brazil.py). A checagem de DOI segue, no máximo,
   um redirecionamento do doi.org, e só quando o esquema é HTTPS e o
   destino é um servidor de metadados conhecido do Crossref ou da
   DataCite; qualquer outro esquema ou destino é tratado como
   `unavailable` sem seguir, e sem abrir o circuito (problema do registro).
5. Comparação de título ignora todos os espaços, depois de remover
   marcação HTML e normalizar: uma tag colada à palavra seguinte sem
   espaço no HTML de origem (ex.: Crossref devolvendo
   "against<i>Plasmodium falciparum</i>Antigen" para o DOI
   10.1155/2014/642391, enquanto o Europe PMC devolve "against Plasmodium
   falciparum Antigen") perde o espaço na junção só por causa da marcação,
   não por diferença real de conteúdo; ignorar espaços nos dois lados evita
   esse mismatch falso.
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
# Servidores de metadados oficiais para os quais um redirecionamento HTTPS do
# doi.org é seguido. Qualquer outro esquema ou destino (ex.: página do
# editor) é tratado como unavailable, sem seguir e sem abrir o circuito.
ALLOWED_METADATA_HOSTS = {"api.crossref.org", "data.crosscite.org", "api.datacite.org"}
SCOPE_NOTE = ("Resolução independente via DOI.org e/ou NCBI PubMed, fora da base Europe PMC. "
              "DOI do próprio depósito Crossref/SciELO não é verificado por não ser fonte independente. "
              "Redirecionamento do doi.org só é seguido, via HTTPS, para servidores de metadados Crossref/DataCite.")
# Erro de rede/tempo esgotado é problema do serviço; abre o circuito.
NETWORK_ERRORS = (httpx.TimeoutException, httpx.NetworkError)


def normalized_title(value: str) -> str:
    """Minúsculas, sem acento, sem pontuação, espaços colapsados — só para comparar títulos."""
    text = unicodedata.normalize("NFKD", value.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def comparable_title(value: str) -> str:
    """Remove marcação HTML antes de normalizar, para tag não virar texto (ex.: <i> não vira "i")."""
    return normalized_title(plain_text(value))


def titles_match(a: str, b: str) -> bool:
    """Compara títulos ignorando espaços, depois de remover HTML e normalizar.

    Uma tag colada à palavra seguinte sem espaço no HTML de origem some com
    a separação entre palavras só por causa da marcação, não por diferença
    real de conteúdo; ignorar espaços nos dois lados evita esse mismatch
    falso (ex.: DOI 10.1155/2014/642391).
    """
    return comparable_title(a).replace(" ", "") == comparable_title(b).replace(" ", "")


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


def _unavailable(trip_breaker: bool) -> dict:
    return {"status": "unavailable", "checked_title": None, "trip_breaker": trip_breaker}


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
        except NETWORK_ERRORS:
            return _unavailable(trip_breaker=True)
        except httpx.HTTPError:
            return _unavailable(trip_breaker=False)

        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("location", "")
            url = httpx.URL(location) if location else None
            if url is None or url.scheme != "https" or url.host not in ALLOWED_METADATA_HOSTS:
                # Destino fora da lista, ou esquema não confiável: problema
                # deste registro, não do serviço. Não abre o circuito.
                return _unavailable(trip_breaker=False)
            try:
                response = await self.client.get(str(url), headers=headers, timeout=20)
            except NETWORK_ERRORS:
                return _unavailable(trip_breaker=True)
            except httpx.HTTPError:
                return _unavailable(trip_breaker=False)

        if response.status_code == 404:
            return {"status": "mismatch", "checked_title": None, "trip_breaker": False}
        if response.status_code == 429 or response.status_code >= 500:
            # Limite de requisições ou falha do servidor: problema do serviço.
            return _unavailable(trip_breaker=True)
        if response.status_code >= 400:
            # Outro 4xx (ex.: 406): recusa específica deste registro, não do serviço.
            return _unavailable(trip_breaker=False)
        try:
            data = response.json()
        except ValueError:
            return _unavailable(trip_breaker=False)
        remote_title = data.get("title", "") if isinstance(data, dict) else ""
        ok = bool(remote_title) and titles_match(remote_title, title)
        return {"status": "matched" if ok else "mismatch", "checked_title": remote_title or None,
                "trip_breaker": False}

    async def resolve_pmid(self, pmid: str, title: str) -> dict:
        await self.pubmed_limiter.wait()
        params = {"db": "pubmed", "id": pmid, "format": "json", "tool": TOOL_NAME}
        try:
            response = await self.client.get(PUBMED_ENDPOINT, params=params,
                                              headers={"User-Agent": USER_AGENT}, timeout=20)
        except NETWORK_ERRORS:
            return _unavailable(trip_breaker=True)
        except httpx.HTTPError:
            return _unavailable(trip_breaker=False)

        if response.status_code == 429 or response.status_code >= 500:
            return _unavailable(trip_breaker=True)
        if response.status_code >= 400:
            return _unavailable(trip_breaker=False)
        try:
            data = response.json()
        except ValueError:
            return _unavailable(trip_breaker=False)
        record = data.get("result", {}).get(pmid) if isinstance(data, dict) else None
        if not isinstance(record, dict) or str(record.get("uid")) != str(pmid):
            return {"status": "mismatch", "checked_title": None, "trip_breaker": False}
        remote_title = record.get("title", "")
        ok = bool(remote_title) and titles_match(remote_title, title)
        return {"status": "matched" if ok else "mismatch", "checked_title": remote_title or None,
                "trip_breaker": False}

    async def check_sources(self, sources: list[Source]) -> list[dict]:
        """Verifica DOI/PMID independentes para as fontes de UMA pesquisa.

        O circuito por serviço (doi.org / NCBI) só abre com um problema do
        serviço (rede, tempo esgotado, 5xx ou 429) — não com um 4xx isolado
        nem com um redirecionamento fora da lista permitida, que marcam
        apenas aquele registro e deixam os seguintes serem checados
        normalmente. Uma vez aberto, as fontes seguintes do mesmo serviço
        nesta pesquisa são marcadas unavailable sem nova tentativa de rede.
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
                    detail["doi_note"] = "doi.org já falhou (rede/tempo esgotado/5xx/429) nesta pesquisa; sem nova tentativa."
                else:
                    result = await self.resolve_doi(source.doi, source.title)
                    source.independent_doi_status = result["status"]
                    detail["doi_status"] = result["status"]
                    if result["trip_breaker"]:
                        doi_broken = True
            if source.pmid:
                checked_any = True
                if pmid_broken:
                    source.independent_pmid_status = "unavailable"
                    detail["pmid_status"] = "unavailable"
                    detail["pmid_note"] = "NCBI já falhou (rede/tempo esgotado/5xx/429) nesta pesquisa; sem nova tentativa."
                else:
                    result = await self.resolve_pmid(source.pmid, source.title)
                    source.independent_pmid_status = result["status"]
                    detail["pmid_status"] = result["status"]
                    if result["trip_breaker"]:
                        pmid_broken = True
            if not checked_any:
                detail["status"] = "not_checked"
            details.append(detail)
        return details

    async def check(self, source: Source) -> dict:
        """Conveniência para uma única fonte; sem estado de circuito entre chamadas."""
        return (await self.check_sources([source]))[0]
