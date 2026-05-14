import pandas as pd
df=pd.read_csv('data/fundamentals/fundamentals.csv')
df['conviction_score']=df['fundamental_score']
df.to_csv('data/fundamentals/fundamental_scores.csv',index=False)
print('Scores updated')
