import sqlite3
import pandas as pd
conn=sqlite3.connect('data/database/stockgpt.db')
df=pd.read_csv('data/scans/latest_scan.csv')
df.to_sql('daily_scans',conn,if_exists='append',index=False)
conn.close()
print('Scans stored')
