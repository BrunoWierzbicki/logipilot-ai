"""API HTTP e dashboard de portfólio. Não requer API paga."""
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .knowledge import KnowledgeBase
from .llm import generate_answer_checked, provider_name
from .rag import rerank, hybrid_pool
from .intelligence import classify
from .evaluation import evaluate_rag
from .reports_ai import generate_report, persist_report
from .semantic import SemanticRetriever, SemanticIndexError, embedding_model
from .ollama_client import OllamaLocalError
from .storage import (add_incident, init_db, list_rows, incident_summary, review_action,
                      record_query, metrics, save_evaluation, latest_evaluation)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class IncidentRequest(BaseModel):
    description: str = Field(min_length=5, max_length=1500)


def approved_webhook(incident: dict) -> str:
    """Somente acionado após clique de aprovação; opt-in EXPLÍCITO no .env."""
    if os.getenv('ALLOW_EXTERNAL_WEBHOOK', 'false').lower() != 'true':
        return 'envio externo desativado (apenas aprovação local)'
    url = os.getenv('ALERT_WEBHOOK_URL','').strip()
    if not url:
        return 'sem webhook configurado (apenas aprovação local)'
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        return 'webhook inválido: somente HTTPS'
    data = json.dumps({'incident_id': incident['id'], 'priority':incident['priority'],
                       'description':incident['description']}, ensure_ascii=False).encode()
    try:
        with urlopen(Request(url, data=data, headers={'Content-Type':'application/json'},method='POST'), timeout=5) as r:
            r.read(100)
        return 'enviado após aprovação'
    except Exception:
        return 'falha no envio (aprovação registrada localmente)'


def create_app(db_path: Path | None = None, knowledge_dir: Path | None = None, semantic_client=None) -> FastAPI:
    db = db_path or Path(os.getenv('DB_PATH', str(ROOT / 'data' / 'logipilot.db')))
    kb = KnowledgeBase(knowledge_dir or ROOT / 'knowledge')
    semantic = SemanticRetriever(kb, client=semantic_client)
    init_db(db)
    api = FastAPI(title='LogiPilot AI', version='3.0.0', description='RAG reranqueado, classificação local por IA, revisões humanas, relatórios e avaliação.')

    @api.get('/')
    def index():
        return FileResponse(ROOT / 'app' / 'static' / 'index.html')

    @api.get('/api/health')
    def health():
        return {'status':'ok', 'version':'3.0.0','provider':provider_name(),
                'retrieval':os.getenv('RETRIEVAL_MODE','semantic').strip().lower(),
                'llm_model':os.getenv('OLLAMA_MODEL','qwen2.5:1.5b'),
                'privacy':'Ollama local; nenhum uso de API paga',
                'embedding_model':embedding_model(), 'semantic_index':semantic.status(),
                'documents':len(kb.passages)}

    @api.post('/api/ask')
    def ask(payload: AskRequest):
        started = time.perf_counter()
        retrieval = os.getenv('RETRIEVAL_MODE','semantic').strip().lower()
        try:
            if provider_name() not in {'ollama','demo'}:
                raise RuntimeError('Provedor pago desativado nesta edição. Altere AI_PROVIDER=ollama no .env.')
            if retrieval == 'semantic':
                candidates = hybrid_pool(payload.question, kb, semantic)
            elif retrieval == 'lexical':
                candidates = hybrid_pool(payload.question, kb, kb)
            else:
                raise SemanticIndexError('RETRIEVAL_MODE inválido; use semantic ou lexical.')
            passages = rerank(payload.question, candidates, kb, top_k=3)
            answer, mode, quality = generate_answer_checked(payload.question, passages, retrieval)
        except (RuntimeError, SemanticIndexError, OllamaLocalError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail='Modelo local não respondeu. Verifique o Ollama.') from exc
        elapsed = int((time.perf_counter()-started)*1000)
        record_query(db, retrieval, mode, elapsed, len(passages), quality)
        return {'answer':answer,'mode':mode,'quality':quality,'latency_ms':elapsed,
                'retrieval':retrieval,'sources':[{'id':i, 'document':p.source, 'section':p.section,
                'score':p.score,'score_kind':p.score_kind,'excerpt':p.text} for i,p in enumerate(passages,1)]}

    @api.post('/api/incidents',status_code=201)
    def create_incident(payload: IncidentRequest):
        assessed = classify(payload.description)
        incident = add_incident(db, payload.description.strip(), assessed['prioridade'], assessment=assessed)
        critical = assessed['prioridade'] in {'CRITICA','ALTA'}
        return {**incident, 'alert_created':critical,
                'classification':assessed, 'approval_required':critical,
                'webhook':'envio externo nunca é automático'}

    @api.get('/api/incidents')
    def get_incidents():
        return list_rows(db,'incidents')

    @api.get('/api/alerts')
    def get_alerts():
        return list_rows(db,'alerts')

    @api.get('/api/actions')
    def get_actions():
        return list_rows(db,'actions')

    @api.post('/api/actions/{action_id}/approve')
    def approve(action_id: int):
        reviewed = review_action(db, action_id, 'approve')
        if not reviewed:
            raise HTTPException(409, 'Ação inexistente ou já revisada')
        incident = next((i for i in list_rows(db,'incidents') if i['id']==reviewed['incident_id']), None)
        delivery = approved_webhook(incident) if incident else 'ocorrência não encontrada'
        return {**reviewed,'delivery':delivery}

    @api.post('/api/actions/{action_id}/reject')
    def reject(action_id: int):
        reviewed = review_action(db, action_id, 'reject')
        if not reviewed:
            raise HTTPException(409,'Ação inexistente ou já revisada')
        return {**reviewed,'delivery':'nenhum envio realizado'}

    @api.get('/api/summary')
    def get_summary():
        return incident_summary(db)

    @api.get('/api/metrics')
    def get_metrics():
        return metrics(db)

    @api.post('/api/reports/generate')
    def generate_ai_report():
        try:
            report = generate_report(incident_summary(db),list_rows(db,'incidents'))
        except (OllamaLocalError,RuntimeError) as exc:
            raise HTTPException(503,str(exc)) from exc
        filename = persist_report(ROOT/'reports',report)
        return {'report':report,'file':filename,'model':os.getenv('OLLAMA_MODEL','qwen2.5:1.5b') if provider_name()=='ollama' else 'demo'}

    @api.get('/api/evaluation/latest')
    def last_eval():
        return latest_evaluation(db)

    @api.post('/api/evaluation/run')
    def run_eval():
        dataset = json.loads((ROOT/'evaluation'/'qa_eval.json').read_text(encoding='utf-8'))
        mode = os.getenv('RETRIEVAL_MODE','semantic').lower()
        retriever = semantic if mode == 'semantic' else kb
        try:
            result = evaluate_rag(dataset,kb,retriever)
        except (OllamaLocalError,SemanticIndexError) as exc:
            raise HTTPException(503,str(exc)) from exc
        result['mode'] = mode
        save_evaluation(db,result)
        return result

    return api


app = create_app()
