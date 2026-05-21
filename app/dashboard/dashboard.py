import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import requests
import base64
from io import StringIO
from datetime import datetime
from zoneinfo import ZoneInfo
import math

st.set_page_config(page_title="StockGPT", layout="wide")

st.title("📈 StockGPT Market Intelligence Terminal")

SCAN_FILE = Path("data/scans/latest_scan.csv")

if not SCAN_FILE.exists():
    st.warning("No scan data available yet.")
    st.stop()

df = pd.read_csv(SCAN_FILE)

if "scan_time" in df.columns and not df["scan_time"].dropna().empty:
    last_scan_time_text = str(df["scan_time"].dropna().iloc[0])
    st.caption(f"🕒 Last scanned on {last_scan_time_text}")

    try:
        last_scan_dt = datetime.strptime(
            last_scan_time_text,
            "%d.%m.%Y at %I:%M %p IST"
        ).replace(tzinfo=ZoneInfo("Asia/Kolkata"))

        now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
        hours_old = (now_ist - last_scan_dt).total_seconds() / 3600

        if hours_old > 16:
            st.error(
                f"⚠️ Data may be stale. Last scan was around {round(hours_old, 1)} hours ago."
            )
        elif hours_old > 8:
            st.warning(
                f"⚠️ Data is getting old. Last scan was around {round(hours_old, 1)} hours ago."
            )
        else:
            st.success(
                f"✅ Data freshness looks okay. Last scan was around {round(hours_old, 1)} hours ago."
            )

    except Exception:
        st.warning("⚠️ Could not verify scan freshness from scan_time format.")
else:
    st.caption("🕒 Last scanned time unavailable")
    st.warning("⚠️ Scan time is missing, so data freshness cannot be verified.")

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

missing = [c for c in required_cols if c not in df.columns]

if missing:
    st.error(f"Missing columns in latest_scan.csv: {missing}")
    st.stop()

optional_cols = [
    "market_cap_cr",
    "technical_score",
    "fundamental_score",
    "sector_score",
    "relative_strength_score",
    "risk_penalty",
    "final_conviction_score",
    "sector_bucket",
    "sector_fundamental_adjustment",
    "sector_adjusted_fundamental_score",
    "active_fundamental_score",
    "return_1m",
    "return_3m",
    "return_6m",
    "return_vs_nifty_1m",
    "return_vs_nifty_3m",
    "return_vs_nifty_6m",
    "sector_rank",
    "sector_rank_pct",
    "score_band",
    "profitability_score",
    "growth_score",
    "balance_sheet_score",
    "cashflow_score",
    "valuation_score",
    "fundamental_risk_penalty"
]

for col in optional_cols:
    if col not in df.columns:
        df[col] = "Unknown" if col in ["score_band", "sector_bucket"] else 0

