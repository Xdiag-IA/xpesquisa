"""Dados inteiramente sintéticos, sem artigos ou alegações clínicas reais."""
import pytest


@pytest.fixture
def article():
    return {"id": "123", "source": "MED", "title": "Synthetic test study — not a real publication",
            "doi": "10.0000/synthetic-test", "firstPublicationDate": "2024-01-01",
            "abstractText": "<h4>Methods</h4>Synthetic test data. <h4>Conclusions</h4>Uncertainty remains in this synthetic example.",
            "pubTypeList": {"pubType": ["Journal Article"]}, "authorList": {"author": [{"fullName": "Synthetic Author"}]}}


@pytest.fixture
def payload(article):
    return {"version": "test", "hitCount": 1, "resultList": {"result": [article]}}
