"""Avaliação offline do recuperador por top-1 e recall@3 no conjunto pequeno."""
import argparse
import json
from pathlib import Path
from app.knowledge import KnowledgeBase

ROOT = Path(__file__).resolve().parent.parent


def evaluate(dataset: list[dict], kb: KnowledgeBase) -> dict:
    results = []
    for item in dataset:
        found = kb.search(item["question"], top_k=3)
        sources = [p.source for p in found]
        results.append({
            "question": item["question"],
            "expected_document": item["expected_document"],
            "retrieved_documents": sources,
            "hit_at_1": bool(sources and sources[0] == item["expected_document"]),
            "hit_at_3": item["expected_document"] in sources,
        })
    count = len(results)
    return {
        "count": count,
        "hit_at_1": round(sum(r["hit_at_1"] for r in results)/count, 3) if count else None,
        "recall_at_3": round(sum(r["hit_at_3"] for r in results)/count, 3) if count else None,
        "details": results,
        "note": "Conjunto pequeno e fictício; métricas não garantem desempenho em produção.",
    }


def main():
    parser = argparse.ArgumentParser(description="Avalia recuperação lexical ou semântica.")
    parser.add_argument("--mode", choices=("lexical", "semantic"), default="lexical")
    options = parser.parse_args()
    dataset = json.loads((ROOT / "evaluation" / "qa_eval.json").read_text(encoding="utf-8"))
    kb = KnowledgeBase(ROOT / "knowledge")
    if options.mode == "semantic":
        from dotenv import load_dotenv
        from app.semantic import SemanticRetriever
        load_dotenv(ROOT / ".env")
        retriever = SemanticRetriever(kb)
        print("Avaliação semântica com Ollama local: nenhuma cobrança por requisição.")
    else:
        retriever = kb
    result = evaluate(dataset, retriever)
    result["mode"] = options.mode
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
