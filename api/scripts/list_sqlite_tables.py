import os
import sqlite3

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db = os.path.join(_root, "data", "iter.db")
con = sqlite3.connect(db)
rows = con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()
print([r[0] for r in rows])
con.close()
