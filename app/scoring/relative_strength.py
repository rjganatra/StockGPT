import pandas as pd
import random
from pathlib import Path
scan=pd.read_csv('data/scans/latest_scan.csv')
scan['relative_strength']=[round(random.uniform(1,100),2) for _ in range(len(scan))]
scan=scan.sort_values('relative_strength',ascending=False)
Path('data/scoring').mkdir(parents=True, exist_ok=True)
scan.to_csv('data/scoring/relative_strength.csv',index=False)
print('RS Generated')
