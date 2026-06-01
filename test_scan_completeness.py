import pandas as pd
from pathlib import Path
import subprocess
import sys

scan_file = Path("data/scans/latest_scan.csv")
assert scan_file.exists(), "latest_scan.csv missing"

subprocess.run(
    [sys.executable, "app/data_quality/repair_scan_completeness.py"],
    check=True,
)

df = pd.read_csv(scan_file, low_memory=False)
assert "data_completeness_status" in df.columns
assert "fundamental_data_status" in df.columns
assert "sector_data_status" in df.columns
assert "data_confidence_score" in df.columns
assert "final_conviction_score_source" in df.columns
assert "data_quality_note" in df.columns

if "RECLTD" in set(df["symbol"].astype(str).str.upper()):
    row = df[df["symbol"].astype(str).str.upper() == "RECLTD"].iloc[0]

    assert str(row.get("sector", "")).strip().lower() not in ["", "nan", "unknown"], row.to_dict()
    assert str(row.get("industry", "")).strip().lower() not in ["", "nan", "unknown"], row.to_dict()
    assert str(row.get("company_name", "")).strip().lower() not in ["", "nan", "unknown"], row.to_dict()

    range_score = float(row.get("range_score", 0) or 0)
    final_score = float(row.get("final_conviction_score", 0) or 0)

    if range_score > 0:
        assert final_score > 0, row.to_dict()

print("✅ Scan completeness tests passed")
