
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="StockGPT", layout="wide")

st.title("📈 StockGPT Interactive Market Dashboard")

scan_file = Path("data/scans/latest_scan.csv")

if not scan_file.exists():
    st.warning("No scan data available yet.")
    st.stop()

df = pd.read_csv(scan_file)

st.sidebar.header("Filters")

max_distance = st.sidebar.slider(
    "Max Distance From 52W Low %",
    0,
    100,
    30
)

max_rsi = st.sidebar.slider(
    "Max RSI",
    0,
    100,
    50
)

selected_sector = "All"

if "sector" in df.columns:

    sectors = ["All"] + sorted(df["sector"].dropna().unique().tolist())

    selected_sector = st.sidebar.selectbox(
        "Sector",
        sectors
    )

filtered_df = df.copy()

filtered_df = filtered_df[
    filtered_df["distance_pct"] <= max_distance
]

filtered_df = filtered_df[
    filtered_df["rsi"] <= max_rsi
]

if selected_sector != "All":

    filtered_df = filtered_df[
        filtered_df["sector"] == selected_sector
    ]

st.header("📊 Market Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Stocks Scanned", len(df))
col2.metric("Avg RSI", round(df["rsi"].mean(), 2))
col3.metric("Near 52W Lows", len(df[df["distance_pct"] < 15]))
col4.metric("Bullish Stocks", len(df[df["trend"] == "Bullish"]))

st.header("🔥 Interactive Heatmap")

fig = px.treemap(
    filtered_df,
    path=["sector", "symbol"] if "sector" in filtered_df.columns else ["symbol"],
    values="current_price",
    color="distance_pct",
    hover_data=["rsi", "trend"]
)

st.plotly_chart(fig, use_container_width=True)

st.header("🎯 52W Low Opportunities")

top_df = filtered_df.sort_values("distance_pct").head(25)

st.dataframe(top_df, use_container_width=True)

st.header("⚡ Swing Trade Mode")

swing_df = filtered_df[
    (filtered_df["distance_pct"] < 20)
    &
    (filtered_df["rsi"] < 45)
]

st.dataframe(swing_df, use_container_width=True)

st.header("🧠 Reason Engine")

st.dataframe(
    filtered_df[["symbol", "reasons"]],
    use_container_width=True
)

if "sector" in filtered_df.columns:

    st.header("🏭 Sector Strength")

    sector_df = filtered_df.groupby(
        "sector"
    )["distance_pct"].mean().reset_index()

    sector_fig = px.bar(
        sector_df,
        x="sector",
        y="distance_pct"
    )

    st.plotly_chart(
        sector_fig,
        use_container_width=True
    )

st.header("⭐ Watchlist")

watchlist = [
    "RELIANCE",
    "INFY",
    "TCS",
    "HDFCBANK",
    "BEL",
    "HAL"
]

watch_df = filtered_df[
    filtered_df["symbol"].isin(watchlist)
]

st.dataframe(
    watch_df,
    use_container_width=True
)

st.header("📉 RSI Overview")

rsi_fig = px.line(
    filtered_df.head(20),
    x="symbol",
    y="rsi",
    markers=True
)

st.plotly_chart(
    rsi_fig,
    use_container_width=True
)

st.header("📉 Distance From 52W Low")

dist_fig = px.bar(
    filtered_df.head(20),
    x="symbol",
    y="distance_pct"
)

st.plotly_chart(
    dist_fig,
    use_container_width=True
)
