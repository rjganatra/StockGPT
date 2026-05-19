import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import math
import requests
import base64
from io import StringIO
from datetime import datetime
from zoneinfo import ZoneInfo

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
    "industry",
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

optional_score_cols = [
    "market_cap_cr",
    "total_cash_cr",
    "total_debt_cr",
    "free_cashflow_cr",
    "operating_cashflow_cr",
    "technical_score",
    "fundamental_score",
    "sector_score",
    "relative_strength_score",
    "risk_penalty",
    "final_conviction_score",
    "return_1m",
    "return_3m",
    "return_6m",
    "return_vs_nifty_1m",
    "return_vs_nifty_3m",
    "return_vs_nifty_6m",
    "sector_rank",
    "sector_rank_pct"
]

for col in optional_score_cols:
    if col not in df.columns:
        df[col] = 0

numeric_cols = [
    "current_price",
    "day_change_pct",
    "distance_pct",
    "distance_from_high_pct",
    "rsi",
    "volume_ratio",
    "score",
    "technical_score",
    "fundamental_score",
    "sector_score",
    "relative_strength_score",
    "risk_penalty",
    "final_conviction_score",
    "return_1m",
    "return_3m",
    "return_6m",
    "return_vs_nifty_1m",
    "return_vs_nifty_3m",
    "return_vs_nifty_6m",
    "sector_rank",
    "sector_rank_pct"
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(
    subset=[
        "current_price",
        "distance_pct",
        "distance_from_high_pct",
        "rsi",
        "score"
    ]
)

for col in optional_score_cols:
    df[col] = df[col].fillna(0)

df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
df["sector"] = df["sector"].fillna("Unknown").astype(str)
df["industry"] = df["industry"].fillna("Unknown").astype(str)
df["trend"] = df["trend"].fillna("Unknown").astype(str)
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


def adaptive_float_slider(label, series, step=0.1, key=None):
    clean_series = pd.to_numeric(series, errors="coerce").dropna()

    if clean_series.empty:
        min_val = 0.0
        max_val = step
    else:
        min_val = float(round(clean_series.min(), 2))
        max_val = float(round(clean_series.max(), 2))

        if min_val == max_val:
            max_val = min_val + step

    return st.sidebar.slider(
        label,
        min_value=min_val,
        max_value=max_val,
        value=(min_val, max_val),
        step=step,
        key=key
    )


def display_table(dataframe, columns=None):
    if dataframe.empty:
        st.info("No data available.")
        return

    if columns:
        available_cols = [col for col in columns if col in dataframe.columns]
        st.dataframe(dataframe[available_cols], use_container_width=True)
    else:
        st.dataframe(dataframe, use_container_width=True)


# =========================
# WATCHLIST STORAGE — GITHUB BACKED
# =========================

WATCHLIST_PATH = "data/watchlist/watchlist.csv"

WATCHLIST_COLUMNS = [
    "symbol",
    "basket",
    "notes",
    "added_at"
]


def get_streamlit_secret(name, default=""):
    try:
        return st.secrets[name]
    except Exception:
        return default


def empty_watchlist():
    return pd.DataFrame(columns=WATCHLIST_COLUMNS)


def github_headers():
    token = get_streamlit_secret("GITHUB_TOKEN")

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }


def github_file_url():
    repo = get_streamlit_secret("GITHUB_REPO", "rjganatra/StockGPT")

    return f"https://api.github.com/repos/{repo}/contents/{WATCHLIST_PATH}"


def load_watchlist_from_github():
    token = get_streamlit_secret("GITHUB_TOKEN")
    branch = get_streamlit_secret("GITHUB_BRANCH", "main")

    if not token:
        local_file = Path(WATCHLIST_PATH)

        if local_file.exists():
            return pd.read_csv(local_file)

        return empty_watchlist()

    response = requests.get(
        github_file_url(),
        headers=github_headers(),
        params={"ref": branch},
        timeout=20
    )

    if response.status_code == 404:
        return empty_watchlist()

    if response.status_code != 200:
        st.warning(f"Could not load GitHub watchlist: {response.text}")
        return empty_watchlist()

    payload = response.json()

    content = base64.b64decode(
        payload["content"]
    ).decode("utf-8")

    if not content.strip():
        return empty_watchlist()

    watchlist = pd.read_csv(StringIO(content))

    for col in WATCHLIST_COLUMNS:
        if col not in watchlist.columns:
            watchlist[col] = ""

    watchlist["symbol"] = watchlist["symbol"].astype(str).str.upper().str.strip()

    return watchlist[WATCHLIST_COLUMNS]


def save_watchlist_to_github(watchlist_df):
    token = get_streamlit_secret("GITHUB_TOKEN")
    branch = get_streamlit_secret("GITHUB_BRANCH", "main")

    if not token:
        st.error("GitHub token missing in Streamlit Secrets.")
        return False

    watchlist_df = watchlist_df[WATCHLIST_COLUMNS].drop_duplicates(
        subset=["symbol", "basket"]
    )

    csv_content = watchlist_df.to_csv(index=False)

    get_response = requests.get(
        github_file_url(),
        headers=github_headers(),
        params={"ref": branch},
        timeout=20
    )

    sha = None

    if get_response.status_code == 200:
        sha = get_response.json().get("sha")

    payload = {
        "message": "Update StockGPT watchlist",
        "content": base64.b64encode(
            csv_content.encode("utf-8")
        ).decode("utf-8"),
        "branch": branch
    }

    if sha:
        payload["sha"] = sha

    put_response = requests.put(
        github_file_url(),
        headers=github_headers(),
        json=payload,
        timeout=20
    )

    if put_response.status_code not in [200, 201]:
        st.error(f"Could not save watchlist: {put_response.text}")
        return False

    return True


