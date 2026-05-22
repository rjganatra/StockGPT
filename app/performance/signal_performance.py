
import math
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

LATEST_SCAN_FILE = Path("data/scans/latest_scan.csv")
HISTORY_ROOT = Path("data/history")
OUTPUT_FILE = Path("data/performance/signal_performance.csv")
SUMMARY_FILE = Path("data/performance/signal_performance_summary.csv")

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

PERFORMANCE_SCAN_TIME = datetime.now(
    ZoneInfo("Asia/Kolkata")
).strftime("%d.%m.%Y at %I:%M %p IST")

MAX_HISTORY_SNAPSHOTS = 75


def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            return default
        return value
    except Exception:
        return default


def safe_text(value, default=""):
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass
    value = str(value).strip()
    return value if value else default


def normalize_symbol(series):
    return series.astype(str).str.upper().str.strip()


def parse_snapshot_date(folder_name):
    try:
        return datetime.strptime(folder_name, "%Y-%m-%d").date()
    except Exception:
        return None


def horizon_bucket(days):
    days = int(days)
    if days <= 2:
        return "1D"
    if days <= 5:
        return "3D"
    if days <= 10:
        return "7D"
    if days <= 20:
        return "15D"
    if days <= 45:
        return "30D"
    return "60D+"


def load_latest_scan():
    if not LATEST_SCAN_FILE.exists():
        raise FileNotFoundError("data/scans/latest_scan.csv not found.")

    latest_df = pd.read_csv(LATEST_SCAN_FILE)

    if latest_df.empty or "symbol" not in latest_df.columns:
        raise RuntimeError("latest_scan.csv is empty or missing symbol column.")

    latest_df["symbol"] = normalize_symbol(latest_df["symbol"])

    numeric_cols = [
        "current_price", "final_conviction_score", "technical_score",
        "fundamental_score", "active_fundamental_score",
        "relative_strength_score", "risk_penalty", "rsi",
        "range_score", "current_position_pct"
    ]

    for col in numeric_cols:
        if col not in latest_df.columns:
            latest_df[col] = 0
        latest_df[col] = pd.to_numeric(latest_df[col], errors="coerce").fillna(0)

    text_cols = ["sector", "industry", "sector_bucket", "score_band", "range_status", "trend"]

    for col in text_cols:
        if col not in latest_df.columns:
            latest_df[col] = ""
        latest_df[col] = latest_df[col].fillna("").astype(str)

    if "active_fundamental_score" not in latest_df.columns or latest_df["active_fundamental_score"].sum() == 0:
        latest_df["active_fundamental_score"] = latest_df.get("fundamental_score", 0)

    return latest_df.drop_duplicates(subset=["symbol"])


def prepare_snapshot(df):
    if df.empty or "symbol" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["symbol"] = normalize_symbol(df["symbol"])

    numeric_cols = [
        "current_price", "final_conviction_score", "technical_score",
        "fundamental_score", "active_fundamental_score",
        "relative_strength_score", "risk_penalty", "rsi",
        "distance_pct", "distance_from_high_pct", "volume_ratio",
        "range_score", "current_position_pct"
    ]

    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    text_cols = ["sector", "industry", "sector_bucket", "score_band", "trend", "range_status"]

    for col in text_cols:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)

    if "active_fundamental_score" not in df.columns or df["active_fundamental_score"].sum() == 0:
        df["active_fundamental_score"] = df.get("fundamental_score", 0)

    return df.drop_duplicates(subset=["symbol"])


def add_signal(signals, row, signal_type, signal_direction, signal_strength="Normal"):
    signals.append({
        "signal_type": signal_type,
        "signal_direction": signal_direction,
        "signal_strength": signal_strength,
        "symbol": row.get("symbol", ""),
        "sector": row.get("sector", ""),
        "industry": row.get("industry", ""),
        "sector_bucket": row.get("sector_bucket", ""),
        "entry_price": safe_float(row.get("current_price")),
        "entry_final_score": safe_float(row.get("final_conviction_score")),
        "entry_technical_score": safe_float(row.get("technical_score")),
        "entry_fundamental_score": safe_float(row.get("fundamental_score")),
        "entry_active_fundamental_score": safe_float(row.get("active_fundamental_score")),
        "entry_relative_strength_score": safe_float(row.get("relative_strength_score")),
        "entry_risk_penalty": safe_float(row.get("risk_penalty")),
        "entry_rsi": safe_float(row.get("rsi")),
        "entry_score_band": row.get("score_band", ""),
        "entry_range_status": row.get("range_status", ""),
        "entry_range_score": safe_float(row.get("range_score")),
        "entry_current_position_pct": safe_float(row.get("current_position_pct")),
    })


