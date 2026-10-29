"""RAG semântico gratuito: embeddings locais via Ollama e índice JSON no disco."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

from .knowledge import KnowledgeBase, Passage
from .ollama_client import OllamaLocalClient, OllamaLocalError

DEFAULT_EMBEDDING_MODEL = 'nomic-embed-text-v2-moe'
DEFAULT_INDEX_PATH = Path(__file__).resolve().parent.parent / 'data' / 'embeddings_index.json'
INDEX_VERSION = 2


class SemanticIndexError(RuntimeError):
    """Índice incompatível, ausente ou com vetores inválidos."""


def embedding_model() -> str:
    return os.getenv('OLLAMA_EMBEDDING_MODEL', DEFAULT_EMBEDDING_MODEL).strip()


def index_path() -> Path:
    return Path(os.getenv('EMBEDDINGS_INDEX_PATH', str(DEFAULT_INDEX_PATH)))


def fingerprint(passages: list[Passage]) -> str:
    payload = [{'source': p.source, 'text': p.text} for p in passages]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _normalized(vector: list[float]) -> list[float]:
    try:
        nums = [float(x) for x in vector]
        magnitude = math.sqrt(sum(x*x for x in nums))
    except (ValueError, TypeError, OverflowError) as exc:
        raise SemanticIndexError('Embedding com valores inválidos.') from exc
    if not nums or not magnitude or not math.isfinite(magnitude) or any(not math.isfinite(x) for x in nums):
        raise SemanticIndexError('Embedding nulo ou não finito.')
    return [x/magnitude for x in nums]


def _vectors(vectors: list[list[float]], expected: int) -> list[list[float]]:
    if not isinstance(vectors, list) or len(vectors) != expected:
        raise SemanticIndexError('Quantidade inesperada de embeddings retornados pelo Ollama.')
    normalized = [_normalized(v) for v in vectors]
    if len({len(v) for v in normalized}) != 1:
        raise SemanticIndexError('Dimensões inconsistentes entre embeddings.')
    return normalized


class SemanticRetriever:
    def __init__(self, kb: KnowledgeBase, path: Path | None = None, model: str | None = None, client=None):
        self.kb = kb
        self.path = path if path is not None else index_path()
        self.model = model or embedding_model()
        self.client = client  # injeção de fake nos testes, nenhuma chamada externa

    def _client(self):
        return self.client if self.client is not None else OllamaLocalClient()

    def build(self) -> dict:
        """Indexa documentos usando Ollama LOCAL. Não usa chave nem serviço pago."""
        if not self.kb.passages:
            raise SemanticIndexError('Não há documentos Markdown para indexar.')
        # Prefixos recomendados para o modelo multilíngue Nomic Embed v2.
        texts = [f'search_document: {passage.text}' for passage in self.kb.passages]
        vectors = _vectors(self._client().embeddings(self.model, texts), len(texts))
        index = {
            'version': INDEX_VERSION, 'provider': 'ollama-local', 'model': self.model,
            'fingerprint': fingerprint(self.kb.passages), 'count': len(vectors),
            'dimensions': len(vectors[0]), 'vectors': vectors,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + '.tmp')
        tmp.write_text(json.dumps(index, ensure_ascii=False), encoding='utf-8')
        tmp.replace(self.path)
        return {'count': len(vectors), 'model': self.model, 'dimensions': len(vectors[0]), 'path': str(self.path), 'cost': 'sem cobrança de API'}

    def _load(self) -> dict:
        hint = 'Execute novamente: .\\.venv\\Scripts\\python.exe -m scripts.build_embeddings'
        if not self.path.exists():
            raise SemanticIndexError(f'Índice semântico não encontrado. {hint}')
        try:
            idx = json.loads(self.path.read_text(encoding='utf-8'))
        except (ValueError, OSError) as exc:
            raise SemanticIndexError(f'Índice ilegível ou corrompido. {hint}') from exc
        if not isinstance(idx, dict) or idx.get('provider') != 'ollama-local' or idx.get('version') != INDEX_VERSION or idx.get('model') != self.model:
            raise SemanticIndexError(f'Índice de outro provedor/modelo, inclusive versão antiga da OpenAI. {hint}')
        if idx.get('fingerprint') != fingerprint(self.kb.passages):
            raise SemanticIndexError(f'Os documentos foram alterados desde a indexação. {hint}')
        vectors = idx.get('vectors')
        dims = idx.get('dimensions')
        if (not isinstance(vectors, list) or len(vectors) != len(self.kb.passages)
            or not isinstance(dims, int) or dims <= 0
            or any(not isinstance(v, list) or len(v) != dims or any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in v) for v in vectors)):
            raise SemanticIndexError(f'Vetores do índice inválidos. {hint}')
        return idx

    def status(self) -> str:
        try:
            self._load()
        except SemanticIndexError:
            return 'ausente_ou_desatualizado'
        return 'pronto'

    def search(self, question: str, top_k: int = 3, min_score: float | None = None) -> list[Passage]:
        if not question.strip() or not self.kb.passages:
            return []
        idx = self._load()  # valida antes de chamar o modelo
        query = _vectors(self._client().embeddings(self.model, [f'search_query: {question}']), 1)[0]
        if len(query) != idx['dimensions']:
            raise SemanticIndexError('Dimensão do embedding diferente do índice. Refaça a indexação.')
        threshold = min_score if min_score is not None else float(os.getenv('SEMANTIC_MIN_SCORE', '0.2'))
        matches = []
        for i, vector in enumerate(idx['vectors']):
            similarity = sum(a * b for a, b in zip(query, vector))
            if similarity >= threshold:
                matches.append((i, similarity))
        matches.sort(key=lambda x: (-x[1], x[0]))
        return [Passage(self.kb.passages[i].source, self.kb.passages[i].text, round(score, 4), self.kb.passages[i].section) for i, score in matches[:top_k]]
