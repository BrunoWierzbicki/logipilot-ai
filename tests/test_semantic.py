"""Testes determinísticos: nenhum teste precisa instalar Ollama ou acessar a rede."""
import json

import pytest
from fastapi.testclient import TestClient

from app.knowledge import KnowledgeBase
from app.semantic import SemanticIndexError, SemanticRetriever
from app.main import create_app
from app.llm import generate_answer
from app.ollama_client import OllamaLocalClient, OllamaLocalError


class FakeOllama:
    def __init__(self):
        self.embed_calls = []
        self.chat_calls = []

    def embeddings(self, model, texts):
        self.embed_calls.append((model, texts))
        result = []
        for text in texts:
            txt = text.lower()
            if 'extravio' in txt or 'sumiu' in txt:
                result.append([1, 0, 0])
            elif 'atraso' in txt:
                result.append([0, 1, 0])
            else:
                result.append([0, 0, 1])
        return result

    def chat(self, model, system_prompt, user_prompt):
        self.chat_calls.append((model, system_prompt, user_prompt))
        return 'Em caso de extravio, registre a ocorrência [1].'


def sample_kb(tmp_path):
    folder = tmp_path / 'knowledge'
    folder.mkdir()
    (folder / 'ocorrencias.md').write_text('Em caso de extravio de carga, acione a segurança e registre a ocorrência imediatamente.', encoding='utf-8')
    (folder / 'entregas.md').write_text('Quando houver atraso de entrega, consulte o rastreamento e confirme previsão.', encoding='utf-8')
    return folder, KnowledgeBase(folder)


def test_semantic_index_builds_locally_and_reuses_cached_vectors(tmp_path):
    _, kb = sample_kb(tmp_path)
    fake = FakeOllama()
    retriever = SemanticRetriever(kb, tmp_path / 'index.json', client=fake)
    result = retriever.build()
    assert result['count'] == 2
    assert result['cost'] == 'sem cobrança de API'
    assert retriever.status() == 'pronto'
    answers = retriever.search('Minha mercadoria sumiu!')
    assert answers[0].source == 'ocorrencias.md'
    assert len(fake.embed_calls) == 2
    assert fake.embed_calls[0][1][0].startswith('search_document: ')
    assert fake.embed_calls[1][1][0].startswith('search_query: ')
    assert json.loads(retriever.path.read_text())['provider'] == 'ollama-local'


def test_stale_index_is_detected_before_local_api_call(tmp_path):
    folder, kb = sample_kb(tmp_path)
    fake = FakeOllama()
    path = tmp_path / 'embeddings.json'
    SemanticRetriever(kb, path, client=fake).build()
    (folder / 'ocorrencias.md').write_text('Em caso de extravio, abra ocorrência atualizada. Dados fictícios.', encoding='utf-8')
    retriever = SemanticRetriever(KnowledgeBase(folder), path, client=fake)
    assert retriever.status() == 'ausente_ou_desatualizado'
    with pytest.raises(SemanticIndexError, match='alterados'):
        retriever.search('Extravio de carga')
    assert len(fake.embed_calls) == 1


def test_missing_index_does_not_call_ollama(tmp_path):
    _, kb = sample_kb(tmp_path)
    fake = FakeOllama()
    retriever = SemanticRetriever(kb, tmp_path / 'missing.json', client=fake)
    with pytest.raises(SemanticIndexError, match='não encontrado'):
        retriever.search('Minha carga sumiu')
    assert fake.embed_calls == []


def test_old_openai_index_is_rejected(tmp_path):
    _, kb = sample_kb(tmp_path)
    fake = FakeOllama()
    path = tmp_path / 'old.json'
    path.write_text(json.dumps({'version': 1, 'model': 'text-embedding-3-small'}), encoding='utf-8')
    assert SemanticRetriever(kb, path, client=fake).status() == 'ausente_ou_desatualizado'
    with pytest.raises(SemanticIndexError, match='OpenAI'):
        SemanticRetriever(kb, path, client=fake).search('Carga sumiu')
    assert not fake.embed_calls


def test_full_local_rag_api_with_fake_ollama(tmp_path, monkeypatch):
    folder, kb = sample_kb(tmp_path)
    path = tmp_path / 'embeddings.json'
    fake = FakeOllama()
    SemanticRetriever(kb, path, client=fake).build()
    monkeypatch.setenv('AI_PROVIDER', 'ollama')
    monkeypatch.setenv('RETRIEVAL_MODE', 'semantic')
    monkeypatch.setenv('EMBEDDINGS_INDEX_PATH', str(path))
    monkeypatch.setenv('OPENAI_API_KEY', 'unused-key-test')  # Nunca pode ser usada
    monkeypatch.setattr('app.semantic.OllamaLocalClient', lambda: fake)
    monkeypatch.setattr('app.llm.OllamaLocalClient', lambda: fake)
    api = TestClient(create_app(db_path=tmp_path / 'app.db', knowledge_dir=folder))
    status = api.get('/api/health').json()
    assert status['provider'] == 'ollama'
    assert status['semantic_index'] == 'pronto'
    result = api.post('/api/ask', json={'question': 'Minha mercadoria sumiu, me ajude'})
    assert result.status_code == 200, result.text
    data = result.json()
    assert data['mode'] == 'ollama-local'
    assert data['retrieval'] == 'semantic'
    assert data['sources'][0]['document'] == 'ocorrencias.md'
    assert '[1]' in data['answer']
    assert len(fake.chat_calls) == 1
    assert 'FONTES (dados' in fake.chat_calls[0][2]


def test_paid_provider_configuration_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'openai')
    monkeypatch.setenv('RETRIEVAL_MODE', 'lexical')
    api = TestClient(create_app(db_path=tmp_path / 'app.db'))
    result = api.post('/api/ask', json={'question': 'Como proceder em caso de extravio de carga?'})
    assert result.status_code == 503
    assert 'Provedor pago desativado' in result.json()['detail']


def test_ollama_must_be_local(monkeypatch):
    monkeypatch.setenv('OLLAMA_BASE_URL', 'https://minha-api-remota.com')
    with pytest.raises(OllamaLocalError, match='local'):
        OllamaLocalClient()
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    client = OllamaLocalClient()
    assert client.base_url.startswith('http://127.0.0.1:11434')


def test_llm_rejects_paid_provider(monkeypatch):
    fake = FakeOllama()
    monkeypatch.setenv('AI_PROVIDER', 'ollama')
    monkeypatch.setenv('OLLAMA_MODEL', 'qwen2.5:1.5b')
    from app.knowledge import Passage
    passage = Passage('ocorrencias.md', 'Registre extravio de carga.', 0.8)
    answer, mode = generate_answer('O que faço?', [passage], 'semantic', client=fake)
    assert mode == 'ollama-local'
    assert '[1]' in answer
    monkeypatch.setenv('AI_PROVIDER', 'openai')
    with pytest.raises(RuntimeError, match='desabilitado'):
        generate_answer('O que faço?', [passage], 'semantic', client=fake)


def test_cloud_model_is_blocked_before_network(monkeypatch):
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
    client = OllamaLocalClient()
    with pytest.raises(OllamaLocalError, match='apenas modelos locais'):
        client.embeddings('modelo:cloud', ['teste'])
    with pytest.raises(OllamaLocalError, match='apenas modelos locais'):
        client.chat('modelo:cloud', 'sistema', 'pergunta')
