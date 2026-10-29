from pathlib import Path
from app.automation import classify_priority, summarize
from app.knowledge import KnowledgeBase
from scripts.daily_report import render_report

ROOT = Path(__file__).resolve().parent.parent


def test_classification():
    assert classify_priority("Extravio de carga em transporte") == "CRITICA"
    assert classify_priority("Houve AVARIA na embalagem") == "ALTA"
    assert classify_priority("Entrega com atraso") == "MEDIA"
    assert classify_priority("Comprovante disponível") == "BAIXA"


def test_retrieval():
    kb = KnowledgeBase(ROOT / "knowledge")
    passages = kb.search("Qual o procedimento em caso de extravio de carga?")
    assert passages
    assert passages[0].source == "ocorrencias.md"
    assert "extravio" in passages[0].text.lower()


def test_empty_retrieval():
    kb = KnowledgeBase(ROOT / "knowledge")
    assert kb.search("") == []


def test_summary():
    data = [{"description": "Roubo de carga"}, {"description": "Entrega com atraso"}]
    assert summarize(data)["exigem_atencao"] == 1


def test_report():
    result = render_report([{"description": "Roubo de carga"}], "2026-10-29")
    assert "CRITICA" in result and "2026-10-29" in result


def test_evaluation():
    from scripts.evaluate_retrieval import evaluate
    dataset = [{"question": "O que fazer em caso de extravio de carga?", "expected_document": "ocorrencias.md"}]
    result = evaluate(dataset, KnowledgeBase(ROOT / "knowledge"))
    assert result["count"] == 1
    assert result["hit_at_1"] == 1.0
