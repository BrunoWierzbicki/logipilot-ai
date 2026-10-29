# Checklist antes de tornar o repositório público

- [ ] Executei os testes (`python -m pytest -q`) e conheço ao menos um teste por módulo.
- [ ] Testei **pessoalmente** RAG, classificação, relatórios e aprovação no Windows com o Ollama.
- [ ] Fiz um vídeo ou captura do meu ambiente e conferi que não expõe informações pessoais.
- [ ] Revisei README, arquitetura e estudo de caso; sei explicar TF-IDF, embeddings, reordenação e fallback.
- [ ] Conferi que não há `.env`, banco SQLite, índices locais, relatórios pessoais, credenciais ou dados de clientes no commit.
- [ ] Rodei `python -m scripts.portfolio_audit` e revisei as advertências.
- [ ] Configurei repositório **público** com descrição e tópicos relevantes.
- [ ] Confirmei que o workflow de testes passou no GitHub Actions sem Ollama.
- [ ] Fixei o projeto no meu perfil do GitHub, se desejar destacá-lo.

**Transparência para entrevistas:** diferencie o que foi implementado com auxílio de IA do que você revisou, executou e testou por conta própria. Não declare integração real com sistemas de transportadoras ou métricas de produção: o projeto é demonstrativo.
