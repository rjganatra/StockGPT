from pathlib import Path
from datetime import datetime
import shutil
today=datetime.now().strftime('%Y-%m-%d')
destination=Path(f'data/history/{today}')
destination.mkdir(parents=True,exist_ok=True)
shutil.copy('data/scans/latest_scan.csv',destination/'latest_scan.csv')
print('History saved')
