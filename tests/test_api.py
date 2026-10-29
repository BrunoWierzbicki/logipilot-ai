from fastapi.testclient import TestClient
from app.main import create_app


def test_api_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "demo")
    monkeypatch.setenv("RETRIEVAL_MODE", "lexical")
    client = TestClient(create_app(db_path=tmp_path / "test.db"))
    assert client.get("/api/health").json()["status"] == "ok"
    r = client.post("/api/ask", json={"question": "Como resolver o atraso de entrega?"})
    assert r.status_code == 200
    assert r.json()["mode"] == "demo"
    assert r.json()["sources"]

    critical = client.post("/api/incidents", json={"description": "Extravio de carga em rota"})
    assert critical.status_code == 201
    assert critical.json()["priority"] == "CRITICA"
    assert critical.json()["alert_created"] is True

    normal = client.post("/api/incidents", json={"description": "Comprovante emitido para pedido"})
    assert normal.json()["priority"] == "BAIXA"
    assert len(client.get("/api/incidents").json()) == 2
    assert len(client.get("/api/alerts").json()) == 1
    assert client.get("/api/summary").json()["total_registrados"] == 2


def test_validation(tmp_path):
    client = TestClient(create_app(db_path=tmp_path / "test.db"))
    assert client.post("/api/ask", json={"question": "a"}).status_code == 422
    assert client.post("/api/incidents", json={"description": "x"}).status_code == 422


def test_paid_provider_configuration_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(create_app(db_path=tmp_path / "test.db"))
    result = client.post("/api/ask", json={"question": "O que fazer em caso de extravio de carga?"})
    assert result.status_code == 503
    assert "Provedor pago desativado" in result.json()["detail"]
