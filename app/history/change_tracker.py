import pandas as pd
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

LATEST_SCAN_FILE = Path("data/scans/latest_scan.csv")
HISTORY_ROOT = Path("data/history")
OUTPUT_FILE = Path("data/history/latest_changes.csv")


def safe_num(value, default=0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def clean_scan(df):
    df = df.copy()

    df["symbol"] = (
        df["symbol"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    text_cols = [
        "sector",
        "industry",
        "trend",
        "score_band",
        "reasons"
    ]

    for col in text_cols:
        if col not in df.columns:
            df[col] = "Unknown"

        df[col] = df[col].fillna("Unknown").astype(str)

    numeric_cols = [
        "current_price",
        "day_change_pct",
        "distance_pct",
        "distance_from_high_pct",
        "rsi",
        "volume_ratio",
        "technical_score",
        "fundamental_score",
        "relative_strength_score",
        "sector_score",
        "risk_penalty",
        "final_conviction_score",
        "return_1m",
        "return_3m",
        "return_6m"
    ]

    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    if "score_band" not in df.columns:
        df["score_band"] = "Unknown"

    return df


def get_previous_history_file():
    if not HISTORY_ROOT.exists:
        return None

    if not HISTORY_ROOT.exists():
        return None

    folders = sorted(
        [
            p for p in HISTORY_ROOT.iterdir()
            if p.is_dir()
        ],
        reverse=True
    )

    valid_files = []

    for folder in folders:
        file_path = folder / "latest_scan.csv"

        if file_path.exists():
            valid_files.append(file_path)

    if not valid_files:
        return None

    # If latest history is same as current run, use second latest if available.
    if len(valid_files) >= 2:
        return valid_files[1]

    return valid_files[0]


def build_change_signal(row):
    signals = []

    score_change = safe_num(row.get("score_change"))
    rsi_change = safe_num(row.get("rsi_change"))
    risk_change = safe_num(row.get("risk_change"))
    current_score = safe_num(row.get("current_final_score"))
    previous_score = safe_num(row.get("previous_final_score"))
    current_rsi = safe_num(row.get("current_rsi"))
    previous_rsi = safe_num(row.get("previous_rsi"))
    current_risk = safe_num(row.get("current_risk"))
    previous_risk = safe_num(row.get("previous_risk"))

    previous_band = str(row.get("previous_score_band", "Unknown"))
    current_band = str(row.get("current_score_band", "Unknown"))

    if previous_score < 65 and current_score >= 65:
        signals.append("Entered Strong Zone")

    if previous_score < 75 and current_score >= 75:
        signals.append("New High Conviction")

    if previous_score >= 65 and current_score < 65:
        signals.append("Dropped Below Strong Zone")

    if previous_score >= 75 and current_score < 75:
        signals.append("Lost High Conviction")

    if score_change >= 10:
        signals.append("Score Improved Sharply")
    elif score_change >= 5:
        signals.append("Score Improved")

    if score_change <= -10:
        signals.append("Score Dropped Sharply")
    elif score_change <= -5:
        signals.append("Score Dropped")

    if previous_rsi < 45 and current_rsi >= 50:
        signals.append("RSI Recovery")

    if previous_rsi < 60 and current_rsi >= 60:
        signals.append("Fresh Momentum")

    if previous_rsi <= 70 and current_rsi > 70:
        signals.append("RSI Overbought")

    if previous_rsi >= 40 and current_rsi < 40:
        signals.append("Fresh Weakness")

    if risk_change >= 10:
        signals.append("Risk Increased Sharply")
    elif risk_change >= 5:
        signals.append("Risk Increased")

    if risk_change <= -10:
        signals.append("Risk Reduced Sharply")
    elif risk_change <= -5:
        signals.append("Risk Reduced")

    if current_risk >= 25 and previous_risk < 25:
        signals.append("New Risk Warning")

    if current_band != previous_band:
        signals.append(f"Band Changed: {previous_band} → {current_band}")

    if not signals:
        signals.append("No Major Change")

    return ", ".join(signals)


def main():
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if not LATEST_SCAN_FILE.exists():
        raise FileNotFoundError("latest_scan.csv not found")

    previous_file = get_previous_history_file()

    if previous_file is None:
        print("No previous history file found. Creating empty latest_changes.csv.")

        empty_df = pd.DataFrame(
            columns=[
                "change_scan_time",
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

        empty_df.to_csv(
            OUTPUT_FILE,
            index=False
        )

        return

    current_df = pd.read_csv(LATEST_SCAN_FILE)
    previous_df = pd.read_csv(previous_file)

    current_df = clean_scan(current_df)
    previous_df = clean_scan(previous_df)

    current_cols = [
        "symbol",
        "sector",
        "industry",
        "current_price",
        "rsi",
        "risk_penalty",
        "final_conviction_score",
        "score_band",
        "technical_score",
        "fundamental_score",
        "relative_strength_score",
        "volume_ratio",
        "distance_pct",
        "distance_from_high_pct",
        "trend"
    ]

    previous_cols = [
        "symbol",
        "rsi",
        "risk_penalty",
        "final_conviction_score",
        "score_band"
    ]

    current_cols = [
        col for col in current_cols
        if col in current_df.columns
    ]

    previous_cols = [
        col for col in previous_cols
        if col in previous_df.columns
    ]

    current_view = current_df[current_cols].copy()
    previous_view = previous_df[previous_cols].copy()

    previous_view = previous_view.rename(
        columns={
            "rsi": "previous_rsi",
            "risk_penalty": "previous_risk",
            "final_conviction_score": "previous_final_score",
            "score_band": "previous_score_band"
        }
    )

    current_view = current_view.rename(
        columns={
            "rsi": "current_rsi",
            "risk_penalty": "current_risk",
            "final_conviction_score": "current_final_score",
            "score_band": "current_score_band"
        }
    )

    changes = current_view.merge(
        previous_view,
        on="symbol",
        how="left"
    )

    changes["previous_final_score"] = pd.to_numeric(
        changes["previous_final_score"],
        errors="coerce"
    ).fillna(0)

    changes["current_final_score"] = pd.to_numeric(
        changes["current_final_score"],
        errors="coerce"
    ).fillna(0)

    changes["previous_rsi"] = pd.to_numeric(
        changes["previous_rsi"],
        errors="coerce"
    ).fillna(0)

    changes["current_rsi"] = pd.to_numeric(
        changes["current_rsi"],
        errors="coerce"
    ).fillna(0)

    changes["previous_risk"] = pd.to_numeric(
        changes["previous_risk"],
        errors="coerce"
    ).fillna(0)

    changes["current_risk"] = pd.to_numeric(
        changes["current_risk"],
        errors="coerce"
    ).fillna(0)

    changes["previous_score_band"] = changes["previous_score_band"].fillna("New Stock")
    changes["current_score_band"] = changes["current_score_band"].fillna("Unknown")

    changes["score_change"] = (
        changes["current_final_score"]
        -
        changes["previous_final_score"]
    ).round(2)

    changes["rsi_change"] = (
        changes["current_rsi"]
        -
        changes["previous_rsi"]
    ).round(2)

    changes["risk_change"] = (
        changes["current_risk"]
        -
        changes["previous_risk"]
    ).round(2)

    changes["change_signal"] = changes.apply(
        build_change_signal,
        axis=1
    )

    change_scan_time = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%d.%m.%Y at %I:%M %p IST")

    changes.insert(
        0,
        "change_scan_time",
        change_scan_time
    )

    changes = changes.sort_values(
        [
            "score_change",
            "current_final_score"
        ],
        ascending=[False, False]
    )

    changes.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(f"Change tracker saved: {len(changes)} rows")
    print(f"Compared against: {previous_file}")


if __name__ == "__main__":
    main()