def add_symbols_to_watchlist(symbols, basket, notes=""):
    watchlist = load_watchlist_from_github()

    now = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%d.%m.%Y %I:%M %p IST")

    new_rows = []

    existing_pairs = set(
        zip(
            watchlist["symbol"].astype(str).str.upper(),
            watchlist["basket"].astype(str)
        )
    )

    for symbol in symbols:
        symbol = str(symbol).strip().upper()

        if not symbol:
            continue

        pair = (symbol, basket)

        if pair not in existing_pairs:
            new_rows.append({
                "symbol": symbol,
                "basket": basket,
                "notes": notes,
                "added_at": now
            })

    if new_rows:
        watchlist = pd.concat(
            [watchlist, pd.DataFrame(new_rows)],
            ignore_index=True
        )

    return save_watchlist_to_github(watchlist)


def remove_symbols_from_watchlist(symbols, basket=None):
    watchlist = load_watchlist_from_github()

    symbols = [
        str(symbol).strip().upper()
        for symbol in symbols
    ]

    if basket:
        watchlist = watchlist[
            ~(
                watchlist["symbol"].astype(str).str.upper().isin(symbols)
                &
                (watchlist["basket"].astype(str) == basket)
            )
        ]
    else:
        watchlist = watchlist[
            ~watchlist["symbol"].astype(str).str.upper().isin(symbols)
        ]

    return save_watchlist_to_github(watchlist)


def has_watchlist_access():
    entered_key = st.session_state.get("watchlist_access_key", "")
    correct_key = get_streamlit_secret("WATCHLIST_SECRET", "")

    return bool(correct_key) and entered_key == correct_key


WATCHLIST_BASKETS = [
    "52W Low Opportunities",
    "Swing Candidates",
    "Near 52W High Momentum",
    "High Conviction",
    "Personal Watchlist",
    "Research",
    "Avoid / Risky"
]


def render_add_to_watchlist(source_df, key_prefix, default_basket):
    st.subheader("➕ Add to Watchlist")

    st.text_input(
        "Access key",
        type="password",
        key=f"{key_prefix}_access_key"
    )

    if st.session_state.get(f"{key_prefix}_access_key", "") != get_streamlit_secret("WATCHLIST_SECRET", ""):
        st.info("Enter access key to add stocks to watchlist.")
        return

    available_symbols = sorted(
        source_df["symbol"].dropna().astype(str).str.upper().unique().tolist()
    )

    selected_symbols = st.multiselect(
        "Select stocks to add",
        available_symbols,
        key=f"{key_prefix}_symbols"
    )

    default_index = WATCHLIST_BASKETS.index(default_basket) if default_basket in WATCHLIST_BASKETS else 0

    basket = st.selectbox(
        "Basket",
        WATCHLIST_BASKETS,
        index=default_index,
        key=f"{key_prefix}_basket"
    )

    notes = st.text_input(
        "Notes",
        placeholder="Optional note",
        key=f"{key_prefix}_notes"
    )

    if st.button("Add Selected to Watchlist", key=f"{key_prefix}_add_button"):
        if not selected_symbols:
            st.warning("Select at least one stock.")
        else:
            ok = add_symbols_to_watchlist(
                selected_symbols,
                basket,
                notes
            )

            if ok:
                st.success("Watchlist updated.")
                st.rerun()


# =========================
# RESET STATE MANAGER
# =========================

if "reset_counter" not in st.session_state:
    st.session_state["reset_counter"] = 0


def reset_all_filters():
    st.session_state["reset_counter"] += 1
    st.rerun()


# =========================
# SIDEBAR FILTERS
# =========================

st.sidebar.header("Filters")

rk = st.session_state["reset_counter"]

if st.sidebar.button("Reset All Filters", key=f"reset_all_{rk}"):
    reset_all_filters()

st.sidebar.caption("Filters are adaptive based on your latest scan data.")

search_symbol = st.sidebar.text_input(
    "Search Symbol",
    placeholder="Example: IDEA, IDEAFORGE, MTARTECH, INFY",
    value="",
    key=f"search_symbol_{rk}"
)

search_reason = st.sidebar.text_input(
    "Search Reason",
    placeholder="Example: RSI, 52W, volume",
    value="",
    key=f"search_reason_{rk}"
)

search_ignore_filters = st.sidebar.checkbox(
    "Search ignores all filters",
    value=False,
    key=f"search_ignore_filters_{rk}",
    help="Turn this ON only when you want to find a stock even if current filters would normally hide it."
)

sector_options = sorted(df["sector"].dropna().unique().tolist())

selected_sectors = st.sidebar.multiselect(
    "Sectors",
    sector_options,
    default=sector_options,
    key=f"selected_sectors_{rk}"
)

industry_options = sorted(df["industry"].dropna().unique().tolist())

selected_industries = st.sidebar.multiselect(
    "Industries",
    industry_options,
    default=industry_options,
    key=f"selected_industries_{rk}"
)

trend_options = sorted(df["trend"].dropna().unique().tolist())

selected_trends = st.sidebar.multiselect(
    "Trend",
    trend_options,
    default=trend_options,
    key=f"selected_trends_{rk}"
)

distance_min, distance_max = adaptive_float_slider(
    "Distance From 52W Low %",
    df["distance_pct"],
    step=0.1,
    key=f"distance_slider_{rk}"
)

high_distance_min, high_distance_max = adaptive_float_slider(
    "Distance From 52W High %",
    df["distance_from_high_pct"],
    step=0.1,
    key=f"high_distance_slider_{rk}"
)

