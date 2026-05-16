import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import math

st.set_page_config(page_title="StockGPT", layout="wide")

st.title("📈 StockGPT Market Intelligence Terminal")

scan_file = Path("data/scans/latest_scan.csv")

if not scan_file.exists():
    st.warning("No scan data available yet.")
    st.stop()

df = pd.read_csv(scan_file)

if "scan_time" in df.columns and not df["scan_time"].dropna().empty:
    last_scan_time = df["scan_time"].dropna().iloc[0]
    st.caption(f"🕒 Last scanned on {last_scan_time}")
else:
    st.caption("🕒 Last scanned time unavailable")

required_cols = [
    "symbol",
    "sector",
    "current_price",
    "day_change_pct",
    "distance_pct",
    "distance_from_high_pct",
    "rsi",
    "volume_ratio",
    "trend",
    "score",
    "reasons"
]

missing = [col for col in required_cols if col not in df.columns]

if missing:
    st.error(f"Missing columns in latest_scan.csv: {missing}")
    st.stop()

df = df.dropna(subset=["symbol", "distance_pct", "rsi", "score"])

# Clean types
numeric_cols = [
    "current_price",
    "day_change_pct",
    "distance_pct",
    "distance_from_high_pct",
    "rsi",
    "volume_ratio",
    "score"
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["current_price", "distance_pct", "distance_from_high_pct", "rsi", "score"])

df["symbol"] = df["symbol"].astype(str)
df["sector"] = df["sector"].astype(str)
df["trend"] = df["trend"].astype(str)
df["reasons"] = df["reasons"].fillna("").astype(str)

# =========================
# HELPER FUNCTIONS
# =========================

def safe_floor(value):
    if pd.isna(value):
        return 0
    return int(math.floor(float(value)))


def safe_ceil(value):
    if pd.isna(value):
        return 1
    return int(math.ceil(float(value)))


def adaptive_int_slider(label, series, default_full=True):
    min_val = safe_floor(series.min())
    max_val = safe_ceil(series.max())

    if min_val == max_val:
        max_val = min_val + 1

    default_value = (min_val, max_val) if default_full else (min_val, max_val)

    return st.sidebar.slider(
        label,
        min_value=min_val,
        max_value=max_val,
        value=default_value
    )


def adaptive_float_slider(label, series, step=0.1):
    min_val = float(round(series.min(), 2))
    max_val = float(round(series.max(), 2))

    if min_val == max_val:
        max_val = min_val + step

    return st.sidebar.slider(
        label,
        min_value=min_val,
        max_value=max_val,
        value=(min_val, max_val),
        step=step
    )


# =========================
# SIDEBAR FILTERS
# =========================

st.sidebar.header("Filters")

if st.sidebar.button("Reset All Filters"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.sidebar.caption("Filters are adaptive based on your latest scan data.")

# Search
search_symbol = st.sidebar.text_input(
    "Search Symbol",
    placeholder="Example: IDEA, IDEAFORGE, MTARTECH, INFY"
)

search_reason = st.sidebar.text_input(
    "Search Reason",
    placeholder="Example: RSI, 52W, volume"
)

search_ignore_filters = st.sidebar.checkbox(
    "Search ignores all filters",
    value=False,
    help="Turn this ON only when you want to find a stock even if current filters would normally hide it."
)

# Sector filter
sector_options = sorted(df["sector"].dropna().unique().tolist())

selected_sectors = st.sidebar.multiselect(
    "Sectors",
    sector_options,
    default=sector_options
)

# Trend filter
trend_options = sorted(df["trend"].dropna().unique().tolist())

selected_trends = st.sidebar.multiselect(
    "Trend",
    trend_options,
    default=trend_options
)

# Adaptive numeric filters
distance_min, distance_max = adaptive_float_slider(
    "Distance From 52W Low %",
    df["distance_pct"],
    step=0.1
)

high_distance_min, high_distance_max = adaptive_float_slider(
    "Distance From 52W High %",
    df["distance_from_high_pct"],
    step=0.1
)

rsi_min, rsi_max = adaptive_float_slider(
    "RSI Range",
    df["rsi"],
    step=0.1
)

score_min, score_max = adaptive_float_slider(
    "Score Range",
    df["score"],
    step=1.0
)

volume_min, volume_max = adaptive_float_slider(
    "Volume Ratio Range",
    df["volume_ratio"],
    step=0.1
)

day_change_min, day_change_max = adaptive_float_slider(
    "Day Change %",
    df["day_change_pct"],
    step=0.1
)

price_min, price_max = adaptive_float_slider(
    "Current Price Range",
    df["current_price"],
    step=1.0
)

# Quick presets
st.sidebar.header("Quick Presets")

preset = st.sidebar.selectbox(
    "Preset Strategy",
    [
        "Custom",
        "52W Low Opportunities",
        "Oversold Bounce",
        "Volume Spike",
        "Bullish Trend",
        "Bearish Weakness",
        "Near 52W High Momentum",
        "High Conviction",
        "Weak But Recovering",
        "Fresh Breakdown Risk"
    ]
)

# Start filtering
filtered = df.copy()

# If search override is ON, search directly from full df
if search_ignore_filters and search_symbol.strip():
    filtered = df[
        df["symbol"].str.contains(
            search_symbol.upper(),
            case=False,
            na=False
        )
    ]
else:
    # Apply normal filters
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
        filtered["current_price"].between(price_min, price_max)
    ]

    if search_symbol.strip():
        filtered = filtered[
            filtered["symbol"].str.contains(
                search_symbol.upper(),
                case=False,
                na=False
            )
        ]

