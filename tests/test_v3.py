"""Testes de regressão 3.0 sem acesso à rede e sem créditos de API."""
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.knowledge import KnowledgeBase, Passage
from app.rag import rerank, extractive_fallback
from app.llm import generate_answer_checked
from app.intelligence import classify
from app.storage import init_db, add_incident, list_rows, review_action, incident_summary
from app.evaluation import evaluate_rag
from app.main import create_app
from app.semantic import SemanticRetriever


class FakeOllamaV3:
    def embeddings(self, model, texts):
        vectors=[]
        for t in texts:
            t=t.casefold()
            vectors.append([1,0,0] if 'extravio' in t or 'sumiu' in t else [0,1,0] if 'avaria' in t else [0,0,1])
        return vectors

    def chat(self, model, system, prompt):
        if 'DADOS AGREGADOS' in prompt:
            return 'Síntese: incidentes fictícios. Priorize revisão humana.'
        return 'Em caso de extravio, acione a segurança [1].'

    def chat_json(self, model, system, prompt, schema):
        return {'tipo':'EXTRAVIO', 'prioridade':'BAIXA', 'justificativa':'Requer verificação logística imediata.',
                'acao_sugerida':'Consultar o time de segurança.'}


def test_rerank_prevents_avaria_when_extravio_is_requested():
    kb=KnowledgeBase(__import__('pathlib').Path(__file__).resolve().parent.parent/'knowledge')
    avaria=next(p for p in kb.passages if p.section == 'Avaria')
    extravio=next(p for p in kb.passages if 'Extravio' in p.section)
    candidates=[Passage(avaria.source,avaria.text,0.605,avaria.section),
                Passage(extravio.source,extravio.text,0.593,extravio.section)]
    results=rerank('Minha carga foi extraviada. O que faço?', candidates,kb)
    assert len(results)==1
    assert results[0].section == 'Extravio e roubo'


def test_rerank_handles_multi_topic_question():
    from pathlib import Path
    kb=KnowledgeBase(Path(__file__).resolve().parent.parent/'knowledge')
    assert len(rerank('Como lidar com avaria e extravio?', kb.search('avaria extravio',top_k=9,threshold=0),kb))>=2


