"""Cria os embeddings usando apenas Ollama instalado no próprio computador."""
import json
from pathlib import Path

from dotenv import load_dotenv
from app.knowledge import KnowledgeBase
from app.semantic import SemanticRetriever

ROOT = Path(__file__).resolve().parent.parent


def main():
    load_dotenv(ROOT / '.env')
    retriever = SemanticRetriever(KnowledgeBase(ROOT / 'knowledge'))
    print('Gerando embeddings localmente com Ollama. Sem cobrança por requisição.')
    print(json.dumps(retriever.build(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
