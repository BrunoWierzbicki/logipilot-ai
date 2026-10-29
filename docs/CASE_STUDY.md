# Estudo de caso — Extravio x avaria em RAG

## Problema observado

Durante um teste do assistente, a pergunta sobre **extravio de carga** trouxe um trecho sobre **avaria** como primeira fonte, com similaridade de cosseno 0,605; o trecho diretamente relacionado a extravio veio em segundo (0,593). A resposta incorporou orientações de avaria, como preservar embalagens, inadequadas como instrução principal para um caso exclusivo de extravio.

**Lição:** uma pontuação alta de embedding não equivale à resposta correta. Fontes semelhantes podem tratar de processos operacionais distintos.

## Solução implementada na versão 3.0

- União de candidatos semânticos e lexicais.
- Reordenação que considera termos e assunto da seção, com regras explícitas para diferenciar extravio, avaria, atrasos e outros temas da base fictícia.
- Orientação para citar trechos recuperados; fallback extrativo se a checagem básica de citações falhar.
- Teste de regressão para formulários de pergunta com variações de termos, incluindo `extraviada`.

## Como reproduzir a verificação

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.evaluate_advanced --mode lexical
```

Em seguida, com Ollama local e índice válido:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_advanced --mode semantic
```

Abra o painel e repita a pergunta sobre extravio. Compare a **seção da primeira fonte** e a resposta, em vez de usar apenas a pontuação de similaridade.

## Resultado e limitações

Na avaliação lexical executada em 29/10/2026, as seis perguntas fictícias retornaram o **documento e assunto esperados na primeira posição**. Esse resultado não comprova que o LLM respondeu corretamente, e o conjunto é pequeno. O desempenho do Ollama semântico no computador do usuário deve ser medido separadamente.

**Próximos testes úteis:** múltiplos incidentes numa pergunta, linguagem informal, documentos contraditórios, texto com instruções maliciosas e informações ausentes.
