import pytest
from pydantic import ValidationError

from xpesquisa.models import Claim, Evidence, ResearchRequest, Run, Source, validate_links
from xpesquisa.pipeline import extract
from xpesquisa.planning import plan_research
from xpesquisa.storage import Store


def sample_run():
    run = Run(request=ResearchRequest(question="Pergunta sintética para teste"))
    run.sources = [Source(id="s", external_id="123", collection="MED", title="Synthetic", source_url="https://europepmc.org/article/MED/123", abstract="Conclusions Test only.", response_sha256="a"*64)]
    run.evidence = extract(run)
    run.claims = [Claim(text=e.supporting_excerpt, evidence_ids=[e.id], kind="excerpt") for e in run.evidence]
    return run


def test_links_and_schema_roundtrip():
    run = sample_run()
    validate_links(run)
    assert Run.model_validate_json(run.model_dump_json()) == run
    assert run.evidence[0].sample_size is None
    assert run.sources[0].country is None


def test_fabricated_citation_is_rejected():
    run = sample_run()
    run.claims[0].evidence_ids = ["made-up-reference"]
    with pytest.raises(ValueError, match="Citação inexistente"):
        validate_links(run)


def test_fabricated_excerpt_is_rejected():
    run = sample_run()
    run.evidence[0].supporting_excerpt = "An invented effect."
    with pytest.raises(ValueError, match="Trecho"):
        validate_links(run)


def test_changed_extractive_claim_is_rejected():
    run = sample_run()
    run.claims[0].text = "Fake conclusion"
    with pytest.raises(ValueError, match="alterou"):
        validate_links(run)


def test_orphan_evidence_is_rejected():
    run = sample_run()
    run.evidence[0].source_id = "missing"
    with pytest.raises(ValueError, match="fonte inexistente"):
        validate_links(run)


def test_duplicates_rejected():
    run = sample_run()
    run.sources.append(run.sources[0])
    with pytest.raises(ValueError, match="duplicados"):
        validate_links(run)


@pytest.mark.parametrize("body", [{"question":"        "}, {"question":"12345678", "limit": 21}, {"question":"12345678", "unexpected":True}])
def test_request_boundaries(body):
    with pytest.raises(ValidationError):
        ResearchRequest(**body)


def test_sample_size_must_be_positive():
    with pytest.raises(ValidationError):
        Evidence(source_id="s", supporting_excerpt="test", excerpt_start=0, excerpt_end=4, sample_size=-1)


def test_missing_abstract_and_mismatched_identity_excluded():
    run = sample_run()
    run.sources[0].identifier_status = "mismatch"
    assert extract(run) == []
    run.sources[0].identifier_status = "matched"
    run.sources[0].abstract = ""
    assert extract(run) == []


def test_planning_is_transparent():
    request = ResearchRequest(question="Qual a evidência sobre elastografia hepática para fibrose?")
    plan = plan_research(request)
    assert "SRC:MED" in plan.query and "fibrosis" in plan.query
    assert plan.population is None
    assert plan_research(ResearchRequest(question=request.question, query="user terms")).query == "user terms"
    assert "literal" in plan_research(ResearchRequest(question="Outra pergunta geral")).strategy


def test_store_persistence_and_recovery(tmp_path):
    path = tmp_path / "test.db"
    store = Store(path)
    run = sample_run()
    store.save(run)
    reopened = Store(path)
    assert reopened.get(run.id).sources == run.sources
    reopened.recover()
    assert reopened.get(run.id).status == "failed"
    assert reopened.get(run.id).events[-1].stage == "interrupted"
