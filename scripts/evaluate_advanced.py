"""Avalia o recuperador híbrido e assunto com casos fictícios; não avalia LLM."""
import argparse
import json
from pathlib import Path

from dotenv import load_dotenv
from app.evaluation import evaluate_rag
from app.knowledge import KnowledgeBase
from app.semantic import SemanticRetriever

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser=argparse.ArgumentParser(description='Avaliação do RAG híbrido/assunto (LogiPilot 3.0)')
    parser.add_argument('--mode',choices=['lexical','semantic'],default='semantic')
    args=parser.parse_args()
    load_dotenv(ROOT/'.env')
    kb=KnowledgeBase(ROOT/'knowledge')
    retriever=SemanticRetriever(kb) if args.mode=='semantic' else kb
    dataset=json.loads((ROOT/'evaluation'/'qa_eval.json').read_text(encoding='utf-8'))
    result=evaluate_rag(dataset,kb,retriever)
    result['mode']=args.mode
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
