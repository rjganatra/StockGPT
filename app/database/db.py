import sqlite3
from pathlib import Path
Path('data/database').mkdir(parents=True, exist_ok=True)
conn=sqlite3.connect('data/database/stockgpt.db')
cur=conn.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS scans(symbol TEXT,sector TEXT,current_price REAL,distance_pct REAL,rsi REAL,trend TEXT)')
conn.commit()
conn.close()
print('DB Ready')
