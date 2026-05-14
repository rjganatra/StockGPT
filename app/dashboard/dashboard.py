
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title='StockGPT', layout='wide')

st.title('📈 StockGPT Market Terminal')

scan_file = Path('data/scans/latest_scan.csv')

if not scan_file.exists():

    st.warning('No scan data available')

    st.stop()

df = pd.read_csv(scan_file)

st.sidebar.header('Filters')

max_rsi = st.sidebar.slider(
    'Max RSI',
    0,
    100,
    50
)

max_distance = st.sidebar.slider(
    'Max Distance %',
    0,
    100,
    30
)

filtered = df[
    (df['rsi'] <= max_rsi)
    &
    (df['distance_pct'] <= max_distance)
]

st.header('📊 Market Breadth')

col1, col2, col3, col4 = st.columns(4)

col1.metric('Stocks', len(filtered))

col2.metric(
    'Bullish',
    len(filtered[
        filtered['trend'] == 'Bullish'
    ])
)

col3.metric(
    'Near Lows',
    len(filtered[
        filtered['distance_pct'] < 15
    ])
)

col4.metric(
    'Avg RSI',
    round(filtered['rsi'].mean(), 2)
)

st.header('🔥 Heatmap')

fig = px.treemap(
    filtered,
    path=['symbol'],
    values='score',
    color='distance_pct'
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.header('🎯 Top Opportunities')

st.dataframe(
    filtered.sort_values(
        'score',
        ascending=False
    ),
    use_container_width=True
)

st.header('📉 RSI Distribution')

rsi_fig = px.histogram(
    filtered,
    x='rsi'
)

st.plotly_chart(
    rsi_fig,
    use_container_width=True
)
