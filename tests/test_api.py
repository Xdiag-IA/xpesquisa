from fastapi.testclient import TestClient

from xpesquisa.api import app


def test_local_skeleton():
    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        assert "XPesquisa" in client.get("/").text
