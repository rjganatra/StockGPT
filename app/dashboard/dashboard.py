import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
st.set_page_config(page_title='StockGPT',layout='wide')
st.title('📈 StockGPT Phase 4 Dashboard')
scan_file=Path('data/scans/latest_scan.csv')
if not scan_file.exists():
    st.warning('No scan data available yet.')
    st.stop()
df=pd.read_csv(scan_file)
max_distance=st.sidebar.slider('Max Distance %',0,100,30)
max_rsi=st.sidebar.slider('Max RSI',0,100,50)
filtered=df[(df['distance_pct']<=max_distance)&(df['rsi']<=max_rsi)]
col1,col2,col3,col4=st.columns(4)
col1.metric('Stocks',len(df))
col2.metric('Avg RSI',round(df['rsi'].mean(),2))
col3.metric('Near Lows',len(df[df['distance_pct']<15]))
col4.metric('Bullish',len(df[df['trend']=='Bullish']))
fig=px.treemap(filtered,path=['sector','symbol'],values='current_price',color='distance_pct',hover_data=['rsi','trend'])
st.plotly_chart(fig,use_container_width=True)
st.dataframe(filtered.sort_values('distance_pct').head(25),use_container_width=True)
sector_df=filtered.groupby('sector')['distance_pct'].mean().reset_index()
sector_fig=px.bar(sector_df,x='sector',y='distance_pct')
st.plotly_chart(sector_fig,use_container_width=True)
