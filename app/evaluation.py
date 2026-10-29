"""Avaliação local de recuperação; não confundir com avaliação factual do LLM."""
import time
from .rag import rerank, passage_topics, hybrid_pool
from .knowledge import KnowledgeBase


def evaluate_rag(dataset: list[dict], kb: KnowledgeBase, retriever) -> dict:
    cases = []
    for item in dataset:
        started = time.perf_counter()
        candidates = hybrid_pool(item['question'], kb, retriever)
        docs = rerank(item['question'], candidates, kb, top_k=3)
        elapsed = int((time.perf_counter()-started)*1000)
        labels = [sorted(passage_topics(p)) for p in docs]
        expected_doc = item['expected_document']
        expected_topic = item.get('expected_topic')
        cases.append({
            'question': item['question'], 'expected_document': expected_doc,
            'expected_topic': expected_topic, 'top_1': docs[0].source if docs else None,
            'top_1_section': docs[0].section if docs else None,
            'hit_at_1': bool(docs and docs[0].source == expected_doc),
            'hit_at_3': any(p.source == expected_doc for p in docs),
            'topic_at_1': bool(docs and expected_topic in labels[0]) if expected_topic else None,
            'latency_ms': elapsed,
        })
    n = len(cases)
    topic_cases = [c for c in cases if c['topic_at_1'] is not None]
    return {
        'count':n,
        'hit_at_1': round(sum(c['hit_at_1'] for c in cases)/n,3) if n else None,
        'hit_at_3': round(sum(c['hit_at_3'] for c in cases)/n,3) if n else None,
        'topic_at_1':round(sum(c['topic_at_1'] for c in topic_cases)/len(topic_cases),3) if topic_cases else None,
        'avg_latency_ms': round(sum(c['latency_ms'] for c in cases)/n) if n else None,
        'cases': cases,
        'note': 'Conjunto pequeno e fictício. Mede recuperação/assunto, NÃO veracidade da resposta LLM ou qualidade de produção.',
    }
