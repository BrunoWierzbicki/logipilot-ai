# Resultados verificáveis e como reproduzir

## Verificado no ambiente de preparação em 29/10/2026

**Ambiente:** Python 3.13.5, testes offline sem Ollama. Dados sintéticos com 6 perguntas e documentos fictícios.

| Verificação | Resultado | Comando |
| --- | --- | --- |
| Testes automatizados | **29 de 29 aprovados** | `python -m pytest -q` |
| Recuperação lexical/híbrida Hit@1 | **6 de 6** | `python -m scripts.evaluate_advanced --mode lexical` |
| Recuperação lexical/híbrida Hit@3 | **6 de 6** | Idem |
| Assunto correto na primeira posição | **6 de 6** | Idem |

O tempo de recuperação lexical medido nesse conjunto foi de **aproximadamente 1 ms por caso** neste ambiente específico. Esse número é uma observação local em um corpus minúsculo, não uma previsão de latência em produção.

### O que os indicadores significam

- **Hit@1:** o documento-alvo foi encontrado na primeira posição.
- **Hit@3:** o documento-alvo apareceu entre os três primeiros resultados.
- **Assunto@1:** o título/tipo da seção priorizada correspondeu ao esperado no caso de teste.

**Estes indicadores NÃO medem** veracidade do modelo, qualidade de linguagem, segurança, latência da geração de texto, uso de memória ou satisfação de usuários. As perguntas foram criadas para uma base pequena e conhecida: há risco de sobreajuste às heurísticas do domínio.

## Resultados pendentes de medição no seu PC

| Experimento | Estado | Como medir |
| --- | --- | --- |
| RAG semântico com Ollama real | Ainda não medido nesta etapa | `python -m scripts.evaluate_advanced --mode semantic` |
| Tempo da resposta gerada pelo Qwen | Ainda não medido nesta etapa | Consultar perguntas reais no painel e observar telemetria |
| Fidelidade factual das respostas | Não avaliado automaticamente | Revisão humana com gabarito e teste de afirmações |
| Robustez a prompt injection | Não validada | Criar casos adversariais antes de qualquer uso real |

## Reproduzir no Windows

Execute na pasta `logipilot-ai`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.evaluate_advanced --mode lexical
.\.venv\Scripts\python.exe -m scripts.evaluate_advanced --mode semantic
```

A última linha requer Ollama rodando e o índice local de embeddings atualizado. Guarde as saídas e a versão dos modelos se quiser publicar um benchmark reprodutível.
