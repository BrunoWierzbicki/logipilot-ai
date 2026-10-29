## 3.1 — Preparação para portfólio GitHub (29/10/2026)

- Documentação de arquitetura, estudo de caso, demonstração e resultados verificáveis.
- Guia de publicação e checklist para evitar vazamento de dados.
- Script simples de auditoria Git para arquivos sensíveis e dois testes adicionais.
- Nenhuma alteração nos endpoints, modelos locais ou fluxo de inferência da versão 3.0.

# Histórico de versões

## 2.1.0 — 29/10/2026 — Gratuito, IA local com Ollama

- Removida dependência do SDK OpenAI e chamadas externas de IA.
- Novo cliente HTTP do Ollama com acesso limitado ao loopback local.
- Busca semântica local com `nomic-embed-text-v2-moe` (`/api/embed`).
- Respostas locais com `qwen2.5:1.5b` (`/api/chat`).
- Índice JSON versionado agora identifica `provider=ollama-local` e rejeita cache antigo.
- Suporte a modo de demonstração lexical, sem Ollama.
- Adicionado verificador de instalação e guia para atualização sem perder o banco SQLite.
- Preservadas automações por regras, painel, relatórios e API REST.
- Testes offline abrangem indexação, cache, integração simulada, configuração antiga e URLs locais.

## 2.0.0 — Versão anterior

- Integração experimental com embeddings e geração por API externa; substituída por Ollama local nesta edição.

## 1.0.0 — Versão inicial

- Dashboard, TF-IDF, ocorrências, SQLite, alertas e relatórios.

## 3.0.0 — RAG aprimorado + automações inteligentes (Ollama local)

- Reranking híbrido semântico/TF-IDF com classificação de assunto a partir das seções Markdown.
- Ajuste de sinônimos (ex.: `extraviada` → `extravio`) e filtro para não misturar rotinas de avaria e extravio.
- Citações numéricas e fallback extrativo quando o LLM omite referências ou mistura ações claramente incompatíveis.
- Classificação por Ollama em JSON estruturado, validada com Pydantic; limite de severidade imposto por regras e fallback determinístico.
- Persistência de propostas de ação para aprovação humana; nenhum webhook automático. Envio externo só com opt-in de URL HTTPS, flag explícita e aprovação.
- Relatórios Markdown com LLM local sob solicitação do usuário.
- Dashboard com avaliação de recuperação, latência e telemetria, usando dados fictícios de demonstração.
- Migrações aditivas de SQLite preservam dados do projeto 2.1.
