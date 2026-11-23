from contextlib import closing,contextmanager
import json
from pathlib import Path
import secrets
import sqlite3

from app.archive.canonical import serialize
from app.problems import DocketError


class Docket:
    def __init__(self,path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as database:
            database.executescript('''
                CREATE TABLE IF NOT EXISTS settings(name TEXT PRIMARY KEY, value BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS dockets(id TEXT PRIMARY KEY, content TEXT NOT NULL);
            ''')
            database.execute("INSERT OR IGNORE INTO settings VALUES ('pseudonym_key', ?)",(secrets.token_bytes(32),))
            self.secret=database.execute("SELECT value FROM settings WHERE name='pseudonym_key'").fetchone()[0]

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.path,timeout=15)) as database,database:
            yield database

    def find(self,key):
        with self.connect() as database:
            row=database.execute('SELECT content FROM dockets WHERE id=?',(key,)).fetchone()
        return None if row is None else json.loads(row[0])

    def require(self,key):
        packet=self.find(key)
        if packet is None:
            raise DocketError('DOCKET_MISSING','清算留档不存在',404)
        return packet

    def publish(self,key,packet):
        content=serialize(packet)
        with self.connect() as db:
            inserted=db.execute('INSERT OR IGNORE INTO dockets VALUES (?,?)',(key,content)).rowcount==1
            original=db.execute('SELECT content FROM dockets WHERE id=?',(key,)).fetchone()[0]
        return json.loads(original),not inserted

    def amend(self,key,packet):
        """用补齐后的证据更正原留档，仍是一条记录。

        只有引用原编号的更正才会走到这里；同一更正重跑得到相同证据摘要时
        视为未变，不写库也不新增历史。比较与写入在同一条 UPDATE 内完成，
        两个并发更正不会互相覆盖成半份证据。返回 (留档, 是否复用)。
        """
        content=serialize(packet)
        digest_value=packet['manifest'].get('evidence_sha256')
        with self.connect() as db:
            changed=db.execute(
                "UPDATE dockets SET content=? WHERE id=?"
                " AND json_extract(content,'$.manifest.evidence_sha256') IS NOT ?",
                (content,key,digest_value)).rowcount==1
            row=db.execute('SELECT content FROM dockets WHERE id=?',(key,)).fetchone()
            if row is None:
                raise DocketError('DOCKET_MISSING','清算留档不存在',404)
        return json.loads(row[0]),not changed

    def manifests(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute(
                "SELECT json_extract(content,'$.manifest') FROM dockets ORDER BY rowid DESC LIMIT 100")]
