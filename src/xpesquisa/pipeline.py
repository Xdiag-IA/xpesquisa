import logging
import re

from .brazil import AccessBlocked, BrazilSearch
from .connectors import ConnectorError, EuropePMC
from .crossref import SciELODeposits, lexical_match
from .models import Coverage, Event, Evidence, Run, validate_links
from .planning import brazil_terms, normalized, plan_research, ultrasound_anatomy
from .providers import ExtractiveProvider, SynthesisProvider
from .storage import Store

logger = logging.getLogger(__name__)


def extract(run: Run) -> list[Evidence]:
    result = []
    seen_dois = set()
    for source in run.sources:
        if not source.abstract or source.identifier_status == "mismatch":
            continue
        if source.doi and source.doi.lower() in seen_dois:
            source.selection_note = "Mesmo DOI já representado em outro trecho nesta pesquisa; mantido como fonte adicional sem repetir a afirmação."
            continue
        first_match = None
        if source.document_type != "scientific_article" and run.plan:
            if source.document_type == "institutional" and ultrasound_anatomy(normalized(run.request.question)):
                # A short institutional query improves recall, but "de próprio punho"
                # in application instructions is not anatomical wrist content.
                topical_text = normalized(source.title + " " + source.abstract).replace("proprio punho", "")
                if not lexical_match(brazil_terms(run.request.question), topical_text):
                    source.selection_note = "Candidato fora da síntese: modalidade e anatomia não aparecem juntas no conteúdo. Correspondência de busca não comprova pertinência clínica."
                    continue
            task = next((t for t in run.plan.searches if t.connector == source.collection.lower()), None)
            terms = [term for term in re.findall(r"\w+", normalized(task.query if task else ""))
                     if len(term) > 2 and term not in {"and", "para", "sobre", "com", "dos", "das"}]
            content = normalized(source.abstract)
            if terms and not all(term in content for term in terms):
                source.selection_note = "Candidato mantido nas fontes, fora da síntese: os termos da consulta não aparecem todos no texto recuperado. A íntegra pode conter informação adicional."
                continue
            if terms:
                first_match = content.find(terms[0])
            source.selection_note = "Trecho com correspondência lexical; relevância semântica e qualidade não avaliadas."
        # Prefer explicit conclusions; otherwise expose an initial excerpt without interpreting it.
        match = re.search(r"\b(?:conclusions?|conclusões|conclusão)\s*[:.]?\s+", source.abstract, re.I) if source.content_kind == "abstract" else None
        start = match.end() if match else 0
        if source.content_kind == "institutional_text" and first_match is not None and first_match > 0:
            boundary = source.abstract.rfind(". ", 0, first_match)
            start = boundary + 2 if boundary >= 0 else 0
        end = min(len(source.abstract), start + 1600)
        if end < len(source.abstract):
            boundary = source.abstract.rfind(". ", start, end)
            if boundary > start:
                end = boundary + 1
        text = source.abstract[start:end]
        if text:
            if source.doi:
                seen_dois.add(source.doi.lower())
            limitation = {"abstract": "Somente abstract; avaliação metodológica pendente.",
                          "ementa": "Somente ementa oficial; íntegra e vigência independente não verificadas.",
                          "institutional_text": "Publicação institucional; não classificada automaticamente como diretriz ou estudo."}
            result.append(Evidence(source_id=source.id, supporting_excerpt=text, excerpt_start=start,
                                   excerpt_end=end, verification_status="excerpt_matched",
                                   extraction_method=f"{source.content_kind}-excerpt-v2",
                                   limitations=[limitation[source.content_kind]]))
    return result


