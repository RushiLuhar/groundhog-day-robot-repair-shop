"""Local SQLite store: append-only configuration versions and immutable run snapshots."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone
from .config import ExperimentConfig

DEFAULT_DB=Path(__file__).resolve().parents[1]/'runs'/'experiments.sqlite3'

def now(): return datetime.now(timezone.utc).isoformat()

class ExperimentStore:
    def __init__(self,path=DEFAULT_DB):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS config_versions(
                config_id TEXT NOT NULL, version INTEGER NOT NULL, created_at TEXT NOT NULL,
                name TEXT NOT NULL, annotation TEXT NOT NULL, body TEXT NOT NULL,
                PRIMARY KEY(config_id,version));
            CREATE TABLE IF NOT EXISTS runs(
                run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                config_snapshot TEXT NOT NULL, task_snapshot TEXT NOT NULL,
                config_id TEXT, config_version INTEGER, status TEXT NOT NULL, report TEXT);
            PRAGMA user_version=1;
            ''')

    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=10)
        c.row_factory=sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        try:
            with c: yield c
        finally:
            c.close()

    def save_config(self,config,config_id=None,expected_version=None):
        config.validate()
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if config_id:
                latest=c.execute('SELECT MAX(version) FROM config_versions WHERE config_id=?',(config_id,)).fetchone()[0]
                if latest is None: raise ValueError('Saved configuration no longer exists.')
                if expected_version != latest: raise ValueError('A newer version exists. Reload it or save as a new configuration.')
                version=latest+1
            else: config_id=uuid.uuid4().hex; version=1
            c.execute('INSERT INTO config_versions VALUES (?,?,?,?,?,?)',
                (config_id,version,now(),config.name,config.annotation,json.dumps(config.to_dict())))
        return {'id':config_id,'version':version}

    def list_configs(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute('SELECT config_id,version,created_at,name,annotation FROM config_versions ORDER BY created_at DESC')]

    def load_config(self,config_id,version):
        with self.connect() as c:
            row=c.execute('SELECT body FROM config_versions WHERE config_id=? AND version=?',(config_id,version)).fetchone()
        if row is None: raise ValueError('Configuration version not found.')
        return ExperimentConfig.from_dict(json.loads(row['body']))

    def begin_run(self,run,reference=None):
        ref=reference or {}
        with self.connect() as c:
            c.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?)',
                (run.id,run.started_at,now(),json.dumps(run.experiment.to_dict()),json.dumps(run.suite.public_description()),
                 ref.get('id'),ref.get('version'),'running',None))

    def checkpoint(self,run,final=False):
        data=run.report()
        state=('error' if run.error else 'completed' if run.completed else 'stopped') if final else 'running'
        with self.connect() as c:
            c.execute('UPDATE runs SET updated_at=?,status=?,report=? WHERE run_id=?',(now(),state,json.dumps(data),run.id))

    def list_runs(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute('SELECT run_id,started_at,status,config_id,config_version FROM runs ORDER BY started_at DESC')]

    def load_run(self,run_id):
        with self.connect() as c:
            row=c.execute('SELECT * FROM runs WHERE run_id=?',(run_id,)).fetchone()
        if row is None: raise ValueError('Run not found.')
        d=dict(row)
        for key in ('config_snapshot','task_snapshot','report'):
            d[key]=json.loads(d[key]) if d[key] else None
        return d
