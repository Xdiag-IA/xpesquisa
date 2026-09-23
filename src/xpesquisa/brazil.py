"""Conectores de domínios oficiais, sem motor pago ou contorno de bloqueios."""
import asyncio
import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from .connectors import ConnectorError, plain_text
from .models import Source

AGENT = "XPesquisa"
SITES = {
    "cfm": ("https://portal.cfm.org.br", "CFM e CRMs"),
    "sbh": ("https://sbhepatologia.org.br", "Sociedade Brasileira de Hepatologia"),
    "cbr": ("https://cbr.org.br", "Colégio Brasileiro de Radiologia"),
}


class AccessBlocked(ConnectorError):
    pass


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def same_origin(url: str, base: str) -> bool:
    target, origin = urlparse(url), urlparse(base)
    return (target.scheme == "https" and target.hostname == origin.hostname
            and target.port in {None, 443} and not target.username and not target.password)


class OfficialAccess:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.robots: dict[str, RobotFileParser] = {}
        self.locks: dict[str, asyncio.Lock] = {}

    async def raw(self, url: str, base: str, params=None) -> httpx.Response:
        for _ in range(3):
            if not same_origin(url, base):
                raise AccessBlocked("Redirecionamento ou endereço fora do domínio oficial permitido.")
            async with self.client.stream("GET", url, params=params, timeout=20,
                                          headers={"User-Agent": "XPesquisa/0.2 (+local research)"},
                                          follow_redirects=False) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    url = urljoin(str(response.url), response.headers.get("location", ""))
                    params = None
                    # Do not follow page redirects into a path whose robots permission wasn't checked.
                    policy = self.robots.get(base)
                    if policy is not None and not policy.can_fetch(AGENT, url):
                        raise AccessBlocked("Destino bloqueado por robots.txt.")
                    continue
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 3_000_000:
                        raise ConnectorError("Documento excede o limite de leitura desta versão.")
                headers = {k: v for k, v in response.headers.items() if k not in {"content-encoding", "content-length"}}
                return httpx.Response(response.status_code, headers=headers, content=bytes(body), request=response.request)
        raise ConnectorError("Número máximo de redirecionamentos atingido.")

    async def get(self, url: str, base: str, params=None) -> httpx.Response:
        if not same_origin(url, base):
            raise AccessBlocked("Endereço fora do domínio oficial permitido.")
        lock = self.locks.setdefault(base, asyncio.Lock())
        async with lock:
            if base not in self.robots:
                robots = await self.raw(base + "/robots.txt", base)
                if robots.status_code not in {200, 404}:
                    raise AccessBlocked(f"Não foi possível confirmar a política de acesso (robots HTTP {robots.status_code}).")
                if robots.status_code == 200 and "<html" in robots.text.lower():
                    raise AccessBlocked("robots.txt retornou uma página de bloqueio ou formato inesperado.")
                policy = RobotFileParser(base + "/robots.txt")
                policy.parse(robots.text.splitlines() if robots.status_code == 200 else [])
                self.robots[base] = policy
            policy = self.robots[base]
            full_url = str(httpx.URL(url, params=params)) if params else url
            if not policy.can_fetch(AGENT, full_url):
                raise AccessBlocked("Consulta não permitida por robots.txt.")
            delay = policy.crawl_delay(AGENT) or policy.crawl_delay("*") or 0
            rate = policy.request_rate(AGENT) or policy.request_rate("*")
            if rate:
                delay = max(delay, rate.seconds / rate.requests)
            if delay > 10:
                raise AccessBlocked("Política de acesso exige intervalo acima do orçamento desta consulta.")
            await asyncio.sleep(max(.25, delay))
            response = await self.raw(url, base, params)
            if response.status_code in {401, 403, 429}:
                raise AccessBlocked(f"Site restringiu a consulta (HTTP {response.status_code}); sem tentativa de contorno.")
            response.raise_for_status()
            return response


def parse_norms(content: str, response_hash: str, retrieval_url: str, limit: int) -> list[Source]:
    if 'id="resultsNormas"' not in content and "id='resultsNormas'" not in content:
        if "Não há resultados para esses parâmetros de busca." in plain_text(content):
            return []
        raise ConnectorError("Estrutura de resultados do CFM não reconhecida; não equivale a zero normas.")
    # Cards are a bounded, source-specific HTML structure; no scripts or hidden API endpoints used.
    cards = re.findall(r"<article\b[^>]*>(.*?)</article>", content, re.S | re.I)
    sources = []
    for card in cards:
        links = Links()
        links.feed(card)
        target = next((link for link in links.links if re.fullmatch(
            r"https://sistemas\.cfm\.org\.br/normas/visualizar/(resolucoes|pareceres)/[A-Z]{2}/\d{4}/\d+", link)), None)
        if not target:
            continue
        kind, uf, year, number = target.split("/")[-4:]
        excerpt_match = re.search(r"<strong[^>]*>\s*Ementa\s*</strong>\s*<span[^>]*>(.*?)</span>", card, re.S | re.I)
        status_match = re.search(r"<strong[^>]*>\s*Situação\s*</strong>\s*<p[^>]*>(.*?)</p>", card, re.S | re.I)
        if not excerpt_match:
            raise ConnectorError("Ementa ausente em resultado do CFM; estrutura alterada.")
        institution = "CFM" if uf == "BR" else f"CRM-{uf}"
        title = f"{'Resolução' if kind == 'resolucoes' else 'Parecer'} {institution} {number}/{year}"
        sources.append(Source(
            id=f"cfm:{kind}:{uf}:{year}:{number}", title=title, source="CFM e CRMs",
            source_url=target, external_id=f"{kind}/{uf}/{year}/{number}", collection="CFM",
            publication_date=year, abstract=plain_text(excerpt_match.group(1)), response_sha256=response_hash,
            document_type="regulation", content_kind="ementa", institution_country="BR", jurisdiction=uf,
            study_types=["Norma profissional — " + ("resolução" if kind == "resolucoes" else "parecer")],
            regulatory_status=plain_text(status_match.group(1)) if status_match else "Não informada",
            retrieval_url=retrieval_url))
    if cards and not sources:
        raise ConnectorError("Resultados do CFM não puderam ser interpretados; não equivale a zero normas.")
    return sources[:limit]