def test_llm_offtopic_answer_falls_back(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','ollama')
    class Bad:
        def chat(self,*args):return 'Isole os volumes e preserve a embalagem [1].'
    p=[Passage('ocorrencias.md','Em extravio, avise a segurança.',0.8,'Extravio e roubo')]
    answer, mode, quality=generate_answer_checked('Minha mercadoria foi extraviada',p,client=Bad())
    assert mode == 'fallback-extrativo'
    assert quality == 'revisao_necessaria'
    assert '[1]' in answer


def test_llm_without_valid_citation_falls_back(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','ollama')
    class Uncited:
        def chat(self,*args):return 'Faça coisas que não estão documentadas.'
    answer, mode, quality=generate_answer_checked('Como lidar com extravio?', [Passage('ocorrencias.md','Avisar segurança.',.5)], client=Uncited())
    assert mode=='fallback-extrativo'


def test_rule_floor_and_llm_json_validation(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','ollama');monkeypatch.setenv('INCIDENT_AI_ENABLED','true')
    result=classify('Extravio de carga',client=FakeOllamaV3())
    assert result['prioridade']=='CRITICA' and result['metodo']=='ollama+regra_seguranca'
    class Broken:
        def chat_json(self,*args):return {'tipo':'LUNAR', 'prioridade':'IMPOSSIVEL'}
    fallback=classify('Extravio de carga',client=Broken())
    assert fallback['metodo']=='regras' and fallback['prioridade']=='CRITICA'


def test_old_sqlite_database_migrates_without_losing_incidents(tmp_path):
    db=tmp_path/'old.db'
    with sqlite3.connect(db) as connection:
        connection.executescript("""
        CREATE TABLE incidents(id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT NOT NULL,
        priority TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT (datetime('now')));
        CREATE TABLE alerts(id INTEGER PRIMARY KEY AUTOINCREMENT,incident_id INTEGER UNIQUE,
        message TEXT NOT NULL,created_at TEXT DEFAULT (datetime('now')));
        INSERT INTO incidents(description,priority) VALUES('Registro antigo','MEDIA');
        """)
    init_db(db)
    assert list_rows(db,'incidents')[0]['description']=='Registro antigo'
    assert 'incident_type' in list_rows(db,'incidents')[0]
    assert 'pendentes' in incident_summary(db)


def test_approval_only_once_and_no_automatic_webhook(tmp_path):
    db=tmp_path/'t.db';init_db(db)
    incident=add_incident(db,'Extravio de carga','CRITICA')
    actions=list_rows(db,'actions')
    assert len(actions)==1 and actions[0]['status']=='PENDENTE'
    a=review_action(db,actions[0]['id'],'approve')
    assert a['status']=='APROVADA'
    assert review_action(db,actions[0]['id'],'approve') is None


def test_retrieval_evaluation_reports_topic_metric(tmp_path):
    root=__import__('pathlib').Path(__file__).resolve().parent.parent
    kb=KnowledgeBase(root/'knowledge')
    result=evaluate_rag([{'question':'Uma carga foi extraviada','expected_document':'ocorrencias.md','expected_topic':'extravio'}],kb,kb)
    assert result['count']==1
    assert result['hit_at_1']==1
    assert result['topic_at_1']==1
    assert 'NÃO' in result['note']


def test_v3_api_dashboard_and_report(tmp_path,monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','ollama')
    monkeypatch.setenv('RETRIEVAL_MODE','lexical')
    monkeypatch.setenv('ALLOW_EXTERNAL_WEBHOOK','false')
    monkeypatch.setattr('app.intelligence.OllamaLocalClient', lambda:FakeOllamaV3())
    monkeypatch.setattr('app.llm.OllamaLocalClient',lambda:FakeOllamaV3())
    monkeypatch.setattr('app.reports_ai.OllamaLocalClient',lambda:FakeOllamaV3())
    api=TestClient(create_app(db_path=tmp_path/'api.db'))
    assert api.get('/api/health').json()['version']=='3.0.0'
    assert api.get('/api/actions').json()==[]
    r=api.post('/api/incidents',json={'description':'Extravio confirmado no centro de distribuição'})
    assert r.status_code==201 and r.json()['priority']=='CRITICA'
    assert r.json()['classification']['metodo']=='ollama+regra_seguranca'
    a=api.get('/api/actions').json()[0]
    assert a['status']=='PENDENTE'
    assert api.post(f"/api/actions/{a['id']}/approve").json()['delivery'].startswith('envio externo desativado')
    assert api.post(f"/api/actions/{a['id']}/approve").status_code==409
    result=api.post('/api/ask',json={'question':'O que fazer quando uma carga é extraviada?'}).json()
    assert result['quality']=='citacoes_presentes_nao_auditadas'
    assert result['sources'][0]['section']=='Extravio e roubo'
    assert api.get('/api/metrics').json()['questions']==1
    report=api.post('/api/reports/generate')
    assert report.status_code==200 and 'Relatório inteligente' in report.json()['report']
    assert (tmp_path.parent/'nothing').exists() is False
    eval_result=api.post('/api/evaluation/run')
    assert eval_result.status_code==200
    assert eval_result.json()['count']==6
    assert api.get('/api/evaluation/latest').json()['count']==6


def test_everything_local_without_paid_sdk():
    from pathlib import Path
    src=(Path(__file__).resolve().parent.parent/'app')
    for f in src.glob('*.py'):
        text=f.read_text(encoding='utf-8')
        assert 'import openai' not in text and 'api.openai.com' not in text


def test_flexed_risk_terms_are_not_downgraded():
    from app.automation import classify_priority
    assert classify_priority('Uma carga foi extraviada') == 'CRITICA'
    assert classify_priority('Mercadoria danificada durante entrega') == 'ALTA'