numeric_cols = [
    "current_price",
    "day_change_pct",
    "distance_pct",
    "distance_from_high_pct",
    "rsi",
    "volume_ratio",
    "score",
    "market_cap_cr",
    "technical_score",
    "fundamental_score",
    "sector_score",
    "relative_strength_score",
    "risk_penalty",
    "final_conviction_score",
    "sector_fundamental_adjustment",
    "sector_adjusted_fundamental_score",
    "active_fundamental_score",
    "return_1m",
    "return_3m",
    "return_6m",
    "return_vs_nifty_1m",
    "return_vs_nifty_3m",
    "return_vs_nifty_6m",
    "sector_rank",
    "sector_rank_pct",
    "profitability_score",
    "growth_score",
    "balance_sheet_score",
    "cashflow_score",
    "valuation_score",
    "fundamental_risk_penalty"
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df[col] = df[col].replace([float("inf"), float("-inf")], pd.NA)

df = df.dropna(subset=["symbol", "current_price", "distance_pct", "distance_from_high_pct", "rsi", "score"])

for col in numeric_cols:
    df[col] = df[col].fillna(0)

df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
df["sector"] = df["sector"].fillna("Unknown").astype(str)
df["industry"] = df["industry"].fillna("Unknown").astype(str)
df["trend"] = df["trend"].fillna("Unknown").astype(str)
df["reasons"] = df["reasons"].fillna("").astype(str)
df["score_band"] = df["score_band"].fillna("Unknown").astype(str)
df["sector_bucket"] = df["sector_bucket"].fillna("Unknown").astype(str)

if "final_conviction_score" not in df.columns or df["final_conviction_score"].sum() == 0:
    df["final_conviction_score"] = df["score"]


# =========================
# Helpers
# =========================

def safe_range_slider(label, series, step=1.0, key=None, sidebar=True):
    clean = pd.to_numeric(series, errors="coerce")
    clean = clean.replace([float("inf"), float("-inf")], pd.NA).dropna()

    if clean.empty:
        min_value = 0.0
        max_value = float(step)
    else:
        min_value = float(round(clean.min(), 2))
        max_value = float(round(clean.max(), 2))

        if min_value == max_value:
            max_value = min_value + float(step)

    if max_value <= min_value:
        max_value = min_value + float(step)

    widget = st.sidebar.slider if sidebar else st.slider

    return widget(
        label,
        min_value=float(min_value),
        max_value=float(max_value),
        value=(float(min_value), float(max_value)),
        step=float(step),
        key=key
    )


def display_table(dataframe, columns=None):
    if dataframe.empty:
        st.info("No data available.")
        return

    if columns:
        cols = [c for c in columns if c in dataframe.columns]
        st.dataframe(dataframe[cols], use_container_width=True)
    else:
        st.dataframe(dataframe, use_container_width=True)


def classify_score(score):
    try:
        score = float(score)
    except Exception:
        return "Unknown"

    if score >= 75:
        return "A+ High Conviction"
    if score >= 65:
        return "A Strong"
    if score >= 55:
        return "B Watchlist"
    if score >= 45:
        return "C Neutral"
    if score >= 35:
        return "D Weak"
    return "E Avoid"


if "score_band" not in df.columns or (df["score_band"] == "Unknown").all():
    df["score_band"] = df["final_conviction_score"].apply(classify_score)


# =========================
# Watchlist storage
# =========================

WATCHLIST_PATH = "data/watchlist/watchlist.csv"
WATCHLIST_COLUMNS = ["symbol", "basket", "notes", "added_at"]

WATCHLIST_BASKETS = [
    "52W Low Opportunities",
    "Swing Candidates",
    "Near 52W High Momentum",
    "High Conviction",
    "Personal Watchlist",
    "Research",
    "Avoid / Risky"
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

    try:
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
        content = base64.b64decode(payload["content"]).decode("utf-8")

        if not content.strip():
            return empty_watchlist()

        watchlist = pd.read_csv(StringIO(content))

        for col in WATCHLIST_COLUMNS:
            if col not in watchlist.columns:
                watchlist[col] = ""

        watchlist["symbol"] = watchlist["symbol"].astype(str).str.upper().str.strip()
        return watchlist[WATCHLIST_COLUMNS]

    except Exception as e:
        st.warning(f"Watchlist load failed: {e}")
        return empty_watchlist()


def save_watchlist_to_github(watchlist_df):
    token = get_streamlit_secret("GITHUB_TOKEN")
    branch = get_streamlit_secret("GITHUB_BRANCH", "main")

    if not token:
        st.error("GitHub token missing in Streamlit Secrets.")
        return False

    try:
        watchlist_df = watchlist_df[WATCHLIST_COLUMNS].drop_duplicates(subset=["symbol", "basket"])
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
            "content": base64.b64encode(csv_content.encode("utf-8")).decode("utf-8"),
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

    except Exception as e:
        st.error(f"Could not save watchlist: {e}")
        return False


def add_symbols_to_watchlist(symbols, basket, notes=""):
    watchlist = load_watchlist_from_github()
    now = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d.%m.%Y %I:%M %p IST")

    existing_pairs = set(zip(watchlist["symbol"].astype(str).str.upper(), watchlist["basket"].astype(str)))
    new_rows = []

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
        watchlist = pd.concat([watchlist, pd.DataFrame(new_rows)], ignore_index=True)

    return save_watchlist_to_github(watchlist)


def remove_symbols_from_watchlist(symbols, basket=None):
    watchlist = load_watchlist_from_github()
    symbols = [str(s).strip().upper() for s in symbols]

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


def render_add_to_watchlist(source_df, key_prefix, default_basket):
    st.subheader("➕ Add to Watchlist")

    st.text_input("Access key", type="password", key=f"{key_prefix}_access_key")

    if st.session_state.get(f"{key_prefix}_access_key", "") != get_streamlit_secret("WATCHLIST_SECRET", ""):
        st.info("Enter access key to add stocks to watchlist.")
        return

    available_symbols = sorted(source_df["symbol"].dropna().astype(str).str.upper().unique().tolist())

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

    notes = st.text_input("Notes", placeholder="Optional note", key=f"{key_prefix}_notes")

    if st.button("Add Selected to Watchlist", key=f"{key_prefix}_add_button"):
        if not selected_symbols:
            st.warning("Select at least one stock.")
        else:
            ok = add_symbols_to_watchlist(selected_symbols, basket, notes)

            if ok:
                st.success("Watchlist updated.")
                st.rerun()


# =========================
# Sidebar filters
# =========================

if "reset_counter" not in st.session_state:
    st.session_state["reset_counter"] = 0


def reset_all_filters():
    st.session_state["reset_counter"] += 1
    st.rerun()


st.sidebar.header("Filters")
rk = st.session_state["reset_counter"]

if st.sidebar.button("Reset All Filters", key=f"reset_all_{rk}"):
    reset_all_filters()

st.sidebar.caption("Filters are adaptive based on latest scan data.")

search_symbol = st.sidebar.text_input(
    "Search Symbol",
    placeholder="Example: IDEA, IDEAFORGE, MTARTECH",
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
    key=f"search_ignore_filters_{rk}"
)

sector_options = sorted(df["sector"].dropna().unique().tolist())
selected_sectors = st.sidebar.multiselect("Sectors", sector_options, default=sector_options, key=f"sectors_{rk}")

industry_options = sorted(df["industry"].dropna().unique().tolist())
selected_industries = st.sidebar.multiselect("Industries", industry_options, default=industry_options, key=f"industries_{rk}")

trend_options = sorted(df["trend"].dropna().unique().tolist())
selected_trends = st.sidebar.multiselect("Trend", trend_options, default=trend_options, key=f"trends_{rk}")

score_band_options = sorted(df["score_band"].dropna().unique().tolist())
selected_score_bands = st.sidebar.multiselect(
    "Score Band",
    score_band_options,
    default=score_band_options,
    key=f"score_bands_{rk}"
)

sector_bucket_options = sorted(df["sector_bucket"].dropna().unique().tolist())

selected_sector_buckets = st.sidebar.multiselect(
    "Sector Bucket",
    sector_bucket_options,
    default=sector_bucket_options,
    key=f"sector_buckets_{rk}"
)

distance_min, distance_max = safe_range_slider("Distance From 52W Low %", df["distance_pct"], step=0.1, key=f"dist_low_{rk}")
high_distance_min, high_distance_max = safe_range_slider("Distance From 52W High %", df["distance_from_high_pct"], step=0.1, key=f"dist_high_{rk}")
rsi_min, rsi_max = safe_range_slider("RSI Range", df["rsi"], step=0.1, key=f"rsi_{rk}")
final_score_min, final_score_max = safe_range_slider("Final Conviction Score", df["final_conviction_score"], step=1.0, key=f"final_{rk}")
technical_min, technical_max = safe_range_slider("Technical Score", df["technical_score"], step=1.0, key=f"tech_{rk}")
fundamental_min, fundamental_max = safe_range_slider("Fundamental Score", df["fundamental_score"], step=1.0, key=f"fund_{rk}")
adjusted_fundamental_min, adjusted_fundamental_max = safe_range_slider(
    "Sector Adjusted Fundamental Score",
    df["sector_adjusted_fundamental_score"],
    step=1.0,
    key=f"adjusted_fund_{rk}"
)

active_fundamental_min, active_fundamental_max = safe_range_slider(
    "Active Fundamental Score",
    df["active_fundamental_score"],
    step=1.0,
    key=f"active_fund_{rk}"
)

sector_adjustment_min, sector_adjustment_max = safe_range_slider(
    "Sector Fundamental Adjustment",
    df["sector_fundamental_adjustment"],
    step=1.0,
    key=f"sector_fund_adj_{rk}"
)
relative_min, relative_max = safe_range_slider("Relative Strength Score", df["relative_strength_score"], step=1.0, key=f"rel_{rk}")
risk_min, risk_max = safe_range_slider("Risk Penalty", df["risk_penalty"], step=1.0, key=f"risk_{rk}")
volume_min, volume_max = safe_range_slider("Volume Ratio", df["volume_ratio"], step=0.1, key=f"vol_{rk}")
day_min, day_max = safe_range_slider("Day Change %", df["day_change_pct"], step=0.1, key=f"day_{rk}")
price_min, price_max = safe_range_slider("Current Price", df["current_price"], step=1.0, key=f"price_{rk}")
ret1_min, ret1_max = safe_range_slider("1M Return %", df["return_1m"], step=0.1, key=f"ret1_{rk}")
ret3_min, ret3_max = safe_range_slider("3M Return %", df["return_3m"], step=0.1, key=f"ret3_{rk}")
ret6_min, ret6_max = safe_range_slider("6M Return %", df["return_6m"], step=0.1, key=f"ret6_{rk}")

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
        "Sector-Adjusted Quality",
        "Relative Strength Leaders",
        "Low Risk Quality",
        "Weak But Recovering",
        "Fresh Breakdown Risk",
        "Avoid / Risky"
    ],
    key=f"preset_{rk}"
)

filtered = df.copy()

if search_ignore_filters and search_symbol.strip():
    filtered = df[df["symbol"].str.contains(search_symbol.upper(), case=False, na=False)]
