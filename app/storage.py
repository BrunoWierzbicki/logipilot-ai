"""SQLite com migração aditiva para preservar ocorrências da edição 2.1."""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    return connection


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL, priority TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER NOT NULL UNIQUE,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(incident_id) REFERENCES incidents(id)
        );
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER NOT NULL UNIQUE,
            kind TEXT NOT NULL DEFAULT 'notificacao',
            status TEXT NOT NULL DEFAULT 'PENDENTE',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            reviewed_at TEXT, FOREIGN KEY(incident_id) REFERENCES incidents(id)
        );
        CREATE TABLE IF NOT EXISTS query_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            retrieval TEXT NOT NULL, mode TEXT NOT NULL,
            latency_ms INTEGER NOT NULL,
            source_count INTEGER NOT NULL,
            quality TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS evaluation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, details_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        ''')
        columns = {row['name'] for row in db.execute('PRAGMA table_info(incidents)')}
        for name in ('incident_type', 'analysis_method', 'reason', 'suggested_action'):
            if name not in columns:
                db.execute(f'ALTER TABLE incidents ADD COLUMN {name} TEXT')


def add_incident(db_path: Path, description: str, priority: str, *, assessment: dict | None = None) -> dict:
    assessment = assessment or {}
    with connect(db_path) as db:
        cur = db.execute('''INSERT INTO incidents(description,priority,incident_type,analysis_method,reason,suggested_action)
            VALUES (?,?,?,?,?,?)''', (description, priority, assessment.get('tipo'), assessment.get('metodo'),
                                      assessment.get('justificativa'), assessment.get('acao_sugerida')))
        incident_id = cur.lastrowid
        if priority in {'CRITICA', 'ALTA'}:
            db.execute('INSERT INTO alerts(incident_id,message) VALUES (?,?)',
                       (incident_id, f'Ocorrência #{incident_id} requer atenção: {priority}'))
            db.execute('INSERT INTO actions(incident_id,kind,status) VALUES (?,?,?)',
                       (incident_id, 'notificacao', 'PENDENTE'))
        return dict(db.execute('SELECT * FROM incidents WHERE id=?', (incident_id,)).fetchone())


def list_rows(db_path: Path, table: str) -> list[dict]:
    if table not in {'incidents','alerts','actions'}:
        raise ValueError('Tabela não autorizada')
    with connect(db_path) as db:
        if table == 'actions':
            sql = '''SELECT actions.*, incidents.description, incidents.priority FROM actions
                     JOIN incidents ON incidents.id=actions.incident_id
                     ORDER BY actions.id DESC LIMIT 100'''
        else:
            sql = f'SELECT * FROM {table} ORDER BY id DESC LIMIT 100'
        return [dict(row) for row in db.execute(sql)]


def review_action(db_path: Path, action_id: int, decision: str) -> dict | None:
    status = {'approve':'APROVADA', 'reject':'REJEITADA'}.get(decision)
    if status is None:
        raise ValueError('Decisão inválida')
    with connect(db_path) as db:
        cur = db.execute('''UPDATE actions SET status=?, reviewed_at=datetime('now')
             WHERE id=? AND status='PENDENTE' ''', (status, action_id))
        if not cur.rowcount:
            return None
        row = db.execute('SELECT * FROM actions WHERE id=?', (action_id,)).fetchone()
        return dict(row)


def incident_summary(db_path: Path) -> dict:
    with connect(db_path) as db:
        total = db.execute('SELECT COUNT(*) FROM incidents').fetchone()[0]
        alerts = db.execute('SELECT COUNT(*) FROM alerts').fetchone()[0]
        priorities = db.execute('SELECT priority, COUNT(*) AS qty FROM incidents GROUP BY priority').fetchall()
        pending = db.execute("SELECT COUNT(*) FROM actions WHERE status='PENDENTE'").fetchone()[0]
    return {'total_registrados':total,'alertas':alerts,'pendentes':pending,
            'por_prioridade': {row['priority']:row['qty'] for row in priorities}}


def record_query(db_path: Path, retrieval: str, mode: str, latency_ms: int, source_count: int, quality: str) -> None:
    with connect(db_path) as db:
        db.execute('INSERT INTO query_metrics(retrieval,mode,latency_ms,source_count,quality) VALUES (?,?,?,?,?)',
                   (retrieval,mode,latency_ms,source_count,quality))


def metrics(db_path: Path) -> dict:
    with connect(db_path) as db:
        row = db.execute('''SELECT COUNT(*) AS questions,
          COALESCE(ROUND(AVG(latency_ms)),0) AS avg_latency_ms,
          COALESCE(SUM(CASE WHEN quality='revisao_necessaria' THEN 1 ELSE 0 END),0) AS fallbacks
          FROM query_metrics''').fetchone()
    return dict(row)


def save_evaluation(db_path: Path, data: dict) -> None:
    with connect(db_path) as db:
        db.execute('INSERT INTO evaluation_runs(details_json) VALUES (?)', (json.dumps(data,ensure_ascii=False),))


def latest_evaluation(db_path: Path) -> dict | None:
    with connect(db_path) as db:
        row = db.execute('SELECT * FROM evaluation_runs ORDER BY id DESC LIMIT 1').fetchone()
    if row is None:
        return None
    return {'id': row['id'], 'created_at': row['created_at'], **json.loads(row['details_json'])}
