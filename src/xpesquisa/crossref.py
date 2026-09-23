"""Public Crossref metadata, restricted to the verified SciELO depositor.

This is not a request to SciELO's search portal or a full-text reader.
"""
import hashlib
import re
from urllib.parse import quote

import httpx

from .connectors import ConnectorError, plain_text
from .models import Source
from .planning import normalized

ENDPOINT = "https://api.crossref.org/members/530/works"
ALIASES = {
    "ultrassonografia": ("ultrass", "ultrason", "ultrasound", "sonograph", "ecograf"),
    "punho": ("punho", "wrist", "carpal", "carpo"),
    "ombro": ("ombro", "shoulder"), "joelho": ("joelho", "knee"),
    "tornozelo": ("tornozelo", "ankle"), "cotovelo": ("cotovelo", "elbow"),
    "elastografia": ("elastograf", "elastograph", "liver stiffness"),
    "esteatose": ("esteatos", "steatos", "fatty liver", "masld", "nafld"),
}


def lexical_match(query: str, content: str) -> bool:
    # Crossref relevance search is not Boolean AND. Require each meaningful concept.
    tokens = [w for w in re.findall(r"\w+", normalized(query))
              if len(w) > 2 and w not in {"and", "para", "com", "sobre", "dos", "das"}]
    value = normalized(content)
    return all(any(term in value for term in ALIASES.get(w, (w,))) for w in tokens)


class SciELODeposits:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def search(self, query: str, limit: int):
        params = {"query.bibliographic": query, "rows": 20, "filter": "type:journal-article"}
        async with self.client.stream("GET", ENDPOINT, params=params, follow_redirects=False,
                                      headers={"User-Agent": "XPesquisa/0.3 (https://github.com/Xdiag-IA/xpesquisa)"}) as response:
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 3_000_000:
                    raise ConnectorError("Resposta Crossref excede o limite de leitura.")
            import json
            try:
                payload = json.loads(body)
            except ValueError as exc:
                raise ConnectorError("Resposta Crossref inválida; não equivale a busca vazia.") from exc
            retrieval_url = str(response.url)
        message = payload.get("message", {})
        if payload.get("status") != "ok" or not isinstance(message.get("items"), list) or "total-results" not in message:
            raise ConnectorError("Resposta incompleta do Crossref; não equivale a busca vazia.")
        digest = hashlib.sha256(body).hexdigest()
        sources, excluded, malformed, seen = [], [], 0, set()
        for record in message["items"]:
            doi = record.get("DOI", "")
            titles = record.get("title", [])
            if (not re.fullmatch(r"10\.\d{4,9}/\S+", doi, re.I) or not titles
                    or str(record.get("member")) != "530" or record.get("type") != "journal-article"):
                malformed += 1
                continue
            title = plain_text(titles[0])
            abstract = plain_text(record.get("abstract", ""))
            if not lexical_match(query, title + " " + abstract):
                excluded.append(doi)
                continue
            if doi.lower() in seen:
                continue
            seen.add(doi.lower())
            parts = record.get("published", {}).get("date-parts", [[]])[0]
            date = "-".join(str(x).zfill(2) for x in parts) or None
            sources.append(Source(
                id="crossref:" + doi.lower(), source="Crossref — depositante FapUNIFESP/SciELO",
                title=title, source_url="https://doi.org/" + quote(doi, safe="/"),
                external_id=doi, collection="CROSSREF_SCIELO", doi=doi, abstract=abstract,
                authors=[" ".join(filter(None, (a.get("given"), a.get("family")))) for a in record.get("author", [])],
                publication_date=date, study_types=["Artigo — metadados depositados no Crossref"],
                response_sha256=digest, retrieval_url=retrieval_url,
                selection_note="Correspondência lexical nos metadados; consulta indireta via Crossref, não busca direta SciELO. "
                               + ("Resumo disponível no depósito; relevância e qualidade não avaliadas." if abstract else "Sem resumo no depósito; nenhuma afirmação será extraída deste registro.")))
        if message["items"] and malformed == len(message["items"]):
            raise ConnectorError("Registros Crossref não reconhecidos; não equivale a busca vazia.")
        return sources[:limit], {"endpoint": ENDPOINT, "query": query, "params": params,
                                 "response_sha256": digest, "hit_count": message["total-results"],
                                 "candidate_count": len(message["items"]), "excluded_dois": excluded,
                                 "skipped_records": malformed, "retrieved_ids": [s.id for s in sources[:limit]],
                                 "scope": "Metadados do depositante 530 via Crossref; não é busca direta nem cobertura integral SciELO."}
