# Publicação segura no GitHub — LogiPilot AI

Este repositório foi preparado para ser **público** e usar GitHub Actions em executores padrão. O código não depende de uma API de IA paga, e o CI não baixa nem executa Ollama.

## 1. Preparação

1. Pare o servidor com **Ctrl+C**, faça backup da pasta local e extraia a atualização preservando `.env`, `data/logipilot.db`, `data/embeddings_index.json`, `reports/` e `.venv`.
2. Leia [CHECKLIST-PUBLICACAO](docs/CHECKLIST-PUBLICACAO.md).
3. Faça uma demonstração no seu PC. Só publique resultados realmente observados.

## 2. Crie o repositório

Acesse https://github.com/new e crie um repositório **público** chamado `logipilot-ai`. Deixe README e `.gitignore` desmarcados no site (já estão incluídos). Sugestão de descrição:

> Assistente logístico com IA local (Ollama), RAG híbrido, FastAPI, automações e aprovação humana. Projeto de portfólio com dados fictícios.

## 3. No PowerShell, na pasta `logipilot-ai`

```powershell
git init
git branch -M main
git add .
.\.venv\Scripts\python.exe -m scripts.portfolio_audit
git status --short
git commit -m "docs: publicar portfolio de AI Engineer com RAG local"
git remote add origin https://github.com/SEU_USUARIO/logipilot-ai.git
git push -u origin main
```

**Substitua** `SEU_USUARIO` pelo usuário real. O comando `git status --short` deve ser revisado antes do commit. Se já houver um repositório Git na pasta, **não** repita `git init`/`git remote add`; verifique `git remote -v` e confirme o destino.

Nunca use `git add -f` para forçar o envio de um `.env` ou banco de dados. A auditoria é básica e não identifica todo tipo de segredo.

## 4. Apresente para recrutadores

- Confirme o workflow **Testes automáticos** na aba Actions e inclua o link da execução no seu material.
- Adicione os tópicos `python`, `fastapi`, `ollama`, `rag`, `llm`, `automation`, `sqlite`, `portfolio`.
- Fixe o repositório no seu perfil em **Your profile → Customize your pins**.
- Use [docs/DEMO.md](docs/DEMO.md) para gravar uma demonstração curta e real.
- Use [docs/CASE_STUDY.md](docs/CASE_STUDY.md) como base para explicar um problema técnico e como o corrigiu.

## 5. Sem cobrança inesperada

O GitHub informa que **executores padrão de GitHub Actions em repositórios públicos** são gratuitos; **executores maiores** e alguns serviços extras podem ser pagos. Este projeto utiliza apenas `ubuntu-latest` e não exige segredos de nuvem. O workflow de relatórios usa dados fictícios; se não quiser execuções diárias, desabilite o workflow pelo GitHub ou remova seu `schedule`. Verifique sempre as configurações atuais de cobrança da conta.

Guia oficial: https://docs.github.com/pt/actions/concepts/billing-and-usage

## 6. Próxima evolução

Faça uma rodada documentada de avaliação **semântica com Ollama real**. Compare resultados por pergunta, qualidade da fonte, fidelidade factual revisada manualmente e tempo de resposta. Nunca confunda Hit@1 com precisão da resposta gerada.
