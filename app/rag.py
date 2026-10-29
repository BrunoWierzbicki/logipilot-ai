"""Recuperação híbrida com alinhamento de assunto e checagem conservadora.

Heurísticas de domínio são transparentes, testáveis e NÃO constituem um reranker
neural. O embedding continua gerado localmente pelo Ollama.
"""
import re
import unicodedata
from dataclasses import dataclass

from .knowledge import KnowledgeBase, Passage


def norm(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', s.casefold()) if not unicodedata.combining(c))

TOPIC_TERMS = {
    'extravio': ('extravio', 'extraviad', 'extraviou', 'extraviar', 'roubo', 'sumiu', 'desapareceu', 'desaparecida', 'furtad', 'perdid'),
    'avaria': ('avaria', 'danificad', 'quebrad', 'embalagem rasgad'),
    'atraso': ('atraso', 'atrasad', 'demora', 'prazo'),
    'tentativa': ('tentativa', 'destinatario ausente', 'reagendamento'),
    'comprovante': ('comprovante', 'recebimento'),
    'repasse': ('repasse', 'divergencia de valores', 'cobranca'),
    'cte': ('ct-e', 'conhecimento de transporte', 'documento fiscal'),
    'pane': ('pane mecanica', 'veiculo parado'),
    'privacidade': ('protecao de dados', 'dados pessoais', 'autorizados'),
}


def topics(text: str) -> set[str]:
    value = norm(text)
    found = set()
    for topic, terms in TOPIC_TERMS.items():
        if any(term in value for term in terms):
            found.add(topic)
    return found


def passage_topics(p: Passage) -> set[str]:
    # O título da seção tem precedência sobre palavras incidentais no trecho.
    return topics(p.section) or topics(p.text)


@dataclass(frozen=True)
class Ranked:
    passage: Passage
    combined: float


def hybrid_pool(question: str, kb: KnowledgeBase, primary) -> list[Passage]:
    """União (deduplicada) de recuperação principal com candidatos lexicais."""
    main = primary.search(question, top_k=max(3, len(kb.passages)))
    lexical = kb.search(question, top_k=max(3, len(kb.passages)))
    unique = {}
    for p in main + lexical:
        unique.setdefault((p.source, p.text), p)
    return list(unique.values())


def rerank(question: str, candidates: list[Passage], kb: KnowledgeBase, top_k: int = 3) -> list[Passage]:
    """Semântico + TF-IDF + seção; veta conflitos de categorias explícitas."""
    expected = topics(question)
    lexical = { (p.source, p.text): p.score for p in kb.search(question, top_k=len(kb.passages), threshold=0) }
    scored = []
    for p in candidates:
        labels = passage_topics(p)
        # Evita que procedimentos de avaria apareçam em perguntas só de extravio.
        if expected and labels and labels.isdisjoint(expected):
            continue
        lex = lexical.get((p.source, p.text), 0.0)
        bonus = 0.25 if expected and labels.intersection(expected) else 0.0
        score = 0.55 * max(p.score, 0) + 0.20 * lex + bonus
        scored.append(Ranked(p, score))
    scored.sort(key=lambda r: (-r.combined, -r.passage.score, r.passage.source))
    return [r.passage for r in scored[:top_k]]


def forbidden_offtopic(question: str, answer: str) -> bool:
    """Guarda-freio básico, não é prova de fidelidade factual."""
    question_topics = topics(question)
    # Confusão mais comum da base: o modelo inventa procedimento de avaria para extravio.
    if 'extravio' in question_topics and 'avaria' not in question_topics:
        body = norm(answer)
        return any(phrase in body for phrase in ('isolar os volumes', 'isole os volumes', 'preservar a embalagem', 'preserve a embalagem', 'registrar fotos da embalagem'))
    return False


def extractive_fallback(passages: list[Passage]) -> str:
    if not passages:
        return 'Não há informações suficientes na base de demonstração.'
    return ('Não consegui validar a resposta gerada; seguem os trechos recuperados, sem interpretação adicional:\n\n'
            + '\n\n'.join(f'[{i}] {p.text}' for i, p in enumerate(passages, 1)))


def has_valid_citation(text: str, source_count: int) -> bool:
    return any(f'[{i}]' in text for i in range(1, source_count + 1))
