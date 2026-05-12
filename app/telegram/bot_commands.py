import pandas as pd
scan=pd.read_csv('data/scans/latest_scan.csv')
print(scan[['symbol','distance_pct','rsi']].head(10))
