import pandas as pd
df=pd.read_csv('data/scans/latest_scan.csv')
print(df[['symbol','score','rsi']].head(10))