rsi_min, rsi_max = adaptive_float_slider(
    "RSI Range",
    df["rsi"],
    step=0.1,
    key=f"rsi_slider_{rk}"
)

score_min, score_max = adaptive_float_slider(
    "Score Range",
    df["score"],
    step=1.0,
    key=f"score_slider_{rk}"
)

final_score_min, final_score_max = adaptive_float_slider(
    "Final Conviction Score Range",
    df["final_conviction_score"],
    step=1.0,
    key=f"final_score_slider_{rk}"
)

technical_score_min, technical_score_max = adaptive_float_slider(
    "Technical Score Range",
    df["technical_score"],
    step=1.0,
    key=f"technical_score_slider_{rk}"
)

relative_score_min, relative_score_max = adaptive_float_slider(
    "Relative Strength Score Range",
    df["relative_strength_score"],
    step=1.0,
    key=f"relative_score_slider_{rk}"
)

fundamental_score_min, fundamental_score_max = adaptive_float_slider(
    "Fundamental Score Range",
    df["fundamental_score"],
    step=1.0,
    key=f"fundamental_score_slider_{rk}"
)

sector_score_min, sector_score_max = adaptive_float_slider(
    "Sector Score Range",
    df["sector_score"],
    step=1.0,
    key=f"sector_score_slider_{rk}"
)

risk_penalty_min, risk_penalty_max = adaptive_float_slider(
    "Risk Penalty Range",
    df["risk_penalty"],
    step=1.0,
    key=f"risk_penalty_slider_{rk}"
)

volume_min, volume_max = adaptive_float_slider(
    "Volume Ratio Range",
    df["volume_ratio"],
    step=0.1,
    key=f"volume_slider_{rk}"
)

day_change_min, day_change_max = adaptive_float_slider(
    "Day Change %",
    df["day_change_pct"],
    step=0.1,
    key=f"day_change_slider_{rk}"
)

price_min, price_max = adaptive_float_slider(
    "Current Price Range",
    df["current_price"],
    step=1.0,
    key=f"price_slider_{rk}"
)

return_1m_min, return_1m_max = adaptive_float_slider(
    "1M Return %",
    df["return_1m"],
    step=0.1,
    key=f"return_1m_slider_{rk}"
)

return_3m_min, return_3m_max = adaptive_float_slider(
    "3M Return %",
    df["return_3m"],
    step=0.1,
    key=f"return_3m_slider_{rk}"
)

return_6m_min, return_6m_max = adaptive_float_slider(
    "6M Return %",
    df["return_6m"],
    step=0.1,
    key=f"return_6m_slider_{rk}"
)

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
        "Strong Fundamentals",
        "Relative Strength Leaders",
        "Low Risk Quality",
        "Weak But Recovering",
        "Fresh Breakdown Risk"
    ],
    key=f"preset_{rk}"
)

filtered = df.copy()

if search_ignore_filters and search_symbol.strip():
    filtered = df[
        df["symbol"].str.contains(
            search_symbol.upper(),
            case=False,
            na=False
        )
    ]
