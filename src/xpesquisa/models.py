"""Contratos do domínio; desconhecido é nulo, nunca uma estimativa implícita."""
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def now() -> datetime:
    return datetime.now(timezone.utc)


def uid() -> str:
    return str(uuid4())


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResearchRequest(Record):
    question: str = Field(min_length=8, max_length=2000)
    query: str | None = Field(default=None, max_length=1000)
    limit: int = Field(default=8, ge=1, le=20)
    scope: Literal["auto", "literature", "brazil", "regulation"] = "auto"
    uf: str | None = Field(default=None, pattern=r"^(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)$")

    @model_validator(mode="after")
    def trim(self):
        self.question = self.question.strip()
        self.query = self.query.strip() if self.query else None
        if len(self.question) < 8:
            raise ValueError("Escreva uma pergunta com pelo menos 8 caracteres.")
        return self


class SearchTask(Record):
    connector: str
    label: str
    query: str
    reason: str
    manual_url: str | None = None


class Coverage(Record):
    connector: str
    label: str
    query: str
    reason: str
    status: Literal["planned", "searching", "success", "empty", "failed", "blocked", "not_integrated"] = "planned"
    count: int = 0
    message: str = ""
    manual_url: str | None = None


class Plan(Record):
    interpretation: str
    query: str
    strategy: str
    population: str | None = None
    intervention: str | None = None
    comparator: str | None = None
    outcome: str | None = None
    limitations: list[str] = Field(default_factory=list)
    intent: Literal["literature", "regulation", "brazil"] = "literature"
    searches: list[SearchTask] = Field(default_factory=list)


class Source(Record):
    id: str
    title: str
    source: str = "Europe PMC"
    source_url: str
    external_id: str
    collection: str
    doi: str | None = None
    pmid: str | None = None
    authors: list[str] = Field(default_factory=list)
    publication_date: str | None = None
    study_types: list[str] = Field(default_factory=list)
    country: str | None = None
    abstract: str = ""
    license: str | None = None
    retrieval_date: datetime = Field(default_factory=now)
    response_sha256: str
    metadata_status: Literal["retrieved"] = "retrieved"
    identifier_status: Literal["not_checked", "matched", "mismatch", "unavailable"] = "not_checked"
    document_type: Literal["scientific_article", "regulation", "institutional"] = "scientific_article"
    content_kind: Literal["abstract", "ementa", "institutional_text"] = "abstract"
    institution_country: str | None = None
    jurisdiction: str | None = None
    regulatory_status: str | None = None
    retrieval_url: str | None = None
    related_urls: list[str] = Field(default_factory=list)
    selection_note: str | None = None


class Evidence(Record):
    id: str = Field(default_factory=uid)
    source_id: str
    supporting_excerpt: str = Field(min_length=1)
    excerpt_start: int = Field(ge=0)
    excerpt_end: int = Field(gt=0)
    population: str | None = None
    study_type: str | None = None
    sample_size: int | None = Field(default=None, gt=0)
    intervention: str | None = None
    comparator: str | None = None
    primary_outcome: str | None = None
    effect_size: str | None = None
    confidence_interval: str | None = None
    diagnostic_metrics: dict[str, float] = Field(default_factory=dict)
    risk_of_bias: str = "Não avaliado"
    confidence: str = "Não graduada"
    limitations: list[str] = Field(default_factory=lambda: ["Somente abstract; avaliação metodológica pendente."])
    applicability_brazil: str = "Não avaliada"
    verification_status: Literal["excerpt_matched", "not_verified"] = "not_verified"
    relation: Literal["supports", "contradicts", "context"] = "context"
    extraction_method: str = "abstract-excerpt-v1"


class Claim(Record):
    id: str = Field(default_factory=uid)
    text: str = Field(min_length=1, max_length=6000)
    evidence_ids: list[str] = Field(min_length=1)
    kind: Literal["excerpt", "draft"] = "excerpt"
    verification_status: Literal["excerpt_only", "not_verified"] = "not_verified"


class Event(Record):
    timestamp: datetime = Field(default_factory=now)
    stage: str
    detail: dict = Field(default_factory=dict)


class Run(Record):
    schema_version: str = "0.3.0"
    pipeline_version: str = "0.3.0"
    id: str = Field(default_factory=uid)
    request: ResearchRequest
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    plan: Plan | None = None
    sources: list[Source] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    summary: str = ""
    limitations: list[str] = Field(default_factory=list)
    provider: str = "extractive"
    model: str | None = None
    error: str | None = None
    coverage: list[Coverage] = Field(default_factory=list)


def validate_links(run: Run) -> None:
    sources = {s.id: s for s in run.sources}
    evidence = {e.id: e for e in run.evidence}
    if len(sources) != len(run.sources) or len(evidence) != len(run.evidence):
        raise ValueError("IDs duplicados no catálogo.")
    if len({c.id for c in run.claims}) != len(run.claims):
        raise ValueError("IDs duplicados nas afirmações.")
    for e in run.evidence:
        if e.source_id not in sources:
            raise ValueError("Evidência aponta para fonte inexistente.")
        abstract = sources[e.source_id].abstract
        if abstract[e.excerpt_start:e.excerpt_end] != e.supporting_excerpt:
            raise ValueError("Trecho não corresponde ao abstract recuperado.")
    for claim in run.claims:
        if any(ref not in evidence for ref in claim.evidence_ids):
            raise ValueError("Citação inexistente: afirmação rejeitada.")
        if claim.kind == "excerpt" and not any(
            claim.text == evidence[ref].supporting_excerpt for ref in claim.evidence_ids
        ):
            raise ValueError("Afirmação extrativa alterou o trecho original.")