else:
    filtered = filtered[filtered["sector"].isin(selected_sectors)]
    filtered = filtered[filtered["industry"].isin(selected_industries)]
    filtered = filtered[filtered["trend"].isin(selected_trends)]
    filtered = filtered[filtered["score_band"].isin(selected_score_bands)]
    filtered = filtered[filtered["sector_bucket"].isin(selected_sector_buckets)]
    filtered = filtered[filtered["distance_pct"].between(distance_min, distance_max)]
    filtered = filtered[filtered["distance_from_high_pct"].between(high_distance_min, high_distance_max)]
    filtered = filtered[filtered["rsi"].between(rsi_min, rsi_max)]
    filtered = filtered[filtered["final_conviction_score"].between(final_score_min, final_score_max)]
    filtered = filtered[filtered["technical_score"].between(technical_min, technical_max)]
    filtered = filtered[filtered["fundamental_score"].between(fundamental_min, fundamental_max)]
    filtered = filtered[
        filtered["sector_adjusted_fundamental_score"].between(
            adjusted_fundamental_min,
            adjusted_fundamental_max
        )
    ]

    filtered = filtered[
        filtered["active_fundamental_score"].between(
            active_fundamental_min,
            active_fundamental_max
        )
    ]

    filtered = filtered[
        filtered["sector_fundamental_adjustment"].between(
            sector_adjustment_min,
            sector_adjustment_max
        )
    ]
    filtered = filtered[filtered["relative_strength_score"].between(relative_min, relative_max)]
    filtered = filtered[filtered["risk_penalty"].between(risk_min, risk_max)]
    filtered = filtered[filtered["volume_ratio"].between(volume_min, volume_max)]
    filtered = filtered[filtered["day_change_pct"].between(day_min, day_max)]
    filtered = filtered[filtered["current_price"].between(price_min, price_max)]
    filtered = filtered[filtered["return_1m"].between(ret1_min, ret1_max)]
    filtered = filtered[filtered["return_3m"].between(ret3_min, ret3_max)]
    filtered = filtered[filtered["return_6m"].between(ret6_min, ret6_max)]

    if search_symbol.strip():
        filtered = filtered[filtered["symbol"].str.contains(search_symbol.upper(), case=False, na=False)]

if search_reason.strip():
    filtered = filtered[filtered["reasons"].str.contains(search_reason, case=False, na=False)]

if preset == "52W Low Opportunities":
    filtered = filtered[filtered["distance_pct"] < 15]
elif preset == "Oversold Bounce":
    filtered = filtered[(filtered["distance_pct"] < 25) & (filtered["rsi"] < 45)]
elif preset == "Volume Spike":
    filtered = filtered[filtered["volume_ratio"] > 1.3]
elif preset == "Bullish Trend":
    filtered = filtered[filtered["trend"] == "Bullish"]
elif preset == "Bearish Weakness":
    filtered = filtered[filtered["trend"] == "Bearish"]
elif preset == "Near 52W High Momentum":
    filtered = filtered[filtered["distance_from_high_pct"] < 15]
elif preset == "High Conviction":
    filtered = filtered[filtered["final_conviction_score"] >= 60]
elif preset == "Strong Fundamentals":
    filtered = filtered[filtered["active_fundamental_score"] >= 60]
elif preset == "Sector-Adjusted Quality":
    filtered = filtered[
        (filtered["sector_adjusted_fundamental_score"] >= 60)
        &
        (filtered["sector_fundamental_adjustment"] >= 0)
    ]

elif preset == "Sector-Adjusted Quality":
    filtered = filtered[
        (filtered["sector_adjusted_fundamental_score"] >= 60)
        &
        (filtered["sector_fundamental_adjustment"] >= 0)
    ]

elif preset == "Relative Strength Leaders":
    filtered = filtered[filtered["relative_strength_score"] >= 60]
elif preset == "Low Risk Quality":
    filtered = filtered[
        (filtered["risk_penalty"] <= 10)
        &
        (filtered["active_fundamental_score"] >= 55)
        &
        (filtered["final_conviction_score"] >= 50)
    ]
elif preset == "Weak But Recovering":
    filtered = filtered[(filtered["rsi"] < 50) & (filtered["trend"] == "Bullish")]
elif preset == "Fresh Breakdown Risk":
    filtered = filtered[(filtered["trend"] == "Bearish") & (filtered["rsi"] < 40) & (filtered["day_change_pct"] < 0)]

elif preset == "Avoid / Risky":
    filtered = filtered[
        (filtered["score_band"] == "E Avoid")
        |
        (filtered["final_conviction_score"] < 35)
        |
        (filtered["risk_penalty"] >= 25)
        |
        (
            (filtered["active_fundamental_score"] < 30)
            &
            (filtered["relative_strength_score"] < 40)
        )
    ]

elif preset == "Avoid / Risky":
    filtered = filtered[
        (filtered["score_band"] == "E Avoid")
        |
        (filtered["final_conviction_score"] < 35)
        |
        (filtered["risk_penalty"] >= 25)
        |
        (
            (filtered["active_fundamental_score"] < 30)
            &
            (filtered["relative_strength_score"] < 40)
        )
    ]

st.sidebar.header("Advanced Query")
st.sidebar.caption('Examples: sector == "Technology" and rsi > 60 | final_conviction_score >= 70 and risk_penalty <= 10')