def detect_signals(snapshot_df):
    signals = []
    if snapshot_df.empty:
        return signals

    df = snapshot_df.copy()

    top_df = df.sort_values("final_conviction_score", ascending=False).head(25)
    for _, row in top_df.iterrows():
        add_signal(signals, row, "Top Final Conviction", "Bullish", "High")

    for _, row in df.iterrows():
        final_score = safe_float(row.get("final_conviction_score"))
        active_fund = safe_float(row.get("active_fundamental_score"))
        relative_strength = safe_float(row.get("relative_strength_score"))
        risk = safe_float(row.get("risk_penalty"))
        rsi = safe_float(row.get("rsi"))
        distance_low = safe_float(row.get("distance_pct"))
        distance_high = safe_float(row.get("distance_from_high_pct"))
        volume_ratio = safe_float(row.get("volume_ratio"))
        trend = safe_text(row.get("trend")).lower()
        score_band = safe_text(row.get("score_band"))
        range_status = safe_text(row.get("range_status"))

        if final_score >= 65:
            add_signal(signals, row, "High Conviction", "Bullish", "High")
        if distance_low <= 15:
            add_signal(signals, row, "52W Low Opportunity", "Bullish", "Normal")
        if distance_low <= 25 and rsi <= 45 and volume_ratio >= 1.0:
            add_signal(signals, row, "Swing Candidate", "Bullish", "Normal")
        if distance_high <= 15 and rsi >= 50 and trend == "bullish":
            add_signal(signals, row, "Near 52W High Momentum", "Bullish", "Normal")
        if active_fund >= 60:
            add_signal(signals, row, "Strong Fundamentals", "Bullish", "Normal")
        if relative_strength >= 60:
            add_signal(signals, row, "Relative Strength Leader", "Bullish", "Normal")
        if risk <= 10 and final_score >= 50 and active_fund >= 50:
            add_signal(signals, row, "Low Risk Quality", "Bullish", "Normal")
        if range_status in ["Accumulation Zone", "Lower Range Watch"]:
            add_signal(signals, row, "Range Accumulation Zone", "Bullish", "Normal")
        if range_status == "Profit Booking Zone":
            add_signal(signals, row, "Range Profit Booking Zone", "Bearish", "Normal")
        if range_status == "Range Breakdown Risk":
            add_signal(signals, row, "Range Breakdown Risk", "Bearish", "High")
        if score_band == "E Avoid" or final_score < 35 or risk >= 25 or (active_fund < 30 and relative_strength < 40):
            add_signal(signals, row, "Avoid / Risky", "Bearish", "High")

    return signals


def classify_result(signal_direction, return_pct):
    return_pct = safe_float(return_pct)
    if signal_direction == "Bullish":
        if return_pct >= 2:
            return "Working"
        if return_pct <= -2:
            return "Failing"
        return "Neutral"
    if signal_direction == "Bearish":
        if return_pct <= -2:
            return "Correct Warning"
        if return_pct >= 2:
            return "False Warning"
        return "Neutral"
    return "Neutral"


def is_success(signal_direction, return_pct):
    return_pct = safe_float(return_pct)
    if signal_direction == "Bullish":
        return return_pct > 0
    if signal_direction == "Bearish":
        return return_pct < 0
    return False


def find_history_files():
    if not HISTORY_ROOT.exists():
        return []

    files = []
    for folder in HISTORY_ROOT.iterdir():
        if not folder.is_dir():
            continue
        snapshot_date = parse_snapshot_date(folder.name)
        if snapshot_date is None:
            continue
        file_path = folder / "latest_scan.csv"
        if file_path.exists():
            files.append((snapshot_date, file_path))

    return sorted(files, key=lambda x: x[0], reverse=True)[:MAX_HISTORY_SNAPSHOTS]