async def execute(run: Run, store: Store, connector: EuropePMC, provider: SynthesisProvider):
    def record(stage: str, **detail):
        run.events.append(Event(stage=stage, detail=detail))
        store.save(run)

    try:
        run.status = "running"
        run.provider, run.model = provider.name, provider.model
        run.plan = plan_research(run.request)
        record("planning", plan=run.plan.model_dump(), pipeline_version=run.pipeline_version)
        run.coverage = [Coverage(**task.model_dump()) for task in run.plan.searches]
        national = BrazilSearch(connector.client)
        for coverage in run.coverage:
            if coverage.connector.endswith("_pending"):
                coverage.status = "not_integrated"
                coverage.message = "Não consultada automaticamente; use o link oficial para complementar a pesquisa."
                record("coverage_gap", **coverage.model_dump())
                continue
            coverage.status = "searching"
            record("search_started", query=coverage.query, limit_per_source=run.request.limit, source=coverage.label)
            try:
                if coverage.connector == "europe_pmc":
                    found, detail = await connector.search(coverage.query, run.request.limit)
                elif coverage.connector == "scielo_crossref":
                    found, detail = await SciELODeposits(connector.client).search(coverage.query, run.request.limit)
                else:
                    found, detail = await national.search(coverage.connector, coverage.query, run.request.limit, run.request.uf)
                run.sources.extend(s for s in found if s.id not in {r.id for r in run.sources})
                coverage.count = len(found)
                coverage.status = "success" if found else "empty"
                coverage.message = "Consulta concluída; cobertura limitada à primeira página."
                if coverage.connector == "scielo_crossref":
                    coverage.message = (f"{detail['candidate_count']} candidatos examinados; {len(found)} com correspondência lexical. "
                                        "Metadados via Crossref, sem consulta direta ao SciELO; resumos podem estar ausentes.")
                if detail.get("failed_documents") or detail.get("failed_queries"):
                    coverage.message += " Alguns documentos não puderam ser lidos; veja a rastreabilidade."
                record("search_completed", source=coverage.label, **detail)
            except Exception as exc:
                coverage.status = "blocked" if isinstance(exc, AccessBlocked) else "failed"
                coverage.message = str(exc) if isinstance(exc, ConnectorError) else "Fonte indisponível ou resposta não reconhecida."
                record("source_failed", source=coverage.label, status=coverage.status, message=coverage.message,
                       error_type=type(exc).__name__)
        attempted = [c for c in run.coverage if c.status != "not_integrated"]
        if attempted and all(c.status in {"failed", "blocked"} for c in attempted):
            raise ConnectorError("Nenhuma fonte consultada respondeu adequadamente. Veja a cobertura por fonte; não é ausência de evidência.")
        record("selection", selected_ids=[s.id for s in run.sources],
               rule="Primeira página de cada fonte, ordem retornada pela base; sem seleção metodológica ou garantia de cobertura.")
        for source in run.sources:
            if source.collection in {"MED", "PMC", "PPR", "AGR", "CBA", "CTX", "ETH", "HIR", "NBK", "PAT"}:
                record("identifier_check", **await connector.check_identifier(source))
        run.evidence = extract(run)
        record("extraction", evidence_ids=[e.id for e in run.evidence],
               source_links={e.id: e.source_id for e in run.evidence}, method="typed-excerpt-v2",
               selection_notes={s.id: s.selection_note for s in run.sources if s.selection_note})
        run.limitations = run.plan.limitations + [
            "Busca exploratória limitada por fonte; não é revisão sistemática nem levantamento normativo completo.",
            "Somente registros Europe PMC passam pela reconferência na mesma base; Crossref e documentos institucionais não têm verificação independente.",
            "Trecho literal conferido não significa suporte semântico ou validade clínica verificados.",
            "Risco de viés, tamanho amostral, GRADE, retratações e aplicabilidade ao Brasil não foram avaliados.",
            "Não houve busca ativa de evidência contrária; discordâncias ainda não avaliadas.",
            "Textos permanecem no idioma da fonte; não há tradução automática no modo extrativo.",
            "Origem institucional brasileira não comprova população brasileira. Notícias e anúncios de diretrizes não equivalem às próprias diretrizes.",
        ]
        if any(c.status in {"failed", "blocked", "not_integrated"} for c in run.coverage):
            run.limitations.append("Cobertura parcial: há fontes não consultadas, bloqueadas ou indisponíveis. Consulte o painel de cobertura.")
        if any(s.identifier_status != "matched" for s in run.sources):
            run.limitations.append("Há referências cuja identidade não foi reconfirmada; consulte o status de cada fonte.")
        if run.evidence:
            record("synthesis_started", provider=provider.name, model=provider.model)
            try:
                claims, provider_detail = await provider.synthesize(run)
                validate_links(run.model_copy(update={"claims": claims}))
                run.claims = claims
                record("synthesis", **provider_detail)
            except Exception as exc:
                record("provider_fallback", failed_provider=provider.name, error_type=type(exc).__name__)
                run.claims, provider_detail = await ExtractiveProvider().synthesize(run)
                run.provider, run.model = "extractive", None
                run.limitations.append("Provider falhou ou retornou saída inválida; utilizada síntese extrativa.")
                record("synthesis", **provider_detail)
            run.summary = (f"Foram recuperados {len(run.sources)} registros; {len(run.evidence)} possuem trechos selecionados. "
                           "Abaixo estão os achados textuais das fontes, sem graduação da força da evidência. "
                           "Esta busca inicial não permite estabelecer uma recomendação clínica.")
            if run.plan.intent == "regulation":
                run.summary = (f"Foram localizados {len(run.sources)} documentos nas fontes consultadas. "
                               "As ementas identificam normas para leitura, mas não respondem integralmente quais obrigações se aplicam ao caso. "
                               "Legislação federal, íntegra das normas e vigência independente ainda precisam ser verificadas.")
        else:
            run.summary = ("Não foram encontrados trechos utilizáveis nesta busca. Isso não demonstra ausência de evidência. "
                           "Revise os termos, as fontes e os critérios de seleção.")
        validate_links(run)
        record("verification", scope="Integridade dos vínculos e correspondência literal dos trechos",
               semantic_status="not_evaluated", claim_links={c.id: c.evidence_ids for c in run.claims})
        run.status = "completed"
        record("completed", source_count=len(run.sources), evidence_count=len(run.evidence), claim_count=len(run.claims))
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc) if isinstance(exc, ConnectorError) else "Não foi possível concluir a pesquisa. Tente novamente."
        record("failed", error_type=type(exc).__name__)
        logger.warning("Pesquisa %s falhou: %s", run.id, type(exc).__name__)
    return run