query_text = st.sidebar.text_area(
    "Custom Query",
    placeholder='industry == "Software - Application" and final_conviction_score >= 60',
    key=f"query_{rk}"
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
        st.info("Try relaxing filters or turn on 'Search ignores all filters'.")

    st.stop()

st.sidebar.header("Sorting")

sort_column = st.sidebar.selectbox(
    "Sort By",
    [
        "final_conviction_score",
        "score",
        "technical_score",
        "fundamental_score",
        "sector_adjusted_fundamental_score",
        "active_fundamental_score",
        "sector_fundamental_adjustment",
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

sort_order = st.sidebar.radio("Sort Order", ["Descending", "Ascending"], key=f"sort_order_{rk}")

filtered = filtered.sort_values(sort_column, ascending=(sort_order == "Ascending"))

# IMPORTANT:
# filtered_full keeps ALL rows after active filters.
# filtered_display is only row-limited for display tables/heatmaps.
# Opportunity baskets use filtered_full so stocks are not hidden by Max Rows Displayed.
filtered_full = filtered.copy()

filtered_count = len(filtered_full)

if filtered_count <= 10:
    result_limit = filtered_count
else:
    max_rows = min(filtered_count, 1000)
    result_limit = st.sidebar.slider(
        "Max Rows Displayed",
        min_value=10,
        max_value=max_rows,
        value=min(100, max_rows),
        step=1,
        key=f"rows_{rk}"
    )

filtered_display = filtered_full.head(result_limit)

st.sidebar.metric("Results", len(filtered_full))
st.sidebar.caption(f"Displaying top {len(filtered_display)} rows")

failed_file = Path("data/scans/failed_symbols.csv")

if failed_file.exists():
    failed_df = pd.read_csv(failed_file)
    st.sidebar.metric("Failed Symbols", len(failed_df))

    with st.sidebar.expander("View Failed Symbols"):
        st.dataframe(failed_df, use_container_width=True)


# =========================
# Tabs
# =========================

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "Market Overview",
    "Heatmap",
    "Opportunities",
    "Sectors",
    "Stock Explorer",
    "History",
    "Watchlist",
    "Fundamentals",
    "Movers & Changes"
])


with tab1:
    st.header("📊 Market Overview")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Stocks Scanned", len(df))
    col2.metric("Filtered Stocks", len(filtered_full))
    col3.metric("Displayed Stocks", len(filtered_display))
    col4.metric("Avg RSI", round(df["rsi"].mean(), 2))

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Bullish Stocks", len(df[df["trend"] == "Bullish"]))
    col6.metric("Bearish Stocks", len(df[df["trend"] == "Bearish"]))
    col7.metric("Avg Final Conviction", round(df["final_conviction_score"].mean(), 2))
    col8.metric("Avg Active Fundamental", round(df["active_fundamental_score"].mean(), 2))

    col9, col10, col11, col12 = st.columns(4)

    col9.metric("Avg Sector Adj. Fundamental", round(df["sector_adjusted_fundamental_score"].mean(), 2))
    col10.metric("Avg Sector Adjustment", round(df["sector_fundamental_adjustment"].mean(), 2))
    col11.metric("Volume Spike Stocks", len(df[df["volume_ratio"] > 1.3]))
    col12.metric(
        "Avoid / Risky Stocks",
        len(
            df[
                (df["score_band"] == "E Avoid")
                |
                (df["risk_penalty"] >= 25)
                |
                (
                    (df["active_fundamental_score"] < 30)
                    &
                    (df["relative_strength_score"] < 40)
                )
            ]
        )
    )

    st.subheader("📡 Market Breadth")

    breadth_cols = st.columns(5)

    above_50 = len(df[df["current_price"] > df.get("sma50", 0)]) if "sma50" in df.columns else 0
    above_200 = len(df[df["current_price"] > df.get("sma200", 0)]) if "sma200" in df.columns else 0

    breadth_cols[0].metric("% Above 50 DMA", round((above_50 / len(df)) * 100, 2))
    breadth_cols[1].metric("% Above 200 DMA", round((above_200 / len(df)) * 100, 2))
    breadth_cols[2].metric("RSI > 60", len(df[df["rsi"] > 60]))
    breadth_cols[3].metric("RSI < 40", len(df[df["rsi"] < 40]))
    breadth_cols[4].metric("Adv / Decl Ratio", round((len(df[df["day_change_pct"] > 0]) / max(len(df[df["day_change_pct"] < 0]), 1)), 2))

    st.subheader("🚨 Today’s Important Signals")

    signal1, signal2 = st.columns(2)

    with signal1:
        st.markdown("**Top Final Conviction**")
        display_table(
            df.sort_values("final_conviction_score", ascending=False).head(10),
            [
                "symbol",
                "sector",
                "industry",
                "sector_bucket",
                "current_price",
                "score_band",
                "final_conviction_score",
                "technical_score",
                "fundamental_score",
                "sector_fundamental_adjustment",
                "sector_adjusted_fundamental_score",
                "active_fundamental_score",
                "relative_strength_score",
                "sector_score",
                "risk_penalty",
            ]
        )

        st.markdown("**52W Low + Sector-Adjusted Quality**")
        low_quality = df[
            (df["distance_pct"] <= 20)
            &
            (df["active_fundamental_score"] >= 55)
        ].sort_values("final_conviction_score", ascending=False).head(10)
        display_table(
            low_quality,
            [
                "symbol",
                "sector",
                "industry",
                "sector_bucket",
                "current_price",
                "distance_pct",
                "rsi",
                "fundamental_score",
                "sector_fundamental_adjustment",
                "sector_adjusted_fundamental_score",
                "active_fundamental_score",
                "relative_strength_score",
                "final_conviction_score",
                "score_band",
            ]
        )

        st.markdown("**High Sector-Adjusted Quality + Low Risk**")
        quality_low_risk = df[
            (df["active_fundamental_score"] >= 60)
            &
            (df["risk_penalty"] <= 10)
        ].sort_values("final_conviction_score", ascending=False).head(10)
        display_table(
            quality_low_risk,
            [
                "symbol",
                "sector",
                "industry",
                "sector_bucket",
                "current_price",
                "fundamental_score",
                "sector_fundamental_adjustment",
                "sector_adjusted_fundamental_score",
                "active_fundamental_score",
                "relative_strength_score",
                "risk_penalty",
                "final_conviction_score",
                "score_band",
            ]
        )

    with signal2:
        st.markdown("**Relative Strength Leaders**")
        display_table(
            df.sort_values("relative_strength_score", ascending=False).head(10),
            [
                "symbol",
                "sector",
                "industry",
                "sector_bucket",
                "return_1m",
                "return_3m",
                "return_6m",
                "relative_strength_score",
                "sector_adjusted_fundamental_score",
                "active_fundamental_score",
                "final_conviction_score",
                "score_band",
            ]
        )

        st.markdown("**Volume Breakout Candidates**")
        volume_breakouts = df[
            df["volume_ratio"] >= 2
        ].sort_values("final_conviction_score", ascending=False).head(10)
        display_table(
            volume_breakouts,
            [
                "symbol",
                "sector",
                "industry",
                "sector_bucket",
                "current_price",
                "volume_ratio",
                "rsi",
                "technical_score",
                "fundamental_score",
                "sector_fundamental_adjustment",
                "sector_adjusted_fundamental_score",
                "active_fundamental_score",
                "relative_strength_score",
                "final_conviction_score",
                "score_band",
            ]
        )

        st.markdown("**Avoid / Risky Watch**")
        avoid_risky = df[
            (df["score_band"] == "E Avoid")
            |
            (df["risk_penalty"] >= 25)
            |
            (
                (df["active_fundamental_score"] < 30)
                &
                (df["relative_strength_score"] < 40)
            )
        ].sort_values(["risk_penalty", "final_conviction_score"], ascending=[False, True]).head(10)

        display_table(
            avoid_risky,
            [
                "symbol",
                "sector",
                "industry",
                "sector_bucket",
                "current_price",
                "final_conviction_score",
                "technical_score",
                "fundamental_score",
                "sector_fundamental_adjustment",
                "sector_adjusted_fundamental_score",
                "active_fundamental_score",
                "relative_strength_score",
                "sector_score",
                "risk_penalty",
                "score_band",
                "risk_reasons",
            ]
        )

        st.markdown("**Near 52W High Momentum**")
        high_momentum = df[
            (df["distance_from_high_pct"] <= 15)
            &
            (df["rsi"] >= 50)
            &
            (df["trend"] == "Bullish")
        ].sort_values("final_conviction_score", ascending=False).head(10)
        display_table(
            high_momentum,
            [
                "symbol",
                "sector",
                "industry",
                "sector_bucket",
                "current_price",
                "distance_from_high_pct",
                "rsi",
                "technical_score",
                "fundamental_score",
                "sector_fundamental_adjustment",
                "sector_adjusted_fundamental_score",
                "active_fundamental_score",
                "relative_strength_score",
                "final_conviction_score",
                "score_band",
            ]
        )

    st.subheader("Filtered Market Table")

    market_cols = [
        "symbol", "sector", "industry", "current_price", "day_change_pct",
        "market_cap_cr", "score_band", "final_conviction_score",
        "technical_score", "fundamental_score", "sector_bucket",
        "sector_fundamental_adjustment", "sector_adjusted_fundamental_score",
        "active_fundamental_score", "relative_strength_score",
        "sector_score", "risk_penalty", "rsi", "volume_ratio",
        "distance_pct", "distance_from_high_pct", "return_1m", "return_3m",
        "return_6m", "trend", "reasons"
    ]

    display_table(filtered_display, market_cols)


with tab2:
    st.header("🔥 Opportunity Heatmap")

    heatmap_df = filtered_display.copy()
    heatmap_df["heatmap_size"] = heatmap_df["final_conviction_score"].apply(lambda x: max(float(x), 1))

    fig = px.treemap(
        heatmap_df,
        path=["sector", "industry", "symbol"],
        values="heatmap_size",
        color="final_conviction_score",
        color_continuous_scale=["red", "yellow", "green"],
        hover_data=[
            "current_price", "day_change_pct", "rsi", "volume_ratio",
            "technical_score", "fundamental_score", "relative_strength_score",
            "sector_score", "risk_penalty", "final_conviction_score", "score_band"
        ],
        title="Opportunity Heatmap: Green = Higher Final Conviction, Red = Lower Final Conviction"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.header("📍 Daily Movement Heatmap")

    movement_df = filtered_display.copy()
    movement_df["heatmap_size"] = movement_df["current_price"].apply(lambda x: max(float(x), 1))

    move_fig = px.treemap(
        movement_df,
        path=["sector", "industry", "symbol"],
        values="heatmap_size",
        color="day_change_pct",
        color_continuous_scale=["red", "white", "green"],
        hover_data=["current_price", "day_change_pct", "rsi", "volume_ratio", "trend", "final_conviction_score", "score_band"],
        title="Daily Movement Heatmap: Green = Up Today, Red = Down Today"
    )

    st.plotly_chart(move_fig, use_container_width=True)


with tab3:
    opportunity_df = filtered_full.copy()
    st.caption(f"Opportunity baskets are calculated from all {len(opportunity_df)} filtered stocks, not only the displayed top {len(filtered_display)} rows.")

    st.header("🎯 52W Low Opportunities")

    low_opportunities = opportunity_df[
        opportunity_df["distance_pct"] <= 15
    ].sort_values(["distance_pct", "final_conviction_score"], ascending=[True, False])

    if low_opportunities.empty:
        st.info("No stocks currently qualify as 52W Low Opportunities under active filters.")
    else:
        display_table(
            low_opportunities,
            ["symbol", "sector", "industry", "sector_bucket", "current_price", "day_change_pct", "52w_low", "distance_pct", "rsi", "volume_ratio", "fundamental_score", "sector_fundamental_adjustment", "sector_adjusted_fundamental_score", "active_fundamental_score", "relative_strength_score", "final_conviction_score", "score_band", "reasons"]
        )
        render_add_to_watchlist(low_opportunities, "low_opp_watchlist", "52W Low Opportunities")

    st.divider()
    st.header("⚡ Swing Candidates")

    swing = opportunity_df[
        (opportunity_df["distance_pct"] <= 25)
        &
        (opportunity_df["rsi"] <= 45)
        &
        (opportunity_df["volume_ratio"] >= 1.0)
    ].sort_values("final_conviction_score", ascending=False)

    if swing.empty:
        st.info("No stocks currently qualify as Swing Candidates under active filters.")
    else:
        display_table(swing)
        render_add_to_watchlist(swing, "swing_watchlist", "Swing Candidates")

    st.divider()
    st.header("🚀 Near 52W High Momentum")

    high_momentum = opportunity_df[
        (opportunity_df["distance_from_high_pct"] <= 15)
        &
        (opportunity_df["rsi"] >= 50)
        &
        (opportunity_df["trend"] == "Bullish")
    ].sort_values(["distance_from_high_pct", "final_conviction_score"], ascending=[True, False])

    if high_momentum.empty:
        st.info("No stocks currently qualify as Near 52W High Momentum under active filters.")
    else:
        display_table(high_momentum)
        render_add_to_watchlist(high_momentum, "high_momentum_watchlist", "Near 52W High Momentum")


with tab4:
    st.header("🏭 Sector Overview")

    sector_df = filtered_full.groupby("sector").agg(
        stocks=("symbol", "count"),
        avg_final_conviction=("final_conviction_score", "mean"),
        avg_technical=("technical_score", "mean"),
        avg_raw_fundamental=("fundamental_score", "mean"),
        avg_sector_adjusted_fundamental=("sector_adjusted_fundamental_score", "mean"),
        avg_active_fundamental=("active_fundamental_score", "mean"),
        avg_sector_fundamental_adjustment=("sector_fundamental_adjustment", "mean"),
        avg_relative_strength=("relative_strength_score", "mean"),
        avg_sector_score=("sector_score", "mean"),
        avg_risk_penalty=("risk_penalty", "mean"),
        avg_rsi=("rsi", "mean"),
        avg_day_change=("day_change_pct", "mean"),
        avg_1m_return=("return_1m", "mean"),
        avg_3m_return=("return_3m", "mean"),
        avg_6m_return=("return_6m", "mean"),
        bullish_count=("trend", lambda x: (x == "Bullish").sum()),
        bearish_count=("trend", lambda x: (x == "Bearish").sum())
    ).reset_index()

    sector_df["bullish_pct"] = round((sector_df["bullish_count"] / sector_df["stocks"]) * 100, 2)
    sector_df = sector_df.sort_values("avg_final_conviction", ascending=False)

    display_table(sector_df)

    c1, c2 = st.columns(2)

    with c1:
        fig_sector = px.bar(sector_df, x="sector", y="avg_final_conviction", title="Sector Average Final Conviction")
        st.plotly_chart(fig_sector, use_container_width=True)

    with c2:
        fig_sector_rs = px.bar(sector_df, x="sector", y="avg_relative_strength", title="Sector Average Relative Strength")
        st.plotly_chart(fig_sector_rs, use_container_width=True)

    st.divider()
    st.header("🏭 Industry Overview")

    industry_df = filtered_full.groupby("industry").agg(
        stocks=("symbol", "count"),
        avg_final_conviction=("final_conviction_score", "mean"),
        avg_technical=("technical_score", "mean"),
        avg_raw_fundamental=("fundamental_score", "mean"),
        avg_sector_adjusted_fundamental=("sector_adjusted_fundamental_score", "mean"),
        avg_active_fundamental=("active_fundamental_score", "mean"),
        avg_sector_fundamental_adjustment=("sector_fundamental_adjustment", "mean"),
        avg_relative_strength=("relative_strength_score", "mean"),
        avg_risk_penalty=("risk_penalty", "mean"),
        avg_rsi=("rsi", "mean"),
        avg_1m_return=("return_1m", "mean"),
        avg_3m_return=("return_3m", "mean"),
        avg_6m_return=("return_6m", "mean")
    ).reset_index()

    industry_df = industry_df.sort_values("avg_final_conviction", ascending=False)

    display_table(industry_df)

    industry_fig = px.treemap(
        industry_df,
        path=["industry"],
        values="stocks",
        color="avg_final_conviction",
        color_continuous_scale=["red", "yellow", "green"],
        hover_data=[
            "avg_technical",
            "avg_raw_fundamental",
            "avg_sector_adjusted_fundamental",
            "avg_active_fundamental",
            "avg_sector_fundamental_adjustment",
            "avg_relative_strength",
            "avg_risk_penalty",
            "avg_rsi"
        ],
        title="Industry Heatmap by Final Conviction"
    )

    st.plotly_chart(industry_fig, use_container_width=True)


with tab5:
    st.header("🔍 Stock Explorer")

    selected_stock = st.selectbox("Select Stock", sorted(df["symbol"].unique()))
    stock = df[df["symbol"] == selected_stock].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Price", stock["current_price"])
    c2.metric("Final Conviction", stock["final_conviction_score"])
    c3.metric("Score Band", stock["score_band"])
    c4.metric("Risk Penalty", stock["risk_penalty"])

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Technical Score", stock["technical_score"])
    c6.metric("Fundamental Score", stock["fundamental_score"])
    c7.metric("Relative Strength", stock["relative_strength_score"])
    c8.metric("Sector Score", stock["sector_score"])

    c9, c10, c11, c12 = st.columns(4)

    c9.metric(
        "Sector Adjusted Fundamental",
        stock.get("sector_adjusted_fundamental_score", 0)
    )

    c10.metric(
        "Sector Adjustment",
        stock.get("sector_fundamental_adjustment", 0)
    )

    c11.metric(
        "Active Fundamental Score",
        stock.get("active_fundamental_score", 0)
    )

    c12.metric(
        "Sector Bucket",
        stock.get("sector_bucket", "Unknown")
    )

    st.subheader("Stock Details")
    st.json(stock.to_dict())

    st.subheader("Reason Engine")

    reason_value = stock.get("reasons", "")
    if pd.isna(reason_value) or str(reason_value).strip() == "":
        st.info("No strong reason generated yet.")
    else:
        st.info(reason_value)

    for label, column, level in [
        ("Technical Reasons", "technical_reasons", "info"),
        ("Fundamental Reasons", "fundamental_reasons", "info"),
        ("Relative Strength Reasons", "relative_strength_reasons", "info"),
        ("Risk Reasons", "risk_reasons", "warning"),
        ("Fundamental Risks", "fundamental_risks", "warning")
    ]:
        if column in df.columns:
            value = stock.get(column, "")

            if not pd.isna(value) and str(value).strip():
                st.subheader(label)

                if level == "warning":
                    st.warning(value)
                else:
                    st.info(value)

    st.divider()
    st.subheader("➕ Add This Stock to Watchlist")

    stock_access_key = st.text_input("Access key for Stock Explorer watchlist", type="password", key="stock_explorer_watchlist_key")

    if stock_access_key == get_streamlit_secret("WATCHLIST_SECRET", ""):
        basket = st.selectbox("Select Basket", WATCHLIST_BASKETS, key="stock_explorer_basket")
        notes = st.text_input("Notes", key="stock_explorer_notes")

        if st.button("Add This Stock"):
            ok = add_symbols_to_watchlist([selected_stock], basket, notes)

            if ok:
                st.success(f"{selected_stock} added to watchlist.")
                st.rerun()
    else:
        st.info("Enter access key to add this stock.")


with tab6:
    st.header("🕰 Historical Snapshots")

    history_root = Path("data/history")

    if not history_root.exists():
        st.warning("No history folder found yet.")
    else:
        folders = sorted([p.name for p in history_root.iterdir() if p.is_dir()], reverse=True)

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


with tab7:
    st.header("⭐ Permanent Watchlist")
    st.caption("This watchlist is saved permanently in GitHub. Visitors can view it, but editing requires your access key.")

    watchlist = load_watchlist_from_github()

    if watchlist.empty:
        st.info("Watchlist is empty.")
    else:
        watchlist["symbol"] = watchlist["symbol"].astype(str).str.upper().str.strip()
        merged_watchlist = watchlist.merge(df, on="symbol", how="left")

        baskets = sorted(watchlist["basket"].dropna().unique().tolist())

        selected_basket_view = st.selectbox("View Basket", ["All"] + baskets, key="watchlist_basket_view")

        display_watchlist = merged_watchlist.copy()

        if selected_basket_view != "All":
            display_watchlist = display_watchlist[display_watchlist["basket"] == selected_basket_view]

        watch_cols = [
            "symbol", "basket", "notes", "added_at", "sector", "industry",
            "current_price", "score_band", "final_conviction_score",
            "fundamental_score", "sector_bucket", "sector_fundamental_adjustment",
            "sector_adjusted_fundamental_score", "active_fundamental_score", "relative_strength_score", "risk_penalty",
            "rsi", "distance_pct", "distance_from_high_pct"
        ]

        st.subheader("Watchlist Table")
        display_table(display_watchlist, watch_cols)

        found_watchlist = display_watchlist[display_watchlist["current_price"].notna()]

        if not found_watchlist.empty:
            st.subheader("Watchlist Summary")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Stocks Found", len(found_watchlist))
            c2.metric("Avg RSI", round(found_watchlist["rsi"].mean(), 2))
            c3.metric("Avg Final Conviction", round(found_watchlist["final_conviction_score"].mean(), 2))
            c4.metric("Near 52W Low", len(found_watchlist[found_watchlist["distance_pct"] < 15]))

        missing_watchlist = display_watchlist[display_watchlist["current_price"].isna()]

        if not missing_watchlist.empty:
            st.warning("Some watchlist stocks were not found in latest scan.")
            display_table(missing_watchlist, ["symbol", "basket", "notes", "added_at"])

        st.divider()
        st.subheader("Watchlist by Opportunity Basket")

        for basket_name in baskets:
            basket_df = merged_watchlist[merged_watchlist["basket"] == basket_name]

            with st.expander(f"{basket_name} ({len(basket_df)})"):
                display_table(basket_df, watch_cols)

    st.divider()
    st.subheader("Remove from Watchlist")

    st.text_input("Access key to remove stocks", type="password", key="watchlist_access_key")

    if has_watchlist_access():
        if watchlist.empty:
            st.info("Nothing to remove.")
        else:
            remove_basket = st.selectbox("Remove from basket", ["All"] + sorted(watchlist["basket"].dropna().unique().tolist()), key="remove_basket")
            removable_df = watchlist.copy()

            if remove_basket != "All":
                removable_df = removable_df[removable_df["basket"] == remove_basket]

            removable_symbols = sorted(removable_df["symbol"].dropna().astype(str).unique().tolist())
            symbols_to_remove = st.multiselect("Select symbols to remove", removable_symbols, key="symbols_to_remove")

            if st.button("Remove Selected"):
                if not symbols_to_remove:
                    st.warning("Select at least one symbol.")
                else:
                    ok = remove_symbols_from_watchlist(symbols_to_remove, None if remove_basket == "All" else remove_basket)

                    if ok:
                        st.success("Selected symbols removed.")
                        st.rerun()
    else:
        st.info("Enter access key to remove stocks.")


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
                st.caption(f"🕒 Fundamentals last updated on {fundamentals_df['fundamental_scan_time'].dropna().iloc[0]}")

            dashboard_cols = [
                "symbol", "sector", "industry", "current_price", "rsi",
                "technical_score", "fundamental_score", "sector_bucket",
                "sector_fundamental_adjustment", "sector_adjusted_fundamental_score",
                "active_fundamental_score", "relative_strength_score", "sector_score",
                "risk_penalty", "final_conviction_score", "score_band"
            ]

            available_dashboard_cols = [c for c in dashboard_cols if c in df.columns]

            fundamentals_view = fundamentals_df.merge(
                df[available_dashboard_cols].drop_duplicates(subset=["symbol"]),
                on="symbol",
                how="left",
                suffixes=("", "_latest")
            )

            if "sector" not in fundamentals_view.columns:
                fundamentals_view["sector"] = fundamentals_view.get("sector_yf", "Unknown")

            if "industry" not in fundamentals_view.columns:
                fundamentals_view["industry"] = fundamentals_view.get("industry_yf", "Unknown")

            fundamentals_view["sector"] = fundamentals_view["sector"].fillna("Unknown").astype(str)
            fundamentals_view["industry"] = fundamentals_view["industry"].fillna("Unknown").astype(str)
           
            if "sector_bucket" not in fundamentals_view.columns:
                fundamentals_view["sector_bucket"] = "Unknown"

            fundamentals_view["sector_bucket"] = fundamentals_view["sector_bucket"].fillna("Unknown").astype(str)

            fund_numeric = [
                "fundamental_score", "profitability_score", "growth_score",
                "balance_sheet_score", "cashflow_score", "valuation_score",
                "fundamental_risk_penalty", "market_cap_cr", "trailing_pe",
                "forward_pe", "price_to_book", "debt_to_equity", "roe", "roa",
                "operating_margin", "net_profit_margin", "gross_margin",
                "revenue_growth", "earnings_growth", "current_ratio",
                "quick_ratio", "total_cash_cr", "total_debt_cr",
                "free_cashflow_cr", "operating_cashflow_cr", "dividend_yield",
                "beta", "final_conviction_score", "technical_score",
                "relative_strength_score", "sector_fundamental_adjustment",
                "sector_adjusted_fundamental_score", "active_fundamental_score", "risk_penalty"
            ]

            for col in fund_numeric:
                if col not in fundamentals_view.columns:
                    fundamentals_view[col] = 0

                fundamentals_view[col] = pd.to_numeric(fundamentals_view[col], errors="coerce")
                fundamentals_view[col] = fundamentals_view[col].replace([float("inf"), float("-inf")], pd.NA).fillna(0)

            st.subheader("Fundamental Filters")

            f1, f2, f3 = st.columns(3)

            with f1:
                selected_fund_sectors = st.multiselect(
                    "Fundamental Sector",
                    sorted(fundamentals_view["sector"].dropna().unique().tolist()),
                    default=[],
                    placeholder="Leave blank for all",
                    key="fund_sector"
                )

            with f2:
                selected_fund_industries = st.multiselect(
                    "Fundamental Industry",
                    sorted(fundamentals_view["industry"].dropna().unique().tolist()),
                    default=[],
                    placeholder="Leave blank for all",
                    key="fund_industry"
                )

            with f3:
                fund_search = st.text_input(
                    "Search Symbol / Company",
                    placeholder="Example: RELIANCE, TCS, PIIND",
                    key="fund_search"
                )

            f4, f5, f6 = st.columns(3)

            with f4:
                fs_min, fs_max = safe_range_slider("Fundamental Score", fundamentals_view["fundamental_score"], step=1.0, key="fund_fs", sidebar=False)

            with f5:
                roe_min2, roe_max2 = safe_range_slider("ROE %", fundamentals_view["roe"], step=0.1, key="fund_roe", sidebar=False)

            with f6:
                debt_min2, debt_max2 = safe_range_slider("Debt/Equity", fundamentals_view["debt_to_equity"], step=1.0, key="fund_debt", sidebar=False)

            f7, f8, f9 = st.columns(3)

            with f7:
                rev_min, rev_max = safe_range_slider("Revenue Growth %", fundamentals_view["revenue_growth"], step=0.1, key="fund_rev", sidebar=False)

            with f8:
                margin_min, margin_max = safe_range_slider("Net Profit Margin %", fundamentals_view["net_profit_margin"], step=0.1, key="fund_margin", sidebar=False)

            with f9:
                div_min, div_max = safe_range_slider("Dividend Yield %", fundamentals_view["dividend_yield"], step=0.1, key="fund_div", sidebar=False)

            f10, f11, f12 = st.columns(3)

            with f10:
                mcap_min, mcap_max = safe_range_slider("Market Cap ₹ Cr", fundamentals_view["market_cap_cr"], step=100.0, key="fund_mcap", sidebar=False)

            with f11:
                pe_min, pe_max = safe_range_slider("Trailing PE", fundamentals_view["trailing_pe"], step=1.0, key="fund_pe", sidebar=False)

            with f12:
                pb_min, pb_max = safe_range_slider("Price to Book", fundamentals_view["price_to_book"], step=0.1, key="fund_pb", sidebar=False)

            adjusted_fs_min, adjusted_fs_max = safe_range_slider(
                "Sector Adjusted Fundamental Score",
                fundamentals_view["sector_adjusted_fundamental_score"],
                step=1.0,
                key="fund_adjusted_fs",
                sidebar=False
            )

            active_fs_min, active_fs_max = safe_range_slider(
                "Active Fundamental Score",
                fundamentals_view["active_fundamental_score"],
                step=1.0,
                key="fund_active_fs",
                sidebar=False
            )

            sector_adj_min, sector_adj_max = safe_range_slider(
                "Sector Fundamental Adjustment",
                fundamentals_view["sector_fundamental_adjustment"],
                step=1.0,
                key="fund_sector_adj",
                sidebar=False
            )

            filtered_fundamentals = fundamentals_view.copy()

            if selected_fund_sectors:
                filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["sector"].isin(selected_fund_sectors)]

            if selected_fund_industries:
                filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["industry"].isin(selected_fund_industries)]

            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["fundamental_score"].between(fs_min, fs_max)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["sector_adjusted_fundamental_score"].between(adjusted_fs_min, adjusted_fs_max)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["active_fundamental_score"].between(active_fs_min, active_fs_max)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["sector_fundamental_adjustment"].between(sector_adj_min, sector_adj_max)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["roe"].between(roe_min2, roe_max2)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["debt_to_equity"].between(debt_min2, debt_max2)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["revenue_growth"].between(rev_min, rev_max)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["net_profit_margin"].between(margin_min, margin_max)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["dividend_yield"].between(div_min, div_max)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["market_cap_cr"].between(mcap_min, mcap_max)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["trailing_pe"].between(pe_min, pe_max)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["price_to_book"].between(pb_min, pb_max)]

            if fund_search.strip():
                search_text = fund_search.strip().upper()
                company_col = filtered_fundamentals["company_name"] if "company_name" in filtered_fundamentals.columns else pd.Series([""] * len(filtered_fundamentals), index=filtered_fundamentals.index)

                filtered_fundamentals = filtered_fundamentals[
                    filtered_fundamentals["symbol"].astype(str).str.upper().str.contains(search_text, na=False)
                    |
                    company_col.astype(str).str.upper().str.contains(search_text, na=False)
                ]

            st.caption(f"Showing {len(filtered_fundamentals)} out of {len(fundamentals_view)} fundamental rows")

            display_cols = [
                "symbol", "company_name", "sector", "industry", "market_cap_cr",
                "fundamental_score", "sector_bucket", "sector_fundamental_adjustment",
                "sector_adjusted_fundamental_score", "active_fundamental_score", "profitability_score", "growth_score",
                "balance_sheet_score", "cashflow_score", "valuation_score",
                "fundamental_risk_penalty", "final_conviction_score",
                "score_band", "roe", "roa", "debt_to_equity", "trailing_pe",
                "price_to_book", "operating_margin", "net_profit_margin",
                "revenue_growth", "earnings_growth", "operating_cashflow_cr",
                "free_cashflow_cr", "dividend_yield", "fundamental_reasons",
                "fundamental_risks"
            ]

            st.subheader("Fundamental Quality Table")
            display_table(filtered_fundamentals.sort_values("active_fundamental_score", ascending=False), display_cols)

            st.subheader("Top Sector-Adjusted Fundamental Companies")
            display_table(filtered_fundamentals.sort_values("sector_adjusted_fundamental_score", ascending=False).head(25), display_cols)

            st.subheader("Best Combined Candidates")
            display_table(filtered_fundamentals.sort_values("final_conviction_score", ascending=False).head(25), display_cols)

