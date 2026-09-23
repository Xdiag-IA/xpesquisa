import logging
import re

from .connectors import ConnectorError, EuropePMC
from .models import Event, Evidence, Run, validate_links
from .planning import plan_research
from .providers import ExtractiveProvider, SynthesisProvider
from .storage import Store

logger = logging.getLogger(__name__)


def extract(run: Run) -> list[Evidence]:
    result = []
    for source in run.sources:
        if not source.abstract or source.identifier_status == "mismatch":
            continue
        # Prefer explicit conclusions; otherwise expose an initial excerpt without interpreting it.
        match = re.search(r"\b(?:conclusions?|conclusões|conclusão)\s*[:.]?\s+", source.abstract, re.I)
        start = match.end() if match else 0
        end = min(len(source.abstract), start + 1600)
        if end < len(source.abstract):
            boundary = source.abstract.rfind(". ", start, end)
            if boundary > start:
                end = boundary + 1
        text = source.abstract[start:end]
        if text:
            result.append(Evidence(source_id=source.id, supporting_excerpt=text, excerpt_start=start,
                                   excerpt_end=end, verification_status="excerpt_matched"))
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
        record("search_started", query=run.plan.query, limit=run.request.limit, source="Europe PMC")
        run.sources, detail = await connector.search(run.plan.query, run.request.limit)
        record("search_completed", **detail)
        record("selection", selected_ids=[s.id for s in run.sources],
               rule="Primeira página, relevância da fonte; sem seleção metodológica ou garantia de cobertura.")
        for source in run.sources:
            record("identifier_check", **await connector.check_identifier(source))
        run.evidence = extract(run)
        record("extraction", evidence_ids=[e.id for e in run.evidence],
               source_links={e.id: e.source_id for e in run.evidence}, method="abstract-excerpt-v1")
        run.limitations = run.plan.limitations + [
            "Busca exploratória limitada a uma página do Europe PMC; não é revisão sistemática.",
            "A conferência de identificadores utiliza a mesma base, não uma validação independente no Crossref/PubMed.",
            "Trecho literal conferido não significa suporte semântico ou validade clínica verificados.",
            "Risco de viés, tamanho amostral, GRADE, retratações e aplicabilidade ao Brasil não foram avaliados.",
            "Não houve busca ativa de evidência contrária; discordâncias ainda não avaliadas.",
            "Textos permanecem no idioma da fonte; não há tradução automática no modo extrativo.",
        ]
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
