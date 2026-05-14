import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="StockGPT",
    layout="wide"
)

st.title("📈 StockGPT Market Terminal")

scan_file = Path(
    "data/scans/latest_scan.csv"
)

if not scan_file.exists():

    st.warning("No scan data available")

    st.stop()

df = pd.read_csv(scan_file)

# =========================
# REQUIRED COLUMNS SAFETY
# =========================

required_cols = [
    "symbol",
    "distance_pct",
    "rsi",
    "trend",
    "score"
]

for col in required_cols:

    if col not in df.columns:

        st.error(f"Missing column: {col}")

        st.stop()

# =========================
# CLEAN DATA
# =========================

df = df.dropna(
    subset=[
        "distance_pct",
        "rsi",
        "score"
    ]
)

# =========================
# SIDEBAR
# =========================

st.sidebar.header("Filters")

max_rsi = st.sidebar.slider(
    "Max RSI",
    0,
    100,
    50
)

max_distance = st.sidebar.slider(
    "Max Distance %",
    0,
    100,
    30
)

filtered = df[
    (df["rsi"] <= max_rsi)
    &
    (df["distance_pct"] <= max_distance)
]

# =========================
# EMPTY CHECK
# =========================

if filtered.empty:

    st.warning(
        "No stocks match current filters"
    )

    st.stop()

# =========================
# MARKET BREADTH
# =========================

st.header("📊 Market Breadth")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Stocks",
    len(filtered)
)

col2.metric(
    "Bullish",
    len(
        filtered[
            filtered["trend"] == "Bullish"
        ]
    )
)

col3.metric(
    "Near 52W Lows",
    len(
        filtered[
            filtered["distance_pct"] < 15
        ]
    )
)

col4.metric(
    "Avg RSI",
    round(filtered["rsi"].mean(), 2)
)

# =========================
# HEATMAP
# =========================

st.header("🔥 Heatmap")

try:

    fig = px.treemap(
        filtered,
        path=["symbol"],
        values="score",
        color="distance_pct"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

except Exception as e:

    st.error(
        f"Heatmap Error: {e}"
    )

# =========================
# TOP OPPORTUNITIES
# =========================

st.header("🎯 Top Opportunities")

st.dataframe(
    filtered.sort_values(
        "score",
        ascending=False
    ),
    use_container_width=True
)

# =========================
# RSI DISTRIBUTION
# =========================

st.header("📉 RSI Distribution")

try:

    rsi_fig = px.histogram(
        filtered,
        x="rsi"
    )

    st.plotly_chart(
        rsi_fig,
        use_container_width=True
    )

except Exception as e:

    st.error(
        f"RSI Chart Error: {e}"
    )

# =========================
# WATCHLIST
# =========================

st.header("⭐ Watchlist")

watchlist = [
    "RELIANCE",
    "INFY",
    "TCS",
    "HDFCBANK"
]

watch_df = filtered[
    filtered["symbol"].isin(
        watchlist
    )
]

st.dataframe(
    watch_df,
    use_container_width=True
)
