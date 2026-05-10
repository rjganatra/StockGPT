import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(layout="wide")

st.title("StockGPT Market Dashboard")

scan_file = Path("data/scans/latest_scan.csv")

if not scan_file.exists():

    st.warning("No scan data available yet.")
    st.stop()

df = pd.read_csv(scan_file)

# ======================
# MARKET OVERVIEW
# ======================

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
    "Closest to 52W Low",
    df.iloc[0]["symbol"]
)

col4.metric(
    "Average RSI",
    round(df["rsi"].mean(), 2)
)

# ======================
# HEATMAP TABLE
# ======================

st.header("Market Heatmap")

st.dataframe(
    df.sort_values("distance_pct")
)

# ======================
# TOP OPPORTUNITIES
# ======================

st.header("52W Low Opportunities")

top_low = df.sort_values("distance_pct").head(10)

st.dataframe(top_low)

# ======================
# SWING TRADE MODE
# ======================

st.header("Swing Trade Mode")

swing = df[
    (df["distance_pct"] < 15) &
    (df["rsi"] < 45)
]

st.dataframe(swing)

# ======================
# CHARTS
# ======================

st.header("Market Charts")

st.bar_chart(
    df.set_index("symbol")["distance_pct"].head(15)
)

st.line_chart(
    df.set_index("symbol")["rsi"].head(15)
)
