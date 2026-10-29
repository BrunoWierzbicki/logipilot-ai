"""Regras explícitas de automação (não são classificação por LLM)."""
import re
import unicodedata
from collections import Counter


def _normalize(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))


RULES = (
    ("CRITICA", ("acidente", "extravio", "roubo", "incendio", "carga desaparecida", "vazamento de dados")),
    ("ALTA", ("avaria", "bloqueio", "quebra", "veiculo parado", "entrega recusada", "carga danificada")),
    ("MEDIA", ("atraso", "demora", "falha", "reagendamento", "nao entregue")),
)


def classify_priority(description: str) -> str:
    content = _normalize(description)
    # Formas flexionadas frequentes são tratadas como risco crítico,
    # mesmo se o classificador LLM errar ou ficar indisponível.
    if re.search(r"\b(?:extraviad[ao]s?|roubad[ao]s?|furtad[ao]s?)\b", content):
        return "CRITICA"
    if re.search(r"\b(?:danificad[ao]s?|avariad[ao]s?)\b", content):
        return "ALTA"
    for priority, patterns in RULES:
        if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", content) for term in patterns):
            return priority
    return "BAIXA"


def summarize(incidents: list[dict]) -> dict:
    priorities = Counter(classify_priority(i["description"]) for i in incidents)
    return {
        "total": len(incidents),
        "por_prioridade": {level: priorities[level] for level in ("CRITICA", "ALTA", "MEDIA", "BAIXA")},
        "exigem_atencao": priorities["CRITICA"] + priorities["ALTA"],
    }
