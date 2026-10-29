"""Auditoria local conservadora antes de publicar o portfólio no GitHub.

Não substitui revisão manual nem detecta todos os tipos de segredo.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    'README.md', '.gitignore', '.env.example', 'LICENSE',
    'docs/ARCHITECTURE.md', 'docs/RESULTADOS.md',
    '.github/workflows/ci.yml', 'tests/test_api.py',
]
BLOCKED_NAMES = {'.env', 'embeddings_index.json'}
BLOCKED_SUFFIXES = {'.db', '.sqlite3', '.p12', '.pem', '.key'}


def find_risks(files: list[str]):
    risks = []
    for name in files:
        p = Path(name)
        if p.name in BLOCKED_NAMES or p.suffix.lower() in BLOCKED_SUFFIXES or '.venv' in p.parts:
            risks.append(name)
    return risks


def main():
    missing = [name for name in REQUIRED if not (ROOT/name).is_file()]
    command = subprocess.run(['git','ls-files','--cached'],cwd=ROOT,text=True,capture_output=True,check=False)
    if command.returncode == 0:
        tracked = [line for line in command.stdout.splitlines() if line]
        print(f'Arquivos rastreados pelo Git: {len(tracked)}')
        risks = find_risks(tracked)
    else:
        print('Git ainda não inicializado: a auditoria de arquivos rastreados exige `git init` e `git add`.')
        risks = []
    for name in missing:
        print(f'FALTA: {name}')
    for name in risks:
        print(f'RISCO: arquivo sensível rastreado: {name}')
    if missing or risks:
        print('Falha: revise os itens listados antes do push.')
        return 1
    print('Verificações básicas concluídas. Revise manualmente o conteúdo e quaisquer segredos antes de publicar.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
