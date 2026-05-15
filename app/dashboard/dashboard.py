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
# Sidebar filters
st.sidebar.header("Filters")

st.sidebar.caption("Use these filters to narrow opportunities without changing the underlying scan.")

# =========================
# TEXT SEARCH
# =========================

search_symbol = st.sidebar.text_input(
    "Search Symbol",
    placeholder="Example: INFY, HDFCBANK, RELIANCE"
)

search_reason = st.sidebar.text_input(
    "Search Reason",
    placeholder="Example: RSI, 52W, volume"
)

# =========================
# SECTOR FILTER
# =========================

sector_options = sorted(df["sector"].dropna().unique().tolist())

selected_sectors = st.sidebar.multiselect(
    "Sectors",
    sector_options,
    default=sector_options
)

# =========================
# TREND FILTER
# =========================

trend_options = sorted(df["trend"].dropna().unique().tolist())

selected_trends = st.sidebar.multiselect(
    "Trend",
    trend_options,
    default=trend_options
)

# =========================
# NUMERIC FILTERS
# =========================

distance_min, distance_max = st.sidebar.slider(
    "Distance From 52W Low %",
    min_value=0,
    max_value=300,
    value=(0, 100)
)

high_distance_min, high_distance_max = st.sidebar.slider(
    "Distance From 52W High %",
    min_value=0,
    max_value=300,
    value=(0, 100)
)

rsi_min, rsi_max = st.sidebar.slider(
    "RSI Range",
    min_value=0,
    max_value=100,
    value=(0, 100)
)

score_min, score_max = st.sidebar.slider(
    "Score Range",
    min_value=0,
    max_value=100,
    value=(0, 100)
)

volume_min, volume_max = st.sidebar.slider(
    "Volume Ratio Range",
    min_value=0.0,
    max_value=10.0,
    value=(0.0, 10.0),
    step=0.1
)

day_change_min, day_change_max = st.sidebar.slider(
    "Day Change %",
    min_value=-20.0,
    max_value=20.0,
    value=(-20.0, 20.0),
    step=0.1
)

price_min = float(df["current_price"].min())
price_max = float(df["current_price"].max())

selected_price_min, selected_price_max = st.sidebar.slider(
    "Current Price Range",
    min_value=float(round(price_min, 2)),
    max_value=float(round(price_max, 2)),
    value=(float(round(price_min, 2)), float(round(price_max, 2))),
    step=1.0
)

# =========================
# QUICK PRESETS
# =========================

st.sidebar.header("Quick Presets")

preset = st.sidebar.selectbox(
    "Preset Strategy",
    [
        "Custom",
        "52W Low Opportunities",
        "Oversold Bounce",
        "Volume Spike",
        "Bullish Trend",
        "Near 52W High Momentum",
        "Weak Sector Hunt",
        "High Conviction"
    ]
)

filtered = df.copy()

# =========================
# APPLY BASIC FILTERS
# =========================

filtered = filtered[
    filtered["sector"].isin(selected_sectors)
]

filtered = filtered[
    filtered["trend"].isin(selected_trends)
]

filtered = filtered[
    filtered["distance_pct"].between(distance_min, distance_max)
]

filtered = filtered[
    filtered["distance_from_high_pct"].between(high_distance_min, high_distance_max)
]

filtered = filtered[
    filtered["rsi"].between(rsi_min, rsi_max)
]

filtered = filtered[
    filtered["score"].between(score_min, score_max)
]

filtered = filtered[
    filtered["volume_ratio"].between(volume_min, volume_max)
]

filtered = filtered[
    filtered["day_change_pct"].between(day_change_min, day_change_max)
]

filtered = filtered[
    filtered["current_price"].between(selected_price_min, selected_price_max)
]

if search_symbol.strip():
    filtered = filtered[
        filtered["symbol"].str.contains(search_symbol.upper(), case=False, na=False)
    ]

if search_reason.strip():
    filtered = filtered[
        filtered["reasons"].astype(str).str.contains(search_reason, case=False, na=False)
    ]

# =========================
# APPLY PRESETS
# =========================

if preset == "52W Low Opportunities":
    filtered = filtered[
        filtered["distance_pct"] < 15
    ]

elif preset == "Oversold Bounce":
    filtered = filtered[
        (filtered["distance_pct"] < 25)
        &
        (filtered["rsi"] < 45)
    ]

elif preset == "Volume Spike":
    filtered = filtered[
        filtered["volume_ratio"] > 1.3
    ]

elif preset == "Bullish Trend":
    filtered = filtered[
        filtered["trend"] == "Bullish"
    ]

elif preset == "Near 52W High Momentum":
    filtered = filtered[
        filtered["distance_from_high_pct"] < 15
    ]

elif preset == "Weak Sector Hunt":
    filtered = filtered[
        (filtered["rsi"] < 45)
        &
        (filtered["trend"] == "Bearish")
    ]

elif preset == "High Conviction":
    filtered = filtered[
        filtered["score"] >= 60
    ]

# =========================
# ADVANCED QUERY TOOL
# =========================

st.sidebar.header("Advanced Query")

st.sidebar.caption(
    'Examples: sector == "Healthcare" and rsi > 70 | score >= 60 and volume_ratio > 1.5'
)

query_text = st.sidebar.text_area(
    "Custom Query",
    placeholder='sector == "Healthcare" and rsi > 70'
)

if query_text.strip():
    try:
        filtered = df.query(query_text)
        st.sidebar.success("Custom query applied.")
    except Exception as e:
        st.sidebar.error(f"Invalid query: {e}")

# =========================
# SORTING
# =========================

st.sidebar.header("Sorting")

sort_column = st.sidebar.selectbox(
    "Sort By",
    [
        "score",
        "distance_pct",
        "rsi",
        "volume_ratio",
        "day_change_pct",
        "distance_from_high_pct",
        "current_price"
    ]
)

sort_order = st.sidebar.radio(
    "Sort Order",
    ["Descending", "Ascending"]
)

filtered = filtered.sort_values(
    sort_column,
    ascending=(sort_order == "Ascending")
)

# =========================
# RESULT LIMIT
# =========================

result_limit = st.sidebar.slider(
    "Max Rows Displayed",
    min_value=10,
    max_value=500,
    value=100,
    step=10
)

filtered = filtered.head(result_limit)

st.sidebar.metric("Results", len(filtered))

if filtered.empty:
    st.warning("No stocks match the selected filters. Try relaxing the sidebar filters or choose Preset Strategy = Custom.")
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
