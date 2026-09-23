"""Europe PMC: acesso oficial limitado a metadados e abstracts."""
import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import quote

import httpx

from .models import Source

ENDPOINT = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


class ConnectorError(Exception):
    pass


def plain_text(value: str) -> str:
    class TextParser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.parts = []
            self.skip = 0

        def handle_data(self, data):
            if not self.skip:
                self.parts.append(data)

        def handle_starttag(self, tag, attrs):
            if tag in {"script", "style", "noscript"}:
                self.skip += 1
            if tag in {"p", "h4", "br", "div", "section"}:
                self.parts.append(" ")

        def handle_endtag(self, tag):
            if tag in {"script", "style", "noscript"}:
                self.skip = max(0, self.skip - 1)
            if tag in {"p", "h4", "div", "section"}:
                self.parts.append(" ")

    parser = TextParser()
    parser.feed(value)
    parser.close()
    return " ".join("".join(parser.parts).split())


class EuropePMC:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def fetch(self, query: str, limit: int) -> tuple[dict, str, dict]:
        params = {"query": query, "format": "json", "resultType": "core", "pageSize": str(limit)}
        # Retry only transient upstream/network failures; bounded and no scraping fallback.
        for attempt in range(3):
            try:
                response = await self.client.get(ENDPOINT, params=params)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < 2:
                        import asyncio
                        await asyncio.sleep(1 + attempt)
                        continue
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload.get("resultList", {}).get("result"), list) or "hitCount" not in payload:
                    raise ConnectorError("Resposta incompleta do Europe PMC; não equivale a busca sem resultados.")
                digest = hashlib.sha256(response.content).hexdigest()
                return payload, digest, {"endpoint": ENDPOINT, "params": params, "response_sha256": digest,
                                         "attempts": attempt + 1, "hit_count": payload["hitCount"],
                                         "api_version": payload.get("version")}
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt == 2:
                    raise ConnectorError("Europe PMC indisponível após três tentativas.") from None
            except (httpx.HTTPStatusError, ValueError) as exc:
                raise ConnectorError("Falha HTTP ou resposta inválida do Europe PMC.") from exc
        raise ConnectorError("Busca interrompida.")

    async def search(self, query: str, limit: int):
        payload, digest, detail = await self.fetch(query, limit)
        sources, skipped, seen = [], 0, set()
        for record in payload["resultList"]["result"]:
            external_id, collection = str(record.get("id", "")), record.get("source", "")
            if not external_id or not re.fullmatch(r"[A-Z]+", collection) or not record.get("title"):
                skipped += 1
                continue
            key = f"epmc:{collection}:{external_id}"
            if key in seen:
                continue
            seen.add(key)
            doi = record.get("doi")
            sources.append(Source(
                id=key, title=plain_text(record["title"]), external_id=external_id, collection=collection,
                source_url=f"https://europepmc.org/article/{collection}/{quote(external_id, safe='')}",
                doi=doi, pmid=external_id if collection == "MED" and external_id.isdigit() else None,
                authors=[a["fullName"] for a in record.get("authorList", {}).get("author", []) if a.get("fullName")],
                publication_date=record.get("firstPublicationDate") or record.get("pubYear"),
                study_types=record.get("pubTypeList", {}).get("pubType", []),
                abstract=plain_text(record.get("abstractText", "")), license=record.get("license"),
                response_sha256=digest))
        detail["skipped_records"] = skipped
        detail["retrieved_ids"] = [s.id for s in sources]
        return sources, detail

    async def check_identifier(self, source: Source) -> dict:
        if not re.fullmatch(r"[A-Za-z0-9.-]+", source.external_id):
            source.identifier_status = "unavailable"
            return {"source_id": source.id, "status": "unavailable"}
        query = f'EXT_ID:{source.external_id} AND SRC:{source.collection}'
        try:
            data, _, detail = await self.fetch(query, 1)
            records = data["resultList"]["result"]
            match = next((r for r in records if str(r.get("id")) == source.external_id and r.get("source") == source.collection), None)
            ok = match is not None and plain_text(match.get("title", "")) == source.title
            if source.doi:
                ok = ok and str(match.get("doi", "") if match else "").lower() == source.doi.lower()
            source.identifier_status = "matched" if ok else "mismatch"
            return {**detail, "source_id": source.id, "status": source.identifier_status,
                    "scope": "Identificador, título e DOI quando disponível, na mesma base; sem resolução independente."}
        except ConnectorError:
            source.identifier_status = "unavailable"
            return {"source_id": source.id, "query": query, "status": "unavailable"}
