"""Separate schema-v2 storage. Legacy configuration tables are never rewritten."""
import json,sqlite3,uuid
from pathlib import Path
from .config import EvaluationConfig
from .runner import recovered

DEFAULT=Path(__file__).resolve().parents[2]/'runs'/'evaluation.sqlite3'

class Store:
    def __init__(self,path=DEFAULT):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS configurations(id TEXT,version INTEGER,body TEXT,PRIMARY KEY(id,version));
                CREATE TABLE IF NOT EXISTS evaluations(id TEXT PRIMARY KEY,manifest TEXT NOT NULL,report TEXT NOT NULL);''')
    def save_config(self,c,ref=None):
        c.validate()
        with sqlite3.connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            ident=ref['id'] if ref else uuid.uuid4().hex
            latest=db.execute('SELECT max(version) FROM configurations WHERE id=?',(ident,)).fetchone()[0] or 0
            if ref and ref['version']!=latest:raise ValueError('A newer version exists; reload or save as new.')
            version=latest+1
            db.execute('INSERT INTO configurations VALUES (?,?,?)',(ident,version,json.dumps(c.to_dict())))
        return {'id':ident,'version':version}
    def configs(self):
        with sqlite3.connect(self.path) as db:return [(i,v,json.loads(b)['name']) for i,v,b in db.execute('SELECT * FROM configurations ORDER BY rowid DESC')]
    def load_config(self,ref):
        with sqlite3.connect(self.path) as db:row=db.execute('SELECT body FROM configurations WHERE id=? AND version=?',(ref['id'],ref['version'])).fetchone()
        if row is None:raise ValueError('Configuration version not found.')
        return EvaluationConfig.from_dict(json.loads(row[0]))
    def begin(self,run):
        with sqlite3.connect(self.path) as db:db.execute('INSERT INTO evaluations VALUES (?,?,?)',(run.id,json.dumps(run.manifest),json.dumps(run.report())))
    def checkpoint(self,run):
        with sqlite3.connect(self.path) as db:db.execute('UPDATE evaluations SET report=? WHERE id=?',(json.dumps(run.report()),run.id))
    def runs(self):
        with sqlite3.connect(self.path) as db:return [(i,json.loads(r)['state']) for i,r in db.execute('SELECT id,report FROM evaluations ORDER BY rowid DESC')]
    def load(self,ident):
        with sqlite3.connect(self.path) as db:row=db.execute('SELECT report FROM evaluations WHERE id=?',(ident,)).fetchone()
        if row is None:raise ValueError('Run not found.')
        return recovered(json.loads(row[0]))
