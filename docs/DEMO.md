# Demonstração guiada (3–5 minutos)

## Preparação

Verifique que `ollama list` mostra `qwen2.5:1.5b` e `nomic-embed-text-v2-moe`, que o índice semântico está atualizado e que a API inicia em `http://127.0.0.1:8000`.

## Roteiro para apresentar em vídeo ou entrevista

1. **0:00 — Contexto.** "O LogiPilot é um protótipo educacional com procedimentos e ocorrências fictícias. Usei IA local para evitar custos de API."
2. **0:30 — Pergunta RAG.** Digite: `Uma carga foi extraviada durante o transporte. Qual o procedimento?` Mostre as fontes e explique como embeddings, TF-IDF e reordenação se combinam. **Confira a resposta antes de gravar**.
3. **1:20 — Casos de borda.** Pergunte algo sem cobertura na base: `Qual a previsão do tempo amanhã em Canoas?` Observe se o sistema admite insuficiência de fontes; se falhar, registre como limitação.
4. **2:00 — Ocorrências.** Registre `Carga extraviada durante o transporte`. Mostre classificação, severidade sugerida e eventual ação pendente.
5. **2:45 — Aprovação.** Demonstre aprovar/rejeitar uma ação; destaque que webhooks externos estão desligados por padrão.
6. **3:30 — Relatórios e métricas.** Gere um relatório local e execute a avaliação. Diferencie qualidade de recuperação de factualidade da resposta.
7. **4:15 — Qualidade.** Mostre `pytest -q`, a documentação `/docs`, os arquivos em `docs/` e o workflow de CI.

## Comandos úteis

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.evaluate_advanced --mode lexical
.\.venv\Scripts\python.exe -m scripts.evaluate_advanced --mode semantic
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

**Nota:** não publique como resultado real uma métrica ilustrativa da interface ou uma resposta ainda não conferida; grave a tela da sua execução.
