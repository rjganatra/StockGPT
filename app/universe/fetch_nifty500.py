import pandas as pd
from pathlib import Path
symbols=['RELIANCE','TCS','INFY','HDFCBANK','ICICIBANK','SBIN','LT','ITC','KOTAKBANK','AXISBANK','ASIANPAINT','BAJFINANCE','MARUTI','TITAN','ULTRACEMCO','NESTLEIND','WIPRO','ONGC','NTPC','POWERGRID','BEL','HAL','TRENT','DMART','PIDILITIND','SUNPHARMA','ADANIPORTS','ADANIENT','COALINDIA','TATASTEEL']
sector_map={'RELIANCE':'Energy','TCS':'IT','INFY':'IT','HDFCBANK':'Banking','ICICIBANK':'Banking','SBIN':'Banking','BEL':'Defence','HAL':'Defence'}
df=pd.DataFrame({'symbol':symbols})
df['sector']=df['symbol'].map(sector_map).fillna('Others')
Path('data/universe').mkdir(parents=True,exist_ok=True)
df.to_csv('data/universe/universe.csv',index=False)
print('Universe refreshed')
