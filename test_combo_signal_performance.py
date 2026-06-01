import subprocess
import sys
from pathlib import Path
import pandas as pd

subprocess.run([sys.executable, "app/performance/combo_signal_performance.py"], check=True)

summary_file = Path("data/performance/combo_signal_performance.csv")
members_file = Path("data/performance/combo_signal_members.csv")

assert summary_file.exists(), "combo summary missing"
assert members_file.exists(), "combo members missing"

summary = pd.read_csv(summary_file)
assert not summary.empty, "combo summary empty"

required = [
    "combo_id",
    "combo_name",
    "description",
    "current_matches",
    "avg_final_conviction",
    "avg_range_score",
    "positive_1m_rate",
    "positive_3m_rate",
    "top_symbols",
    "interpretation",
]

for col in required:
    assert col in summary.columns, f"missing {col}"

expected_combos = [
    "52w_low_bearish_strong_rsi",
    "range_accumulation_low_risk",
    "high_conviction_quality",
    "fallback_range_opportunity",
]

for combo in expected_combos:
    assert combo in set(summary["combo_id"]), f"missing combo {combo}"

print("✅ Combo signal performance tests passed")
