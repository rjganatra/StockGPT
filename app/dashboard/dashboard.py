import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="StockGPT", layout="wide")
st.title("📈 StockGPT Market Intelligence Terminal")

scan_file = Path("data/scans/latest_scan.csv")

if not scan_file.exists() or scan_file.stat().st_size == 0:
    st.error("latest_scan.csv is missing or empty. Run phase6_pipeline.yml again.")
    st.stop()

df = pd.read_csv(scan_file)

if df.empty:
    st.error("latest_scan.csv has no rows.")
    st.stop()

st.sidebar.header("Filters")

search = st.sidebar.text_input("Search Symbol", "")

if "sector" in df.columns:
    sectors = sorted(df["sector"].dropna().unique().tolist())
    selected_sectors = st.sidebar.multiselect("Sector", sectors, default=sectors)
    df = df[df["sector"].isin(selected_sectors)]

if "rsi" in df.columns:
    rsi_range = st.sidebar.slider("RSI Range", 0, 100, (0, 100))
    df = df[df["rsi"].between(rsi_range[0], rsi_range[1])]

if "distance_pct" in df.columns:
    distance_range = st.sidebar.slider("Distance From 52W Low %", 0, 300, (0, 300))
    df = df[df["distance_pct"].between(distance_range[0], distance_range[1])]

if "score" in df.columns:
    score_min = st.sidebar.slider("Minimum Score", 0, 100, 0)
    df = df[df["score"] >= score_min]

if search and "symbol" in df.columns:
    df = df[df["symbol"].str.contains(search.upper(), case=False, na=False)]

query_text = st.sidebar.text_area(
    "Advanced Query",
    placeholder='Example: sector == "Healthcare" and rsi > 70'
)

if query_text.strip():
    try:
        df = df.query(query_text)
    except Exception as e:
        st.sidebar.error(f"Invalid query: {e}")

if df.empty:
    st.warning("No stocks match your filters.")
    st.stop()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview", "Heatmap", "Opportunities", "Sectors", "Stock Explorer"
])

with tab1:
    st.header("📊 Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Stocks Visible", len(df))
    c2.metric("Avg RSI", round(df["rsi"].mean(), 2) if "rsi" in df else "NA")
    c3.metric("Near 52W Low", len(df[df["distance_pct"] < 15]) if "distance_pct" in df else "NA")
    c4.metric("Avg Score", round(df["score"].mean(), 2) if "score" in df else "NA")

    st.dataframe(df, use_container_width=True)

with tab2:
    st.header("🔥 Heatmap")

    if {"sector", "symbol", "score", "distance_pct"}.issubset(df.columns):
        fig = px.treemap(
            df,
            path=["sector", "symbol"],
            values="score",
            color="distance_pct",
            hover_data=df.columns
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Heatmap needs sector, symbol, score, distance_pct columns.")

with tab3:
    st.header("🎯 52W Low Opportunities")

    if "distance_pct" in df.columns:
        st.dataframe(df.sort_values("distance_pct"), use_container_width=True)

    st.header("⚡ Swing Candidates")

    if {"distance_pct", "rsi"}.issubset(df.columns):
        swing = df[(df["distance_pct"] < 20) & (df["rsi"] < 45)]
        st.dataframe(swing, use_container_width=True)

with tab4:
    st.header("🏭 Sector Overview")

    if {"sector", "score", "rsi", "distance_pct"}.issubset(df.columns):
        sector_df = df.groupby("sector").agg(
            stocks=("symbol", "count"),
            avg_score=("score", "mean"),
            avg_rsi=("rsi", "mean"),
            avg_distance=("distance_pct", "mean")
        ).reset_index()

        st.dataframe(sector_df, use_container_width=True)

        st.plotly_chart(
            px.bar(sector_df, x="sector", y="avg_score", title="Sector Avg Score"),
            use_container_width=True
        )

with tab5:
    st.header("🔍 Stock Explorer")

    selected = st.selectbox("Select Stock", sorted(df["symbol"].unique()))
    stock = df[df["symbol"] == selected].iloc[0]

    st.json(stock.to_dict())