def build_performance():
    latest_df = load_latest_scan()
    latest_lookup = latest_df.set_index("symbol").to_dict(orient="index")
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    rows = []
    history_files = find_history_files()

    print(f"History snapshots found: {len(history_files)}")

    for snapshot_date, file_path in history_files:
        days_passed = (today - snapshot_date).days
        if days_passed <= 0:
            continue

        try:
            snapshot_df = pd.read_csv(file_path)
        except Exception as e:
            print(f"Could not read {file_path}: {e}")
            continue

        snapshot_df = prepare_snapshot(snapshot_df)
        if snapshot_df.empty:
            continue

        for signal in detect_signals(snapshot_df):
            symbol = signal["symbol"]
            latest_row = latest_lookup.get(symbol)
            if latest_row is None:
                continue

            entry_price = safe_float(signal.get("entry_price"))
            latest_price = safe_float(latest_row.get("current_price"))
            if entry_price <= 0 or latest_price <= 0:
                continue

            return_pct = ((latest_price - entry_price) / entry_price) * 100
            direction = signal.get("signal_direction", "Bullish")

            rows.append({
                "performance_scan_time": PERFORMANCE_SCAN_TIME,
                "signal_date": snapshot_date.strftime("%Y-%m-%d"),
                "days_passed": int(days_passed),
                "horizon_bucket": horizon_bucket(days_passed),
                "symbol": symbol,
                "sector": signal.get("sector", ""),
                "industry": signal.get("industry", ""),
                "sector_bucket": signal.get("sector_bucket", ""),
                "signal_type": signal.get("signal_type", ""),
                "signal_direction": direction,
                "signal_strength": signal.get("signal_strength", ""),
                "entry_price": round(entry_price, 2),
                "latest_price": round(latest_price, 2),
                "return_pct": round(return_pct, 2),
                "is_success": bool(is_success(direction, return_pct)),
                "result_status": classify_result(direction, return_pct),
                "entry_final_score": round(safe_float(signal.get("entry_final_score")), 2),
                "latest_final_score": round(safe_float(latest_row.get("final_conviction_score")), 2),
                "entry_technical_score": round(safe_float(signal.get("entry_technical_score")), 2),
                "latest_technical_score": round(safe_float(latest_row.get("technical_score")), 2),
                "entry_fundamental_score": round(safe_float(signal.get("entry_fundamental_score")), 2),
                "latest_fundamental_score": round(safe_float(latest_row.get("fundamental_score")), 2),
                "entry_active_fundamental_score": round(safe_float(signal.get("entry_active_fundamental_score")), 2),
                "latest_active_fundamental_score": round(safe_float(latest_row.get("active_fundamental_score")), 2),
                "entry_relative_strength_score": round(safe_float(signal.get("entry_relative_strength_score")), 2),
                "latest_relative_strength_score": round(safe_float(latest_row.get("relative_strength_score")), 2),
                "entry_risk_penalty": round(safe_float(signal.get("entry_risk_penalty")), 2),
                "latest_risk_penalty": round(safe_float(latest_row.get("risk_penalty")), 2),
                "entry_rsi": round(safe_float(signal.get("entry_rsi")), 2),
                "latest_rsi": round(safe_float(latest_row.get("rsi")), 2),
                "entry_score_band": signal.get("entry_score_band", ""),
                "latest_score_band": latest_row.get("score_band", ""),
                "entry_range_status": signal.get("entry_range_status", ""),
                "latest_range_status": latest_row.get("range_status", ""),
                "entry_range_score": round(safe_float(signal.get("entry_range_score")), 2),
                "latest_range_score": round(safe_float(latest_row.get("range_score")), 2),
                "entry_current_position_pct": round(safe_float(signal.get("entry_current_position_pct")), 2),
                "latest_current_position_pct": round(safe_float(latest_row.get("current_position_pct")), 2),
            })

    performance_df = pd.DataFrame(rows)

    if performance_df.empty:
        performance_df = pd.DataFrame(columns=[
            "performance_scan_time", "signal_date", "days_passed", "horizon_bucket", "symbol",
            "sector", "industry", "sector_bucket", "signal_type", "signal_direction",
            "entry_price", "latest_price", "return_pct", "is_success", "result_status"
        ])

    performance_df = performance_df.drop_duplicates(
        subset=["signal_date", "symbol", "signal_type"],
        keep="last"
    )

    performance_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Signal performance saved: {len(performance_df)} rows")

    if performance_df.empty:
        pd.DataFrame().to_csv(SUMMARY_FILE, index=False)
        return

    summary = (
        performance_df.groupby(["signal_type", "horizon_bucket"])
        .agg(
            signals=("symbol", "count"),
            win_rate=("is_success", "mean"),
            avg_return=("return_pct", "mean"),
            median_return=("return_pct", "median"),
            best_return=("return_pct", "max"),
            worst_return=("return_pct", "min"),
        )
        .reset_index()
    )

    summary["win_rate"] = (summary["win_rate"] * 100).round(2)
    for col in ["avg_return", "median_return", "best_return", "worst_return"]:
        summary[col] = summary[col].round(2)

    summary.to_csv(SUMMARY_FILE, index=False)
    print(f"Signal performance summary saved: {len(summary)} rows")


if __name__ == "__main__":
    build_performance()
