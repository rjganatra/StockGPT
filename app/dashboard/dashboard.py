import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="StockGPT", layout="wide")

st.title("📈 StockGPT Market Intelligence Terminal")

scan_file = Path("data/scans/latest_scan.csv")

if not scan_file.exists():
    st.warning("No scan data available yet.")
    st.stop()

df = pd.read_csv(scan_file)

required_cols = [
    "symbol", "sector", "current_price", "day_change_pct",
    "distance_pct", "distance_from_high_pct",
    "rsi", "volume_ratio", "trend", "score", "reasons"
]

missing = [col for col in required_cols if col not in df.columns]

if missing:
    st.error(f"Missing columns in latest_scan.csv: {missing}")
    st.stop()

df = df.dropna(subset=["distance_pct", "rsi", "score"])

# Sidebar filters
st.sidebar.header("Filters")

sector_options = ["All"] + sorted(df["sector"].dropna().unique().tolist())

selected_sector = st.sidebar.selectbox("Sector", sector_options)

max_distance = st.sidebar.slider("Max Distance From 52W Low %", 0, 100, 30)
max_rsi = st.sidebar.slider("Max RSI", 0, 100, 60)
min_score = st.sidebar.slider("Minimum Score", 0, 100, 0)

filtered = df.copy()

filtered = filtered[
    (filtered["distance_pct"] <= max_distance)
    &
    (filtered["rsi"] <= max_rsi)
    &
    (filtered["score"] >= min_score)
]

if selected_sector != "All":
    filtered = filtered[filtered["sector"] == selected_sector]

if filtered.empty:
    st.warning("No stocks match the selected filters.")
    st.stop()

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Market Overview",
    "Heatmap",
    "Opportunities",
    "Sectors",
    "Stock Explorer",
    "History"
])

with tab1:
    st.header("📊 Market Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Stocks Scanned", len(df))
    col2.metric("Filtered Stocks", len(filtered))
    col3.metric("Near 52W Low", len(df[df["distance_pct"] < 15]))
    col4.metric("Avg RSI", round(df["rsi"].mean(), 2))

    col5, col6, col7, col8 = st.columns(4)

    col5.metric("Bullish Stocks", len(df[df["trend"] == "Bullish"]))
    col6.metric("Bearish Stocks", len(df[df["trend"] == "Bearish"]))
    col7.metric("Avg Score", round(df["score"].mean(), 2))
    col8.metric("Volume Spike Stocks", len(df[df["volume_ratio"] > 1.3]))

    st.subheader("Full Market Table")

    st.dataframe(
        filtered.sort_values("score", ascending=False),
        use_container_width=True
    )

with tab2:
    st.header("🔥 Market Heatmap")

    fig = px.treemap(
        filtered,
        path=["sector", "symbol"],
        values="score",
        color="distance_pct",
        hover_data=[
            "current_price",
            "day_change_pct",
            "rsi",
            "volume_ratio",
            "trend",
            "score"
        ],
    )

    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("🎯 52W Low Opportunities")

    low_df = filtered.sort_values(["distance_pct", "score"], ascending=[True, False])

    st.dataframe(
        low_df[
            [
                "symbol", "sector", "current_price", "day_change_pct",
                "52w_low", "distance_pct", "rsi", "volume_ratio",
                "trend", "score", "reasons"
            ]
        ],
        use_container_width=True
    )

    st.header("⚡ Swing Candidates")

    swing = filtered[
        (filtered["distance_pct"] < 20)
        &
        (filtered["rsi"] < 45)
    ].sort_values("score", ascending=False)

    st.dataframe(swing, use_container_width=True)

    st.header("🚀 Near 52W High Momentum")

    high_momentum = df[
        df["distance_from_high_pct"] < 15
    ].sort_values("distance_from_high_pct")

    st.dataframe(high_momentum, use_container_width=True)

with tab4:
    st.header("🏭 Sector Overview")

    sector_df = df.groupby("sector").agg(
        stocks=("symbol", "count"),
        avg_score=("score", "mean"),
        avg_rsi=("rsi", "mean"),
        avg_distance_from_low=("distance_pct", "mean"),
        avg_day_change=("day_change_pct", "mean"),
        bullish_count=("trend", lambda x: (x == "Bullish").sum()),
        bearish_count=("trend", lambda x: (x == "Bearish").sum())
    ).reset_index()

    sector_df["bullish_pct"] = round(
        (sector_df["bullish_count"] / sector_df["stocks"]) * 100,
        2
    )

    sector_df = sector_df.sort_values("avg_score", ascending=False)

    st.dataframe(sector_df, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        fig_sector_score = px.bar(
            sector_df,
            x="sector",
            y="avg_score",
            title="Sector Average Score"
        )
        st.plotly_chart(fig_sector_score, use_container_width=True)

    with col2:
        fig_sector_rsi = px.bar(
            sector_df,
            x="sector",
            y="avg_rsi",
            title="Sector Average RSI"
        )
        st.plotly_chart(fig_sector_rsi, use_container_width=True)

with tab5:
    st.header("🔍 Stock Explorer")

    selected_stock = st.selectbox(
        "Select Stock",
        sorted(df["symbol"].unique())
    )

    stock = df[df["symbol"] == selected_stock].iloc[0]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Current Price", stock["current_price"])
    col2.metric("Distance From Low %", stock["distance_pct"])
    col3.metric("RSI", stock["rsi"])
    col4.metric("Score", stock["score"])

    st.subheader("Stock Details")

    st.json(stock.to_dict())

    st.subheader("Reason Engine")

    st.info(stock["reasons"] if stock["reasons"] else "No strong reason generated yet.")

with tab6:
    st.header("🕰 Historical Snapshots")

    history_root = Path("data/history")

    if not history_root.exists():
        st.warning("No history folder found yet.")
    else:
        folders = sorted(
            [p.name for p in history_root.iterdir() if p.is_dir()],
            reverse=True
        )

        if not folders:
            st.warning("No historical snapshots available.")
        else:
            selected_date = st.selectbox("Select Snapshot Date", folders)

            history_file = history_root / selected_date / "latest_scan.csv"

            if history_file.exists():
                hist_df = pd.read_csv(history_file)
                st.dataframe(hist_df, use_container_width=True)
            else:
                st.warning("Snapshot file missing.")