# =========================
# TAB 9 — MOVERS & CHANGES
# =========================

with tab9:
    st.header("📈 Movers & Changes")

    changes_file = Path("data/history/latest_changes.csv")

    if not changes_file.exists():
        st.warning("No latest_changes.csv found yet. Run phase6_pipeline.yml after adding change_tracker.py.")
    else:
        changes_df = pd.read_csv(changes_file)

        if changes_df.empty:
            st.info("No change data available yet.")
        else:
            if "change_scan_time" in changes_df.columns and not changes_df["change_scan_time"].dropna().empty:
                st.caption(f"🕒 Changes calculated on {changes_df['change_scan_time'].dropna().iloc[0]}")

            changes_df["symbol"] = (
                changes_df["symbol"]
                .astype(str)
                .str.upper()
                .str.strip()
            )

            text_cols = [
                "sector",
                "industry",
                "previous_score_band",
                "current_score_band",
                "change_signal"
            ]

            for col in text_cols:
                if col not in changes_df.columns:
                    changes_df[col] = "Unknown"

                changes_df[col] = changes_df[col].fillna("Unknown").astype(str)

            numeric_change_cols = [
                "current_price",
                "previous_final_score",
                "current_final_score",
                "score_change",
                "previous_rsi",
                "current_rsi",
                "rsi_change",
                "previous_risk",
                "current_risk",
                "risk_change",
                "technical_score",
                "fundamental_score",
                "relative_strength_score",
                "volume_ratio",
                "distance_pct",
                "distance_from_high_pct"
            ]

            for col in numeric_change_cols:
                if col not in changes_df.columns:
                    changes_df[col] = 0

                changes_df[col] = pd.to_numeric(
                    changes_df[col],
                    errors="coerce"
                ).fillna(0)

            st.subheader("Change Summary")

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Rows Compared",
                len(changes_df)
            )

            col2.metric(
                "Score Improvers",
                len(changes_df[changes_df["score_change"] > 0])
            )

            col3.metric(
                "Score Droppers",
                len(changes_df[changes_df["score_change"] < 0])
            )

            col4.metric(
                "Risk Increased",
                len(changes_df[changes_df["risk_change"] > 0])
            )

            col5, col6, col7, col8 = st.columns(4)

            col5.metric(
                "New High Conviction",
                len(
                    changes_df[
                        changes_df["change_signal"].str.contains(
                            "New High Conviction",
                            case=False,
                            na=False
                        )
                    ]
                )
            )

            col6.metric(
                "Entered Strong Zone",
                len(
                    changes_df[
                        changes_df["change_signal"].str.contains(
                            "Entered Strong Zone",
                            case=False,
                            na=False
                        )
                    ]
                )
            )

            col7.metric(
                "RSI Recovery",
                len(
                    changes_df[
                        changes_df["change_signal"].str.contains(
                            "RSI Recovery|Fresh Momentum",
                            case=False,
                            na=False
                        )
                    ]
                )
            )

            col8.metric(
                "Risk Warnings",
                len(
                    changes_df[
                        changes_df["change_signal"].str.contains(
                            "Risk Increased|New Risk Warning",
                            case=False,
                            na=False
                        )
                    ]
                )
            )

            st.subheader("Change Filters")

            c1, c2, c3 = st.columns(3)

            with c1:
                change_sector_filter = st.multiselect(
                    "Sector",
                    sorted(changes_df["sector"].dropna().unique().tolist()),
                    default=[],
                    placeholder="Leave blank for all",
                    key="change_sector_filter"
                )

            with c2:
                available_signals = sorted(
                    changes_df["change_signal"]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

                change_signal_filter = st.multiselect(
                    "Change Signal",
                    available_signals,
                    default=[],
                    placeholder="Leave blank for all",
                    key="change_signal_filter"
                )

            with c3:
                change_search = st.text_input(
                    "Search Symbol",
                    placeholder="Example: RELIANCE, MTARTECH, IDEA",
                    key="change_search"
                )

            filtered_changes = changes_df.copy()

            if change_sector_filter:
                filtered_changes = filtered_changes[
                    filtered_changes["sector"].isin(change_sector_filter)
                ]

            if change_signal_filter:
                filtered_changes = filtered_changes[
                    filtered_changes["change_signal"].isin(change_signal_filter)
                ]

            if change_search.strip():
                filtered_changes = filtered_changes[
                    filtered_changes["symbol"].str.contains(
                        change_search.strip().upper(),
                        case=False,
                        na=False
                    )
                ]

            st.caption(
                f"Showing {len(filtered_changes)} out of {len(changes_df)} changed rows"
            )

            st.subheader("🚀 Biggest Score Improvers")

            score_improvers = filtered_changes[
                filtered_changes["score_change"] > 0
            ].sort_values(
                "score_change",
                ascending=False
            ).head(25)

            display_table(
                score_improvers,
                [
                    "symbol",
                    "sector",
                    "industry",
                    "current_price",
                    "previous_final_score",
                    "current_final_score",
                    "score_change",
                    "previous_score_band",
                    "current_score_band",
                    "change_signal"
                ]
            )

            st.subheader("⚠️ Biggest Score Droppers")

            score_droppers = filtered_changes[
                filtered_changes["score_change"] < 0
            ].sort_values(
                "score_change",
                ascending=True
            ).head(25)

            display_table(
                score_droppers,
                [
                    "symbol",
                    "sector",
                    "industry",
                    "current_price",
                    "previous_final_score",
                    "current_final_score",
                    "score_change",
                    "previous_score_band",
                    "current_score_band",
                    "change_signal"
                ]
            )

            st.subheader("🟢 New / Improved Conviction")

            improved_conviction = filtered_changes[
                filtered_changes["change_signal"].str.contains(
                    "Entered Strong Zone|New High Conviction|Score Improved|RSI Recovery|Fresh Momentum",
                    case=False,
                    na=False
                )
            ].sort_values(
                ["score_change", "current_final_score"],
                ascending=[False, False]
            ).head(25)

            display_table(
                improved_conviction,
                [
                    "symbol",
                    "sector",
                    "industry",
                    "current_price",
                    "previous_final_score",
                    "current_final_score",
                    "score_change",
                    "previous_rsi",
                    "current_rsi",
                    "rsi_change",
                    "previous_score_band",
                    "current_score_band",
                    "change_signal"
                ]
            )

            st.subheader("🔴 Risk / Weakness Alerts")

            risk_changes = filtered_changes[
                filtered_changes["change_signal"].str.contains(
                    "Risk Increased|New Risk Warning|Score Dropped|Fresh Weakness|Lost High Conviction|Dropped Below Strong Zone",
                    case=False,
                    na=False
                )
            ].sort_values(
                ["risk_change", "score_change"],
                ascending=[False, True]
            ).head(25)

            display_table(
                risk_changes,
                [
                    "symbol",
                    "sector",
                    "industry",
                    "current_price",
                    "previous_risk",
                    "current_risk",
                    "risk_change",
                    "previous_final_score",
                    "current_final_score",
                    "score_change",
                    "previous_score_band",
                    "current_score_band",
                    "change_signal"
                ]
            )

            st.subheader("📋 Full Change Table")

            display_table(
                filtered_changes.sort_values(
                    ["score_change", "current_final_score"],
                    ascending=[False, False]
                ),
                [
                    "symbol",
                    "sector",
                    "industry",
                    "current_price",
                    "previous_final_score",
                    "current_final_score",
                    "score_change",
                    "previous_rsi",
                    "current_rsi",
                    "rsi_change",
                    "previous_risk",
                    "current_risk",
                    "risk_change",
                    "previous_score_band",
                    "current_score_band",
                    "change_signal"
                ]
            )
