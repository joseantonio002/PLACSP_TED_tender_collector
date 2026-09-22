import argparse
import json
from pathlib import Path
import sqlite3

p = argparse.ArgumentParser()
p.add_argument('database', type=Path)
p.add_argument('sql')
a = p.parse_args()
db = sqlite3.connect(f'file:{a.database.resolve()}?mode=ro', uri=True)
db.row_factory = sqlite3.Row
print(json.dumps([dict(r) for r in db.execute(a.sql)], ensure_ascii=False, indent=2))
