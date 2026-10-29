"""Checa o Ollama local e se os modelos necessários foram baixados."""
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener

from dotenv import load_dotenv
from app.ollama_client import OllamaLocalError, ollama_base_url
from app.semantic import embedding_model

ROOT = Path(__file__).resolve().parent.parent


def main():
    load_dotenv(ROOT / '.env')
    base = ollama_base_url()
    try:
        opener = build_opener(ProxyHandler({}))
        with opener.open(base + '/api/tags', timeout=8) as resp:
            tags = json.load(resp)
    except (URLError, HTTPError, TimeoutError, OSError, ValueError) as exc:
        raise SystemExit('ERRO: Ollama não está acessível localmente. Abra o Ollama; teste `ollama list`.') from exc
    names = {item.get('name') for item in tags.get('models', [])}
    llm = os.getenv('OLLAMA_MODEL', 'qwen2.5:1.5b')
    emb = embedding_model()
    missing = [model for model in (llm, emb) if model not in names and f'{model}:latest' not in names]
    print('Servidor Ollama local: OK')
    print('Modelo de respostas:', llm)
    print('Modelo de embeddings:', emb)
    if missing:
        print('Modelos ainda não instalados:')
        for model in missing:
            print('  ollama pull', model)
        raise SystemExit(1)
    print('Todos os modelos necessários estão disponíveis localmente.')


if __name__ == '__main__':
    try:
        main()
    except OllamaLocalError as exc:
        raise SystemExit(f'ERRO: {exc}') from exc