class BrazilSearch:
    def __init__(self, client: httpx.AsyncClient):
        self.access = OfficialAccess(client)

    async def search(self, connector: str, query: str, limit: int, uf: str | None = None):
        base, label = SITES[connector]
        if connector == "cfm":
            sources, queries, failures = [], [], []
            for jurisdiction in (["BR", uf] if uf else [None]):
                params = [("texto", query), ("tipo[]", "R"), ("tipo[]", "P")]
                if jurisdiction:
                    params.append(("uf", jurisdiction))
                try:
                    response = await self.access.get(base + "/buscar-normas-cfm-e-crm/", base, params)
                    digest = hashlib.sha256(response.content).hexdigest()
                    sources.extend(parse_norms(response.text, digest, str(response.url), limit))
                    queries.append({"url": str(response.url), "response_sha256": digest, "jurisdiction": jurisdiction})
                except (httpx.HTTPError, ConnectorError) as exc:
                    if not queries and (not uf or jurisdiction == uf):
                        raise
                    failures.append({"jurisdiction": jurisdiction, "error_type": type(exc).__name__})
            # When a state is selected, retain both national and state results (bounded per query).
            sources = list({s.id: s for s in sources}.values())
            return sources, {"queries": queries, "query": query,
                             "retrieved_ids": [s.id for s in sources], "scope": "Ementas e metadados; íntegra não lida",
                             "robots_checked": True, "failed_queries": failures, "types": ["resolução", "parecer"]}

        response = await self.access.get(base + "/wp-json/wp/v2/search", base,
                                         {"search": query, "per_page": min(limit, 5), "type": "post"})
        results = response.json()
        if not isinstance(results, list):
            raise ConnectorError("Busca institucional retornou formato inesperado.")
        sources, failures, documents = [], [], []
        for item in results:
            try:
                url = item["url"]
                api_url = item["_links"]["self"][0]["href"]
                if not same_origin(url, base) or not same_origin(api_url, base):
                    raise AccessBlocked("Resultado fora do domínio da instituição.")
                if not re.fullmatch(r"/wp-json/wp/v2/(posts|pages)/\d+", urlparse(api_url).path):
                    raise ConnectorError("Tipo institucional sem leitor implementado.")
                document = await self.access.get(api_url, base)
                data = document.json()
                if str(data.get("id")) != str(item["id"]):
                    raise ConnectorError("Identidade divergente no documento institucional.")
                if data.get("content", {}).get("protected") or data.get("status", "publish") != "publish":
                    raise AccessBlocked("Conteúdo restrito; não recuperado.")
                rendered = data.get("content", {}).get("rendered", "")
                text = plain_text(rendered)
                links = Links()
                links.feed(rendered)
                related = list(dict.fromkeys(urljoin(url, link) for link in links.links
                              if same_origin(urljoin(url, link), base) and urlparse(urljoin(url, link)).path.lower().endswith(".pdf")))[:10]
                digest = hashlib.sha256(document.content).hexdigest()
                sources.append(Source(
                    id=f"{connector}:{item['id']}", source=label, title=plain_text(data.get("title", {}).get("rendered") or item["title"]),
                    source_url=url, external_id=str(item["id"]), collection=connector.upper(),
                    publication_date=(data.get("date") or "")[:10] or None,
                    abstract=text[:16000], response_sha256=digest, document_type="institutional",
                    content_kind="institutional_text", institution_country="BR", retrieval_url=str(document.url),
                    related_urls=related, study_types=["Publicação institucional — classificação editorial não avaliada"]))
                documents.append({"url": str(document.url), "response_sha256": digest, "truncated": len(text) > 16000})
            except (httpx.HTTPError, ConnectorError, KeyError, TypeError, ValueError) as exc:
                failures.append({"id": str(item.get("id", "")), "reason": type(exc).__name__})
        if results and not sources:
            raise ConnectorError("Itens localizados, mas seus documentos não puderam ser recuperados.")
        return sources, {"endpoint": str(response.url), "query": query, "robots_checked": True,
                         "response_sha256": hashlib.sha256(response.content).hexdigest(), "documents": documents,
                         "retrieved_ids": [s.id for s in sources], "failed_documents": failures,
                         "scope": "Publicações institucionais; não presumir diretriz, estudo ou recomendação validada"}