else:
    filtered = filtered[
        filtered["sector"].isin(selected_sectors)
    ]

    filtered = filtered[
        filtered["industry"].isin(selected_industries)
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
        filtered["final_conviction_score"].between(final_score_min, final_score_max)
    ]

    filtered = filtered[
        filtered["technical_score"].between(technical_score_min, technical_score_max)
    ]

    filtered = filtered[
        filtered["relative_strength_score"].between(relative_score_min, relative_score_max)
    ]

    filtered = filtered[
        filtered["fundamental_score"].between(fundamental_score_min, fundamental_score_max)
    ]

    filtered = filtered[
        filtered["sector_score"].between(sector_score_min, sector_score_max)
    ]

    filtered = filtered[
        filtered["risk_penalty"].between(risk_penalty_min, risk_penalty_max)
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

    filtered = filtered[
        filtered["return_1m"].between(return_1m_min, return_1m_max)
    ]

    filtered = filtered[
        filtered["return_3m"].between(return_3m_min, return_3m_max)
    ]

    filtered = filtered[
        filtered["return_6m"].between(return_6m_min, return_6m_max)
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
        filtered["final_conviction_score"] >= 60
    ]

elif preset == "Strong Fundamentals":
    filtered = filtered[
        filtered["fundamental_score"] >= 60
    ]

elif preset == "Relative Strength Leaders":
    filtered = filtered[
        filtered["relative_strength_score"] >= 60
    ]

elif preset == "Low Risk Quality":
    filtered = filtered[
        (filtered["risk_penalty"] <= 10)
        &
        (filtered["final_conviction_score"] >= 50)
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

st.sidebar.header("Advanced Query")

st.sidebar.caption(
    'Examples: sector == "Technology" and rsi > 60 | final_conviction_score >= 70 and relative_strength_score > 50'
)

query_text = st.sidebar.text_area(
    "Custom Query",
    placeholder='industry == "Software - Application" and final_conviction_score >= 60',
    key=f"query_text_{rk}"
)

if query_text.strip():
    try:
        filtered = filtered.query(query_text)
        st.sidebar.success("Custom query applied.")
    except Exception as e:
        st.sidebar.error(f"Invalid query: {e}")

if filtered.empty:
    st.warning("No stocks meet the strict criteria.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Reset Filters"):
            reset_all_filters()

    with col2:
        st.info(
            "Try relaxing filters, using Search ignores all filters, or searching another stock like IDEA, IDEAFORGE, MTARTECH, INFY."
        )

    st.stop()

st.sidebar.header("Sorting")

sort_column = st.sidebar.selectbox(
    "Sort By",
    [
        "final_conviction_score",
        "score",
        "technical_score",
        "fundamental_score",
        "relative_strength_score",
        "sector_score",
        "risk_penalty",
        "distance_pct",
        "distance_from_high_pct",
        "rsi",
        "volume_ratio",
        "day_change_pct",
        "current_price",
        "return_1m",
        "return_3m",
        "return_6m"
    ],
    key=f"sort_column_{rk}"
)

sort_order = st.sidebar.radio(
    "Sort Order",
    ["Descending", "Ascending"],
    key=f"sort_order_{rk}"
)

filtered = filtered.sort_values(
    sort_column,
    ascending=(sort_order == "Ascending")
)

filtered_count = len(filtered)

if filtered_count <= 10:
    result_limit = filtered_count
else:
    max_rows_displayed = min(filtered_count, 1000)

    result_limit = st.sidebar.slider(
        "Max Rows Displayed",
        min_value=10,
        max_value=max_rows_displayed,
        value=min(100, max_rows_displayed),
        step=1,
        key=f"result_limit_{rk}"
    )

filtered = filtered.head(result_limit)

st.sidebar.metric("Results", len(filtered))

failed_file = Path("data/scans/failed_symbols.csv")

if failed_file.exists():
    failed_df = pd.read_csv(failed_file)

    st.sidebar.metric("Failed Symbols", len(failed_df))

    with st.sidebar.expander("View Failed Symbols"):
        st.dataframe(failed_df, use_container_width=True)


# =========================
# TABS
# =========================

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Market Overview",
    "Heatmap",
    "Opportunities",
    "Sectors",
    "Stock Explorer",
    "History",
    "Watchlist",
    "Fundamentals"
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
    col7.metric("Avg Final Conviction", round(df["final_conviction_score"].mean(), 2))
    col8.metric("Volume Spike Stocks", len(df[df["volume_ratio"] > 1.3]))

    col9, col10, col11, col12 = st.columns(4)

    col9.metric("Avg Technical Score", round(df["technical_score"].mean(), 2))
    col10.metric("Avg Fundamental Score", round(df["fundamental_score"].mean(), 2))
    col11.metric("Avg Relative Strength", round(df["relative_strength_score"].mean(), 2))
    col12.metric("Avg Risk Penalty", round(df["risk_penalty"].mean(), 2))

    st.subheader("Filtered Market Table")

    market_overview_cols = [
        "symbol",
        "sector",
        "industry",
        "current_price",
        "day_change_pct",
        "market_cap_cr",
        "final_conviction_score",
        "technical_score",
        "fundamental_score",
        "relative_strength_score",
        "sector_score",
        "risk_penalty",
        "rsi",
        "volume_ratio",
        "distance_pct",
        "distance_from_high_pct",
        "return_1m",
        "return_3m",
        "return_6m",
        "trend",
        "reasons"
]

available_market_cols = [
    col for col in market_overview_cols
    if col in filtered.columns
]

display_table(
    filtered[available_market_cols]
)


# =========================
# TAB 2 — HEATMAP
# =========================

with tab2:
    st.header("🔥 Opportunity Heatmap")

    heatmap_df = filtered.copy()

    heatmap_df["heatmap_size"] = heatmap_df["final_conviction_score"].apply(
        lambda x: max(float(x), 1)
    )

    fig = px.treemap(
        heatmap_df,
        path=["sector", "industry", "symbol"],
        values="heatmap_size",
        color="final_conviction_score",
        color_continuous_scale=["red", "yellow", "green"],
        hover_data=[
            "current_price",
            "day_change_pct",
            "rsi",
            "volume_ratio",
            "technical_score",
            "fundamental_score",
            "relative_strength_score",
            "sector_score",
            "risk_penalty",
            "final_conviction_score"
        ],
        title="Opportunity Heatmap: Green = Higher Final Conviction, Red = Lower Final Conviction"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.header("📍 Daily Movement Heatmap")

    movement_df = filtered.copy()

    movement_df["heatmap_size"] = movement_df["current_price"].apply(
        lambda x: max(float(x), 1)
    )

    move_fig = px.treemap(
        movement_df,
        path=["sector", "industry", "symbol"],
        values="heatmap_size",
        color="day_change_pct",
        color_continuous_scale=["red", "white", "green"],
        hover_data=[
            "current_price",
            "day_change_pct",
            "rsi",
            "volume_ratio",
            "trend",
            "final_conviction_score"
        ],
        title="Daily Movement Heatmap: Green = Up Today, Red = Down Today"
    )

    st.plotly_chart(move_fig, use_container_width=True)


# =========================
# TAB 3 — OPPORTUNITIES
# =========================

with tab3:
    st.header("🎯 52W Low Opportunities")

    low_opportunities = filtered[
        filtered["distance_pct"] <= 15
    ].sort_values(
        ["distance_pct", "final_conviction_score"],
        ascending=[True, False]
    )

    if low_opportunities.empty:
        st.info("No stocks currently qualify as 52W Low Opportunities under the active filters.")
    else:
        display_table(
            low_opportunities,
            [
                "symbol",
                "sector",
                "industry",
                "current_price",
                "day_change_pct",
                "52w_low",
                "distance_pct",
                "rsi",
                "volume_ratio",
                "technical_score",
                "fundamental_score",
                "relative_strength_score",
                "risk_penalty",
                "final_conviction_score",
                "reasons"
            ]
        )

        render_add_to_watchlist(
            low_opportunities,
            "low_opportunity_watchlist",
            "52W Low Opportunities"
        )

    st.divider()

    st.header("⚡ Swing Candidates")

    swing = filtered[
        (filtered["distance_pct"] <= 25)
        &
        (filtered["rsi"] <= 45)
        &
        (filtered["volume_ratio"] >= 1.0)
    ].sort_values(
        "final_conviction_score",
        ascending=False
    )

    if swing.empty:
        st.info("No stocks currently qualify as Swing Candidates under the active filters.")
    else:
        display_table(swing)

        render_add_to_watchlist(
            swing,
            "swing_watchlist",
            "Swing Candidates"
        )

    st.divider()

    st.header("🚀 Near 52W High Momentum")

    high_momentum = filtered[
        (filtered["distance_from_high_pct"] <= 15)
        &
        (filtered["rsi"] >= 50)
        &
        (filtered["trend"] == "Bullish")
    ].sort_values(
        ["distance_from_high_pct", "final_conviction_score"],
        ascending=[True, False]
    )

    if high_momentum.empty:
        st.info("No stocks currently qualify as Near 52W High Momentum under the active filters.")
    else:
        display_table(high_momentum)

        render_add_to_watchlist(
            high_momentum,
            "high_momentum_watchlist",
            "Near 52W High Momentum"
        )


# =========================
# TAB 4 — SECTORS + INDUSTRIES
# =========================

with tab4:
    st.header("🏭 Sector Overview")

    sector_df = filtered.groupby("sector").agg(
        stocks=("symbol", "count"),
        avg_final_conviction=("final_conviction_score", "mean"),
        avg_technical=("technical_score", "mean"),
        avg_fundamental=("fundamental_score", "mean"),
        avg_relative_strength=("relative_strength_score", "mean"),
        avg_sector_score=("sector_score", "mean"),
        avg_risk_penalty=("risk_penalty", "mean"),
        avg_rsi=("rsi", "mean"),
        avg_distance_from_low=("distance_pct", "mean"),
        avg_distance_from_high=("distance_from_high_pct", "mean"),
        avg_day_change=("day_change_pct", "mean"),
        avg_volume_ratio=("volume_ratio", "mean"),
        avg_1m_return=("return_1m", "mean"),
        avg_3m_return=("return_3m", "mean"),
        avg_6m_return=("return_6m", "mean"),
        bullish_count=("trend", lambda x: (x == "Bullish").sum()),
        bearish_count=("trend", lambda x: (x == "Bearish").sum())
    ).reset_index()

    sector_df["bullish_pct"] = round(
        (sector_df["bullish_count"] / sector_df["stocks"]) * 100,
        2
    )

    sector_df = sector_df.sort_values(
        "avg_final_conviction",
        ascending=False
    )

    display_table(sector_df)

    col1, col2 = st.columns(2)

    with col1:
        fig_sector_score = px.bar(
            sector_df,
            x="sector",
            y="avg_final_conviction",
            title="Sector Average Final Conviction"
        )
        st.plotly_chart(fig_sector_score, use_container_width=True)

    with col2:
        fig_sector_relative = px.bar(
            sector_df,
            x="sector",
            y="avg_relative_strength",
            title="Sector Average Relative Strength"
        )
        st.plotly_chart(fig_sector_relative, use_container_width=True)

    st.divider()

    st.header("🏭 Industry Overview")

    industry_df = filtered.groupby("industry").agg(
        stocks=("symbol", "count"),
        avg_final_conviction=("final_conviction_score", "mean"),
        avg_technical=("technical_score", "mean"),
        avg_fundamental=("fundamental_score", "mean"),
        avg_relative_strength=("relative_strength_score", "mean"),
        avg_sector_score=("sector_score", "mean"),
        avg_risk_penalty=("risk_penalty", "mean"),
        avg_rsi=("rsi", "mean"),
        avg_1m_return=("return_1m", "mean"),
        avg_3m_return=("return_3m", "mean"),
        avg_6m_return=("return_6m", "mean"),
        bullish_count=("trend", lambda x: (x == "Bullish").sum()),
        bearish_count=("trend", lambda x: (x == "Bearish").sum())
    ).reset_index()

    industry_df["bullish_pct"] = round(
        (industry_df["bullish_count"] / industry_df["stocks"]) * 100,
        2
    )

    industry_df = industry_df.sort_values(
        "avg_final_conviction",
        ascending=False
    )

    display_table(industry_df)

    industry_fig = px.treemap(
        industry_df,
        path=["industry"],
        values="stocks",
        color="avg_final_conviction",
        color_continuous_scale=["red", "yellow", "green"],
        hover_data=[
            "avg_technical",
            "avg_fundamental",
            "avg_relative_strength",
            "avg_risk_penalty",
            "avg_rsi",
            "avg_1m_return",
            "avg_3m_return",
            "avg_6m_return"
        ],
        title="Industry Heatmap by Final Conviction"
    )

    st.plotly_chart(industry_fig, use_container_width=True)

    st.subheader("Top Industries by Final Conviction")

    display_table(industry_df.head(25))


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
    col2.metric("Final Conviction", stock["final_conviction_score"])
    col3.metric("RSI", stock["rsi"])
    col4.metric("Risk Penalty", stock["risk_penalty"])

    col5, col6, col7, col8 = st.columns(4)

    col5.metric("Technical Score", stock["technical_score"])
    col6.metric("Fundamental Score", stock["fundamental_score"])
    col7.metric("Relative Strength", stock["relative_strength_score"])
    col8.metric("Sector Score", stock["sector_score"])

    st.subheader("Stock Details")

    st.json(stock.to_dict())

    st.subheader("Reason Engine")

    reason_value = stock["reasons"]

    if pd.isna(reason_value) or str(reason_value).strip() == "":
        st.info("No strong reason generated yet.")
    else:
        st.info(reason_value)

    if "technical_reasons" in df.columns:
        tech_reason = stock.get("technical_reasons", "")
        if not pd.isna(tech_reason) and str(tech_reason).strip():
            st.subheader("Technical Reasons")
            st.info(tech_reason)

    if "relative_strength_reasons" in df.columns:
        rs_reason = stock.get("relative_strength_reasons", "")
        if not pd.isna(rs_reason) and str(rs_reason).strip():
            st.subheader("Relative Strength Reasons")
            st.info(rs_reason)

    if "fundamental_reasons" in df.columns:
        fund_reason = stock.get("fundamental_reasons", "")
        if not pd.isna(fund_reason) and str(fund_reason).strip():
            st.subheader("Fundamental Reasons")
            st.info(fund_reason)

    if "risk_reasons" in df.columns:
        risk_reason = stock.get("risk_reasons", "")
        if not pd.isna(risk_reason) and str(risk_reason).strip():
            st.subheader("Risk Reasons")
            st.warning(risk_reason)

    st.divider()

    st.subheader("➕ Add This Stock to Watchlist")

    stock_access_key = st.text_input(
        "Access key for Stock Explorer watchlist",
        type="password",
        key="stock_explorer_watchlist_key"
    )

    if stock_access_key == get_streamlit_secret("WATCHLIST_SECRET", ""):
        basket = st.selectbox(
            "Select Basket",
            WATCHLIST_BASKETS,
            key="stock_explorer_basket"
        )

        notes = st.text_input(
            "Notes",
            key="stock_explorer_notes"
        )

        if st.button("Add This Stock"):
            ok = add_symbols_to_watchlist(
                [selected_stock],
                basket,
                notes
            )

            if ok:
                st.success(f"{selected_stock} added to watchlist.")
                st.rerun()
    else:
        st.info("Enter access key to add this stock.")


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


# =========================
# TAB 7 — WATCHLIST
# =========================

with tab7:
    st.header("⭐ Permanent Watchlist")

    st.caption(
        "This watchlist is saved permanently in GitHub. Visitors can view it, but editing requires your access key."
    )

    watchlist = load_watchlist_from_github()

    if watchlist.empty:
        st.info("Watchlist is empty.")
    else:
        watchlist["symbol"] = watchlist["symbol"].astype(str).str.upper()

        merged_watchlist = watchlist.merge(
            df,
            on="symbol",
            how="left"
        )

        baskets = sorted(
            watchlist["basket"].dropna().unique().tolist()
        )

        selected_basket_view = st.selectbox(
            "View Basket",
            ["All"] + baskets,
            key="watchlist_basket_view"
        )

        display_watchlist = merged_watchlist.copy()

        if selected_basket_view != "All":
            display_watchlist = display_watchlist[
                display_watchlist["basket"] == selected_basket_view
            ]

        st.subheader("Watchlist Table")

        display_table(display_watchlist)

        st.subheader("Watchlist Summary")

        found_watchlist = display_watchlist[
            display_watchlist["current_price"].notna()
        ]

        if not found_watchlist.empty:
            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Stocks Found", len(found_watchlist))
            col2.metric("Avg RSI", round(found_watchlist["rsi"].mean(), 2))
            col3.metric("Avg Final Conviction", round(found_watchlist["final_conviction_score"].mean(), 2))
            col4.metric(
                "Near 52W Low",
                len(found_watchlist[found_watchlist["distance_pct"] < 15])
            )

            col5, col6, col7, col8 = st.columns(4)

            col5.metric("Avg Fundamental", round(found_watchlist["fundamental_score"].mean(), 2))
            col6.metric("Avg Technical", round(found_watchlist["technical_score"].mean(), 2))
            col7.metric("Avg Relative Strength", round(found_watchlist["relative_strength_score"].mean(), 2))
            col8.metric("Avg Risk Penalty", round(found_watchlist["risk_penalty"].mean(), 2))

        missing_watchlist = display_watchlist[
            display_watchlist["current_price"].isna()
        ]

        if not missing_watchlist.empty:
            st.warning("Some watchlist stocks were not found in latest scan.")
            display_table(
                missing_watchlist,
                ["symbol", "basket", "notes", "added_at"]
            )

        st.divider()

        st.subheader("Watchlist by Opportunity Basket")

        for basket_name in baskets:
            basket_df = merged_watchlist[
                merged_watchlist["basket"] == basket_name
            ]

            with st.expander(f"{basket_name} ({len(basket_df)})"):
                display_table(basket_df)

    st.divider()

    st.subheader("Remove from Watchlist")

    st.text_input(
        "Access key to remove stocks",
        type="password",
        key="watchlist_access_key"
    )

    if has_watchlist_access():
        if watchlist.empty:
            st.info("Nothing to remove.")
        else:
            remove_basket = st.selectbox(
                "Remove from basket",
                ["All"] + sorted(watchlist["basket"].dropna().unique().tolist()),
                key="remove_basket"
            )

            removable_df = watchlist.copy()

            if remove_basket != "All":
                removable_df = removable_df[
                    removable_df["basket"] == remove_basket
                ]

            removable_symbols = sorted(
                removable_df["symbol"].dropna().astype(str).unique().tolist()
            )

            symbols_to_remove = st.multiselect(
                "Select symbols to remove",
                removable_symbols,
                key="symbols_to_remove"
            )

            if st.button("Remove Selected"):
                if not symbols_to_remove:
                    st.warning("Select at least one symbol.")
                else:
                    ok = remove_symbols_from_watchlist(
                        symbols_to_remove,
                        None if remove_basket == "All" else remove_basket
                    )

                    if ok:
                        st.success("Selected symbols removed.")
                        st.rerun()
    else:
        st.info("Enter access key to remove stocks.")


# =========================
# TAB 8 — FUNDAMENTALS
# =========================

with tab8:
    st.header("📚 Fundamentals")

    fundamentals_file = Path("data/fundamentals/fundamental_scores.csv")

    if not fundamentals_file.exists():
        st.warning("Fundamentals file not found. Run weekly_fundamentals.yml first.")
    else:
        fundamentals_df = pd.read_csv(fundamentals_file)

        if fundamentals_df.empty:
            st.warning("Fundamentals file exists but has no rows.")
        else:
            fundamentals_df["symbol"] = fundamentals_df["symbol"].astype(str).str.upper().str.strip()

            if "fundamental_scan_time" in fundamentals_df.columns and not fundamentals_df["fundamental_scan_time"].dropna().empty:
                fund_time = fundamentals_df["fundamental_scan_time"].dropna().iloc[0]
                st.caption(f"🕒 Fundamentals last updated on {fund_time}")

            # Merge latest dashboard data
            if "symbol" in df.columns:
                dashboard_cols = [
                    "symbol",
                    "sector",
                    "industry",
                    "current_price",
                    "rsi",
                    "technical_score",
                    "relative_strength_score",
                    "sector_score",
                    "risk_penalty",
                    "final_conviction_score"
                ]

                available_dashboard_cols = [
                    col for col in dashboard_cols
                    if col in df.columns
                ]

                fundamentals_view = fundamentals_df.merge(
                    df[available_dashboard_cols].drop_duplicates(subset=["symbol"]),
                    on="symbol",
                    how="left",
                    suffixes=("", "_latest")
                )
            else:
                fundamentals_view = fundamentals_df.copy()

            if "sector" not in fundamentals_view.columns:
                fundamentals_view["sector"] = fundamentals_view.get("sector_yf", "Unknown")

            if "industry" not in fundamentals_view.columns:
                fundamentals_view["industry"] = fundamentals_view.get("industry_yf", "Unknown")

            fundamentals_view["sector"] = fundamentals_view["sector"].fillna("Unknown").astype(str)
            fundamentals_view["industry"] = fundamentals_view["industry"].fillna("Unknown").astype(str)

            numeric_fund_cols = [
                "fundamental_score",
                "market_cap_cr",
                "trailing_pe",
                "forward_pe",
                "price_to_book",
                "debt_to_equity",
                "roe",
                "roa",
                "operating_margin",
                "net_profit_margin",
                "gross_margin",
                "revenue_growth",
                "earnings_growth",
                "current_ratio",
                "quick_ratio",
                "total_cash_cr",
                "total_debt_cr",
                "free_cashflow_cr",
                "operating_cashflow_cr",
                "dividend_yield",
                "beta",
                "final_conviction_score",
                "technical_score",
                "relative_strength_score",
                "risk_penalty"
            ]

            for col in numeric_fund_cols:
                if col not in fundamentals_view.columns:
                    fundamentals_view[col] = 0

                fundamentals_view[col] = pd.to_numeric(
                    fundamentals_view[col],
                    errors="coerce"
                )

            fundamentals_view[numeric_fund_cols] = fundamentals_view[numeric_fund_cols].fillna(0)

            st.subheader("Fundamental Filters")

            fcol1, fcol2, fcol3 = st.columns(3)

            sector_list = sorted(fundamentals_view["sector"].dropna().unique().tolist())
            industry_list = sorted(fundamentals_view["industry"].dropna().unique().tolist())

            with fcol1:
                selected_fund_sectors = st.multiselect(
                    "Fundamental Sector",
                    sector_list,
                    default=[],
                    placeholder="Choose sector or leave blank for all",
                    key="fundamental_sector_filter"
                )

            with fcol2:
                selected_fund_industries = st.multiselect(
                    "Fundamental Industry",
                    industry_list,
                    default=[],
                    placeholder="Choose industry or leave blank for all",
                    key="fundamental_industry_filter"
                )

            with fcol3:
                fund_search = st.text_input(
                    "Search Symbol / Company",
                    placeholder="Example: RELIANCE, TCS, PIIND",
                    key="fundamental_search"
                )

            # Adaptive slider helper inside Fundamentals tab
            def fund_slider(label, column, step=1.0, key=None):
                clean_series = pd.to_numeric(
                  fundamentals_view[column],
                 errors="coerce"
               )

               clean_series = clean_series.replace(
                   [float("inf"), float("-inf")],
                   pd.NA
               ).dropna()

               if clean_series.empty:
                      min_value = 0.0
                      max_value = float(step)
               else:
                   min_value = float(round(clean_series.min(), 2)).
                   max_value = float(round(clean_series.max(), 2))

                   if min_value == max_value:
                       max_value = min_value + float(step)

    # Avoid Streamlit slider crash when numbers are too tiny/awkward
    min_value = float(min_value)
    max_value = float(max_value)
    step = float(step)

    if max_value <= min_value:
        max_value = min_value + step

    return st.slider(
        label,
        min_value=min_value,
        max_value=max_value,
        value=(min_value, max_value),
        step=step,
        key=key
    )

            fcol4, fcol5, fcol6 = st.columns(3)

            with fcol4:
                fund_score_min, fund_score_max = fund_slider(
                    "Fundamental Score Range",
                    "fundamental_score",
                    step=1.0,
                    key="fund_score_range_filter"
                )

            with fcol5:
                roe_min, roe_max = fund_slider(
                    "ROE % Range",
                    "roe",
                    step=0.1,
                    key="roe_range_filter"
                )

            with fcol6:
                debt_min, debt_max = fund_slider(
                    "Debt/Equity Range",
                    "debt_to_equity",
                    step=1.0,
                    key="debt_range_filter"
                )

            fcol7, fcol8, fcol9 = st.columns(3)

            with fcol7:
                revenue_min, revenue_max = fund_slider(
                    "Revenue Growth % Range",
                    "revenue_growth",
                    step=0.1,
                    key="revenue_growth_range_filter"
                )

            with fcol8:
                margin_min, margin_max = fund_slider(
                    "Net Profit Margin % Range",
                    "net_profit_margin",
                    step=0.1,
                    key="profit_margin_range_filter"
                )

            with fcol9:
                dividend_min, dividend_max = fund_slider(
                    "Dividend Yield % Range",
                    "dividend_yield",
                    step=0.1,
                    key="dividend_yield_range_filter"
                )

            fcol10, fcol11, fcol12 = st.columns(3)

            with fcol10:
                market_cap_min, market_cap_max = fund_slider(
                    "Market Cap ₹ Cr Range",
                    "market_cap_cr",
                    step=100.0,
                    key="market_cap_cr_range_filter"
                )

            with fcol11:
                pe_min, pe_max = fund_slider(
                    "Trailing PE Range",
                    "trailing_pe",
                    step=1.0,
                    key="trailing_pe_range_filter"
                )

            with fcol12:
                pb_min, pb_max = fund_slider(
                    "Price to Book Range",
                    "price_to_book",
                    step=0.1,
                    key="price_to_book_range_filter"
                )

            filtered_fundamentals = fundamentals_view.copy()

            # Important: empty sector/industry selection means "All"
            if selected_fund_sectors:
                filtered_fundamentals = filtered_fundamentals[
                    filtered_fundamentals["sector"].isin(selected_fund_sectors)
                ]

            if selected_fund_industries:
                filtered_fundamentals = filtered_fundamentals[
                    filtered_fundamentals["industry"].isin(selected_fund_industries)
                ]

            filtered_fundamentals = filtered_fundamentals[
                filtered_fundamentals["fundamental_score"].between(fund_score_min, fund_score_max)
            ]

            filtered_fundamentals = filtered_fundamentals[
                filtered_fundamentals["roe"].between(roe_min, roe_max)
            ]

            filtered_fundamentals = filtered_fundamentals[
                filtered_fundamentals["debt_to_equity"].between(debt_min, debt_max)
            ]

            filtered_fundamentals = filtered_fundamentals[
                filtered_fundamentals["revenue_growth"].between(revenue_min, revenue_max)
            ]

            filtered_fundamentals = filtered_fundamentals[
                filtered_fundamentals["net_profit_margin"].between(margin_min, margin_max)
            ]

            filtered_fundamentals = filtered_fundamentals[
                filtered_fundamentals["dividend_yield"].between(dividend_min, dividend_max)
            ]

            filtered_fundamentals = filtered_fundamentals[
                filtered_fundamentals["market_cap_cr"].between(market_cap_min, market_cap_max)
            ]

            filtered_fundamentals = filtered_fundamentals[
                filtered_fundamentals["trailing_pe"].between(pe_min, pe_max)
            ]

            filtered_fundamentals = filtered_fundamentals[
                filtered_fundamentals["price_to_book"].between(pb_min, pb_max)
            ]

            if fund_search.strip():
                search_text = fund_search.strip().upper()

                company_col = (
                    filtered_fundamentals["company_name"]
                    if "company_name" in filtered_fundamentals.columns
                    else pd.Series([""] * len(filtered_fundamentals), index=filtered_fundamentals.index)
                )

                filtered_fundamentals = filtered_fundamentals[
                    filtered_fundamentals["symbol"].astype(str).str.upper().str.contains(search_text, na=False)
                    |
                    company_col.astype(str).str.upper().str.contains(search_text, na=False)
                ]

            st.caption(f"Showing {len(filtered_fundamentals)} out of {len(fundamentals_view)} fundamental rows")

            st.subheader("Fundamental Quality Table")

            display_cols = [
                "symbol",
                "company_name",
                "sector",
                "industry",
                "market_cap_cr",
                "fundamental_score",
                "final_conviction_score",
                "roe",
                "roa",
                "debt_to_equity",
                "trailing_pe",
                "price_to_book",
                "operating_margin",
                "net_profit_margin",
                "revenue_growth",
                "earnings_growth",
                "operating_cashflow_cr",
                "free_cashflow_cr",
                "dividend_yield",
                "fundamental_reasons",
                "fundamental_risks"
            ]

            available_display_cols = [
                col for col in display_cols
                if col in filtered_fundamentals.columns
            ]

            st.dataframe(
                filtered_fundamentals.sort_values(
                    "fundamental_score",
                    ascending=False
                )[available_display_cols],
                use_container_width=True
            )

            st.subheader("Top Fundamental Companies")

            st.dataframe(
                filtered_fundamentals.sort_values(
                    "fundamental_score",
                    ascending=False
                ).head(25)[available_display_cols],
                use_container_width=True
            )

            st.subheader("Best Combined Candidates")

            if "final_conviction_score" in filtered_fundamentals.columns:
                st.dataframe(
                    filtered_fundamentals.sort_values(
                        "final_conviction_score",
                        ascending=False
                    ).head(25)[available_display_cols],
                    use_container_width=True
                )
            else:
                st.info("Final conviction score not available yet.")
