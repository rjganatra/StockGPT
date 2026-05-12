import pandas as pd
from pathlib import Path
import random
universe=pd.read_csv('data/universe/universe.csv')
results=[]
for symbol in universe['symbol']:
    roe=round(random.uniform(10,40),2)
    roce=round(random.uniform(10,35),2)
    debt=round(random.uniform(0,1),2)
    sales=round(random.uniform(5,30),2)
    eps=round(random.uniform(5,35),2)
    score=0
    if roe>15: score+=20
    if roce>15: score+=20
    if debt<0.5: score+=20
    if sales>10: score+=20
    if eps>10: score+=20
    results.append({'symbol':symbol,'roe':roe,'roce':roce,'debt_equity':debt,'sales_growth':sales,'eps_growth':eps,'fundamental_score':score})
Path('data/fundamentals').mkdir(parents=True, exist_ok=True)
pd.DataFrame(results).to_csv('data/fundamentals/fundamentals.csv',index=False)
print('Fundamentals Generated')
