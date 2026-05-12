import pandas as pd
from pathlib import Path
scan=pd.read_csv('data/scans/latest_scan.csv')
sector=scan.groupby('sector').agg({'distance_pct':'mean','rsi':'mean'}).reset_index()
Path('data/sectors').mkdir(parents=True, exist_ok=True)
sector.to_csv('data/sectors/sector_rotation.csv',index=False)
print('Sector Rotation Generated')
