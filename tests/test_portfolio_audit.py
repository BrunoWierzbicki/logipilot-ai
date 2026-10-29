from scripts.portfolio_audit import find_risks


def test_audit_catches_private_files():
    files = ['app/main.py', '.env', 'data/logipilot.db', 'data/embeddings_index.json', '.venv/lib/test.py']
    assert set(find_risks(files)) == set(files[1:])


def test_audit_allows_regular_files():
    assert find_risks(['README.md', 'app/main.py', 'knowledge/ocorrencias.md']) == []
