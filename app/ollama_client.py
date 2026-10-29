"""Cliente HTTP do Ollama *exclusivamente local*, sem SDK ou chave de API.

A URL é limitada ao loopback para prevenir chamadas externas acidentais.
Não usa os endpoints cloud do Ollama nem serviços de terceiros.
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener


class OllamaLocalError(RuntimeError):
    """Erro compreensível para quem executa o protótipo localmente."""


def ollama_base_url() -> str:
    raw = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').strip().rstrip('/')
    parts = urlparse(raw)
    if (parts.scheme != 'http' or parts.hostname not in {'127.0.0.1', 'localhost', '::1'}
            or parts.username or parts.password or parts.path or parts.query or parts.fragment):
        raise OllamaLocalError('OLLAMA_BASE_URL deve apontar apenas para Ollama local: http://127.0.0.1:11434')
    return raw


def _local_model(name: str) -> str:
    model = name.strip()
    if not model or 'cloud' in model.lower():
        raise OllamaLocalError('Utilize apenas modelos locais, sem modelos cloud:cloud.')
    return model


class OllamaLocalClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or ollama_base_url()
        parsed = urlparse(self.base_url)
        if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}:
            raise OllamaLocalError('Ollama deve usar uma URL de loopback local, nunca um servidor remoto.')
        # Não utilizar proxy de ambiente para o serviço local.
        self._opener = build_opener(ProxyHandler({}))

    def _post(self, endpoint: str, payload: dict, *, timeout: int) -> dict:
        request = Request(
            self.base_url + endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json'}, method='POST',
        )
        try:
            with self._opener.open(request, timeout=timeout) as response:
                result = json.load(response)
        except HTTPError as exc:
            detail = exc.read(600).decode('utf-8', errors='replace')
            if exc.code == 404:
                raise OllamaLocalError('Modelo não encontrado no Ollama. Confira os comandos ollama pull no README.') from exc
            raise OllamaLocalError(f'Ollama respondeu HTTP {exc.code}. Confira seus modelos e logs. {detail[:250]}') from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise OllamaLocalError('Ollama local indisponível ou demorou a responder. Abra o Ollama e confirme http://127.0.0.1:11434.') from exc
        except ValueError as exc:
            raise OllamaLocalError('Ollama retornou um JSON inválido.') from exc
        if not isinstance(result, dict) or result.get('error'):
            raise OllamaLocalError(f'Resposta inválida do Ollama: {str(result.get("error"))[:200] if isinstance(result, dict) else "formato inesperado"}')
        return result

    def embeddings(self, model: str, texts: list[str]) -> list[list[float]]:
        """API /api/embed. Recebe lista de textos e retorna os vetores na mesma ordem."""
        response = self._post('/api/embed', {'model': _local_model(model), 'input': texts}, timeout=120)
        vectors = response.get('embeddings')
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            raise OllamaLocalError('Ollama retornou quantidade inesperada de embeddings.')
        return vectors

    def chat(self, model: str, system_prompt: str, user_prompt: str) -> str:
        response = self._post('/api/chat', {
            'model': _local_model(model), 'stream': False,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'options': {'temperature': 0.1, 'num_predict': 500},
        }, timeout=180)
        content = response.get('message', {}).get('content')
        if not isinstance(content, str) or not content.strip():
            raise OllamaLocalError('Ollama não retornou texto de resposta.')
        return content.strip()

    def chat_json(self, model: str, system_prompt: str, user_prompt: str, schema: dict) -> dict:
        """Resposta estruturada seguindo o formato JSON Schema do Ollama local."""
        response = self._post('/api/chat', {
            'model': _local_model(model), 'stream': False, 'format': schema,
            'messages': [{'role': 'system', 'content': system_prompt},
                         {'role': 'user', 'content': user_prompt}],
            'options': {'temperature': 0, 'num_predict': 350},
        }, timeout=180)
        content = response.get('message', {}).get('content')
        try:
            parsed = json.loads(content)
        except (TypeError, ValueError) as exc:
            raise OllamaLocalError('Ollama não produziu JSON estruturado válido.') from exc
        if not isinstance(parsed, dict):
            raise OllamaLocalError('Classificação deve ser um objeto JSON.')
        return parsed
