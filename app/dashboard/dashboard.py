import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="StockGPT",
    layout="wide"
)

st.title("📈 StockGPT Market Intelligence Terminal")

scan_file = Path("data/scans/latest_scan.csv")

if not scan_file.exists():
    st.warning("No scan data available. Run GitHub Action first.")
    st.stop()

df = pd.read_csv(scan_file)

required_columns = [
    "symbol",
    "sector",
    "current_price",
    "distance_pct",
    "rsi",
    "trend",
    "score"
]

missing = [col for col in required_columns if col not in df.columns]

if missing:
    st.error(f"Missing columns in latest_scan.csv: {missing}")
    st.stop()

df = df.dropna(subset=["distance_pct", "rsi", "score"])

st.sidebar.header("Filters")

sector_options = ["All"] + sorted(df["sector"].dropna().unique().tolist())

selected_sector = st.sidebar.selectbox(
    "Sector",
    sector_options
)

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
    60
)

min_score = st.sidebar.slider(
    "Minimum Score",
    0,
    100,
    0
)

filtered = df.copy()

filtered = filtered[
    (filtered["distance_pct"] <= max_distance)
    &
    (filtered["rsi"] <= max_rsi)
    &
    (filtered["score"] >= min_score)
]

if selected_sector != "All":
    filtered = filtered[
        filtered["sector"] == selected_sector
    ]

if filtered.empty:
    st.warning("No stocks match current filters.")
    st.stop()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Market Overview",
    "Heatmap",
    "Opportunities",
    "Sector View",
    "Stock Explorer",
    "History"
])

with tab1:
    st.header("📊 Market Breadth")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Stocks Scanned", len(df))
    col2.metric("Filtered Stocks", len(filtered))
    col3.metric("Bullish", len(filtered[filtered["trend"] == "Bullish"]))
    col4.metric("Near 52W Low", len(filtered[filtered["distance_pct"] < 15]))
    col5.metric("Avg RSI", round(filtered["rsi"].mean(), 2))

    st.subheader("Top Ranked Stocks")

    st.dataframe(
        filtered.sort_values("score", ascending=False),
        use_container_width=True
    )

    st.subheader("RSI Distribution")

    rsi_fig = px.histogram(
        filtered,
        x="rsi",
        nbins=20
    )

    st.plotly_chart(rsi_fig, use_container_width=True)

with tab2:
    st.header("🔥 Market Heatmap")

    heatmap_df = filtered.copy()

    heatmap_df["heatmap_size"] = heatmap_df["score"].clip(lower=1)

    fig = px.treemap(
        heatmap_df,
        path=["sector", "symbol"],
        values="heatmap_size",
        color="distance_pct",
        hover_data=[
            "current_price",
            "rsi",
            "trend",
            "score"
        ],
        color_continuous_scale="RdYlGn_r"
    )

    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("🎯 52W Low Opportunities")

    low_df = filtered.sort_values("distance_pct").head(50)

    st.dataframe(low_df, use_container_width=True)

    st.header("⚡ Swing Trade Candidates")

    swing_df = filtered[
        (filtered["distance_pct"] < 20)
        &
        (filtered["rsi"] < 45)
    ].sort_values("score", ascending=False)

    st.dataframe(swing_df, use_container_width=True)

    st.header("🚀 Near 52W High Momentum")

    if "distance_from_high_pct" in filtered.columns:
        high_df = filtered.sort_values("distance_from_high_pct").head(30)
        st.dataframe(high_df, use_container_width=True)
    else:
        st.info("distance_from_high_pct column not available yet.")

with tab4:
    st.header("🏭 Sector Overview")

    sector_df = filtered.groupby("sector").agg(
        stocks=("symbol", "count"),
        avg_score=("score", "mean"),
        avg_rsi=("rsi", "mean"),
        avg_distance_from_low=("distance_pct", "mean"),
        bullish_count=("trend", lambda x: (x == "Bullish").sum())
    ).reset_index()

    sector_df = sector_df.sort_values("avg_score", ascending=False)

    st.dataframe(sector_df, use_container_width=True)

    sector_score_fig = px.bar(
        sector_df,
        x="sector",
        y="avg_score",
        title="Average Sector Score"
    )

    st.plotly_chart(sector_score_fig, use_container_width=True)

    sector_rsi_fig = px.bar(
        sector_df,
        x="sector",
        y="avg_rsi",
        title="Average Sector RSI"
    )

    st.plotly_chart(sector_rsi_fig, use_container_width=True)

with tab5:
    st.header("🔍 Stock Explorer")

    selected_stock = st.selectbox(
        "Select Stock",
        sorted(df["symbol"].unique())
    )

    stock_row = df[df["symbol"] == selected_stock].iloc[0]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Price", stock_row["current_price"])
    c2.metric("RSI", stock_row["rsi"])
    c3.metric("Score", stock_row["score"])
    c4.metric("Distance From 52W Low", stock_row["distance_pct"])

    st.subheader("Stock Details")

    st.dataframe(
        pd.DataFrame([stock_row]),
        use_container_width=True
    )

    if "reasons" in df.columns:
        st.subheader("Reason Engine")
        st.write(stock_row["reasons"])

with tab6:
    st.header("📚 Historical Snapshots")

    history_root = Path("data/history")

    if history_root.exists():
        dates = sorted(
            [p.name for p in history_root.iterdir() if p.is_dir()],
            reverse=True
        )

        if dates:
            selected_date = st.selectbox("Select Date", dates)
            history_file = history_root / selected_date / "latest_scan.csv"

            if history_file.exists():
                history_df = pd.read_csv(history_file)
                st.dataframe(history_df, use_container_width=True)
            else:
                st.warning("History file missing for selected date.")
        else:
            st.info("No historical snapshots available yet.")
    else:
        st.info("No history folder available yet.")
