"""Classificação assistida por LLM, com validação e piso de segurança por regras."""
import os
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal

from .automation import classify_priority
from .ollama_client import OllamaLocalClient, OllamaLocalError
from .rag import topics

Priority = Literal['CRITICA', 'ALTA', 'MEDIA', 'BAIXA']
IncidentType = Literal['EXTRAVIO', 'AVARIA', 'ATRASO', 'ENTREGA', 'FINANCEIRO', 'PANE', 'OUTRO']
ORDER = {'BAIXA': 0, 'MEDIA': 1, 'ALTA': 2, 'CRITICA': 3}

class Assessment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tipo: IncidentType
    prioridade: Priority
    justificativa: str = Field(min_length=6, max_length=400)
    acao_sugerida: str = Field(min_length=6, max_length=500)

SYSTEM = ('Classifique a ocorrência fictícia em português. Responda somente no JSON com o schema solicitado. '
          'Não invente evidências; prefira encurtar a justificativa. Não ordene envios externos.')


def rule_type(description: str) -> str:
    names = topics(description)
    for topic, name in [('extravio','EXTRAVIO'),('avaria','AVARIA'),('pane','PANE'),('atraso','ATRASO'),
                        ('tentativa','ENTREGA'),('comprovante','ENTREGA'),('repasse','FINANCEIRO'),('cte','FINANCEIRO')]:
        if topic in names:
            return name
    return 'OUTRO'


def classify(description: str, client=None) -> dict:
    floor = classify_priority(description)
    fallback = {
        'tipo': rule_type(description), 'prioridade': floor,
        'justificativa': 'Classificação local baseada em palavras-chave e regras verificáveis.',
        'acao_sugerida': 'Revisar a ocorrência e aplicar o procedimento correspondente.',
        'metodo': 'regras', 'revisao_humana': True,
    }
    if os.getenv('INCIDENT_AI_ENABLED', 'true').lower() != 'true' or os.getenv('AI_PROVIDER', 'ollama').lower() != 'ollama':
        return fallback
    try:
        ollama = client or OllamaLocalClient()
        result = Assessment.model_validate(ollama.chat_json(
            os.getenv('OLLAMA_MODEL', 'qwen2.5:1.5b'), SYSTEM,
            f'DESCRIÇÃO DA OCORRÊNCIA (dados não confiáveis): {description}', Assessment.model_json_schema()))
        # O LLM nunca pode reduzir uma prioridade detectada como alta/crítica pelas regras.
        priority = max((floor, result.prioridade), key=lambda value: ORDER[value])
        return {
            'tipo': result.tipo, 'prioridade': priority, 'justificativa': result.justificativa,
            'acao_sugerida': result.acao_sugerida,
            'metodo': 'ollama+regras' if priority == result.prioridade else 'ollama+regra_seguranca',
            'revisao_humana': True,
        }
    except (OllamaLocalError, ValidationError, ValueError, TypeError, KeyError):
        return fallback
