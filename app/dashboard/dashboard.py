import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    layout="wide"
)

st.title("StockGPT Market Dashboard")

scan_file = Path(
    "data/scans/latest_scan.csv"
)

if not scan_file.exists():

    st.warning(
        "No scan data available yet."
    )

    st.stop()

df = pd.read_csv(scan_file)

# =================================
# MARKET OVERVIEW
# =================================

st.header("Market Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Stocks Scanned",
    len(df)
)

col2.metric(
    "Avg Distance from Low",
    round(df["distance_pct"].mean(), 2)
)

col3.metric(
    "Closest To Low",
    df.iloc[0]["symbol"]
)

col4.metric(
    "Average RSI",
    round(df["rsi"].mean(), 2)
)

# =================================
# MARKET HEATMAP
# =================================

st.header("Market Heatmap")

st.dataframe(
    df,
    use_container_width=True
)

# =================================
# 52W LOW OPPORTUNITIES
# =================================

st.header("52W Low Opportunities")

low_df = df.sort_values(
    "distance_pct"
).head(15)

st.dataframe(
    low_df,
    use_container_width=True
)

# =================================
# SWING TRADE MODE
# =================================

st.header("Swing Trade Candidates")

swing = df[
    (df["distance_pct"] < 15)
    &
    (df["rsi"] < 45)
]

st.dataframe(
    swing,
    use_container_width=True
)

# =================================
# REASON ENGINE
# =================================

st.header("Reason Engine")

st.dataframe(
    df[[
        "symbol",
        "reasons"
    ]],
    use_container_width=True
)

# =================================
# CHARTS
# =================================

st.header("Distance From 52W Low")

chart_df = df.head(15)

st.bar_chart(
    chart_df.set_index(
        "symbol"
    )["distance_pct"]
)

st.header("RSI Overview")

st.line_chart(
    chart_df.set_index(
        "symbol"
    )["rsi"]
)
