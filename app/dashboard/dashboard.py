
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="StockGPT", layout="wide")

st.title("StockGPT Market Intelligence Dashboard")

scan_file = Path("data/scans/latest_scan.csv")

if not scan_file.exists():
    st.warning("No scan data available yet.")
    st.stop()

df = pd.read_csv(scan_file)

st.header("Market Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Stocks Scanned", len(df))
col2.metric("Average RSI", round(df["rsi"].mean(), 2))
col3.metric("Near 52W Low", len(df[df["distance_pct"] < 15]))
col4.metric("Bullish Stocks", len(df[df["trend"] == "Bullish"]))

st.header("Market Heatmap")

st.dataframe(df, use_container_width=True)

st.header("52W Low Opportunities")

low_df = df.sort_values("distance_pct").head(20)

st.dataframe(low_df, use_container_width=True)

st.header("Swing Trade Mode")

swing = df[(df["distance_pct"] < 20) & (df["rsi"] < 45)]

st.dataframe(swing, use_container_width=True)

st.header("Reason Engine")

st.dataframe(
    df[["symbol", "reasons"]],
    use_container_width=True
)

if "sector" in df.columns:

    st.header("Sector Strength")

    sector_df = df.groupby("sector")["distance_pct"].mean().sort_values()

    st.bar_chart(sector_df)

st.header("Watchlist")

watchlist = ["RELIANCE","INFY","TCS","HDFCBANK","BEL","HAL"]

watch_df = df[df["symbol"].isin(watchlist)]

st.dataframe(watch_df, use_container_width=True)

st.header("Distance From 52W Low")

chart_df = df.head(20)

st.bar_chart(
    chart_df.set_index("symbol")["distance_pct"]
)

st.header("RSI Chart")

st.line_chart(
    chart_df.set_index("symbol")["rsi"]
)