if search_reason.strip():
    filtered = filtered[
        filtered["reasons"].str.contains(
            search_reason,
            case=False,
            na=False
        )
    ]

# Apply presets ON TOP of selected filters
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

elif preset == "Bearish Weakness":
    filtered = filtered[
        filtered["trend"] == "Bearish"
    ]

elif preset == "Near 52W High Momentum":
    filtered = filtered[
        filtered["distance_from_high_pct"] < 15
    ]

elif preset == "High Conviction":
    filtered = filtered[
        filtered["score"] >= 60
    ]

elif preset == "Weak But Recovering":
    filtered = filtered[
        (filtered["rsi"] < 50)
        &
        (filtered["trend"] == "Bullish")
    ]

elif preset == "Fresh Breakdown Risk":
    filtered = filtered[
        (filtered["trend"] == "Bearish")
        &
        (filtered["rsi"] < 40)
        &
        (filtered["day_change_pct"] < 0)
    ]

# Advanced query
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
        filtered = filtered.query(query_text)
        st.sidebar.success("Custom query applied.")
    except Exception as e:
        st.sidebar.error(f"Invalid query: {e}")

# Sorting
st.sidebar.header("Sorting")

sort_column = st.sidebar.selectbox(
    "Sort By",
    [
        "score",
        "distance_pct",
        "distance_from_high_pct",
        "rsi",
        "volume_ratio",
        "day_change_pct",
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

result_limit = st.sidebar.slider(
    "Max Rows Displayed",
    min_value=10,
    max_value=max(10, len(filtered)),
    value=min(100, max(10, len(filtered))),
    step=10
)

filtered = filtered.head(result_limit)

st.sidebar.metric("Results", len(filtered))

failed_file = Path("data/scans/failed_symbols.csv")

if failed_file.exists():
    failed_df = pd.read_csv(failed_file)

    st.sidebar.metric("Failed Symbols", len(failed_df))

    with st.sidebar.expander("View Failed Symbols"):
        st.dataframe(failed_df, use_container_width=True)

if filtered.empty:
    st.warning("No stocks meet the strict criteria.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Reset Filters"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    with col2:
        st.info(
            "Try relaxing filters, using Search ignores all filters, or searching another stock like IDEA, IDEAFORGE, MTARTECH, INFY."
        )

    st.stop()


# =========================
# TABS
# =========================

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Market Overview",
    "Heatmap",
    "Opportunities",
    "Sectors",
    "Stock Explorer",
    "History"
])


# =========================
# TAB 1 — MARKET OVERVIEW
# =========================

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

    st.subheader("Filtered Market Table")

    st.dataframe(
        filtered,
        use_container_width=True
    )


# =========================
# TAB 2 — HEATMAP
# =========================

with tab2:
    st.header("🔥 Market Heatmap")

    heatmap_df = filtered.copy()

    heatmap_df["heatmap_size"] = heatmap_df["score"].apply(
        lambda x: max(float(x), 1)
    )

    fig = px.treemap(
        heatmap_df,
        path=["sector", "symbol"],
        values="heatmap_size",
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


# =========================
# TAB 3 — OPPORTUNITIES
# =========================

with tab3:
    st.header("🎯 52W Low Opportunities")

    low_df = filtered.sort_values(
        ["distance_pct", "score"],
        ascending=[True, False]
    )

    st.dataframe(
        low_df[
            [
                "symbol",
                "sector",
                "current_price",
                "day_change_pct",
                "52w_low",
                "distance_pct",
                "rsi",
                "volume_ratio",
                "trend",
                "score",
                "reasons"
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

    high_momentum = filtered[
        filtered["distance_from_high_pct"] < 15
    ].sort_values("distance_from_high_pct")

    st.dataframe(high_momentum, use_container_width=True)


# =========================
# TAB 4 — SECTORS
# =========================

with tab4:
    st.header("🏭 Sector Overview")

    sector_df = filtered.groupby("sector").agg(
        stocks=("symbol", "count"),
        avg_score=("score", "mean"),
        avg_rsi=("rsi", "mean"),
        avg_distance_from_low=("distance_pct", "mean"),
        avg_distance_from_high=("distance_from_high_pct", "mean"),
        avg_day_change=("day_change_pct", "mean"),
        avg_volume_ratio=("volume_ratio", "mean"),
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


# =========================
# TAB 5 — STOCK EXPLORER
# =========================

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

    reason_value = stock["reasons"]

    if pd.isna(reason_value) or str(reason_value).strip() == "":
        st.info("No strong reason generated yet.")
    else:
        st.info(reason_value)


# =========================
# TAB 6 — HISTORY
# =========================

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
