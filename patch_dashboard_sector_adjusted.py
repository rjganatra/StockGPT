from pathlib import Path
import shutil

DASHBOARD = Path("app/dashboard/dashboard.py")

if not DASHBOARD.exists():
    raise FileNotFoundError("app/dashboard/dashboard.py not found. Run this from your repo root.")

backup = DASHBOARD.with_suffix(".py.bak_sector_adjusted")
shutil.copy2(DASHBOARD, backup)

text = DASHBOARD.read_text(encoding="utf-8")


def replace_once(old, new, label):
    global text
    if old in text:
        text = text.replace(old, new, 1)
        print(f"✅ {label}")
    else:
        print(f"⚠️ Not found / already patched: {label}")


# 1) sector_bucket should default to Unknown, not 0
replace_once(
'''for col in optional_cols:
    if col not in df.columns:
        df[col] = "Unknown" if col == "score_band" else 0''',
'''for col in optional_cols:
    if col not in df.columns:
        df[col] = "Unknown" if col in ["score_band", "sector_bucket"] else 0''',
"sector_bucket default"
)

# 2) Strong Fundamentals should use active score
replace_once(
'''elif preset == "Strong Fundamentals":
    filtered = filtered[filtered["fundamental_score"] >= 60]''',
'''elif preset == "Strong Fundamentals":
    filtered = filtered[filtered["active_fundamental_score"] >= 60]''',
"Strong Fundamentals uses active_fundamental_score"
)

# 3) Add new presets
replace_once(
'''        "Strong Fundamentals",
        "Relative Strength Leaders",''',
'''        "Strong Fundamentals",
        "Sector-Adjusted Quality",
        "Relative Strength Leaders",''',
"Add Sector-Adjusted Quality preset"
)

replace_once(
'''        "Fresh Breakdown Risk"
    ],''',
'''        "Fresh Breakdown Risk",
        "Avoid / Risky"
    ],''',
"Add Avoid / Risky preset"
)

replace_once(
'''elif preset == "Relative Strength Leaders":
    filtered = filtered[filtered["relative_strength_score"] >= 60]''',
'''elif preset == "Sector-Adjusted Quality":
    filtered = filtered[
        (filtered["sector_adjusted_fundamental_score"] >= 60)
        &
        (filtered["sector_fundamental_adjustment"] >= 0)
    ]

elif preset == "Relative Strength Leaders":
    filtered = filtered[filtered["relative_strength_score"] >= 60]''',
"Sector-Adjusted Quality logic"
)

replace_once(
'''elif preset == "Fresh Breakdown Risk":
    filtered = filtered[(filtered["trend"] == "Bearish") & (filtered["rsi"] < 40) & (filtered["day_change_pct"] < 0)]''',
'''elif preset == "Fresh Breakdown Risk":
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
    ]''',
"Avoid / Risky logic"
)

# 4) Low Risk Quality should use active_fundamental_score
replace_once(
'''elif preset == "Low Risk Quality":
    filtered = filtered[(filtered["risk_penalty"] <= 10) & (filtered["final_conviction_score"] >= 50)]''',
'''elif preset == "Low Risk Quality":
    filtered = filtered[
        (filtered["risk_penalty"] <= 10)
        &
        (filtered["active_fundamental_score"] >= 55)
        &
        (filtered["final_conviction_score"] >= 50)
    ]''',
"Low Risk Quality uses active_fundamental_score"
)

# 5) Sorting options
replace_once(
'''        "fundamental_score",
        "relative_strength_score",''',
'''        "fundamental_score",
        "sector_adjusted_fundamental_score",
        "active_fundamental_score",
        "sector_fundamental_adjustment",
        "relative_strength_score",''',
"Sort menu adjusted score columns"
)

# 6) Market overview signal tables
replace_once(
'''"symbol", "sector", "industry", "current_price", "score_band", "final_conviction_score", "fundamental_score", "relative_strength_score", "risk_penalty"''',
'''"symbol", "sector", "industry", "sector_bucket", "current_price", "score_band", "final_conviction_score", "active_fundamental_score", "sector_fundamental_adjustment", "relative_strength_score", "risk_penalty"''',
"Top Final Conviction table"
)

replace_once(
'''        st.markdown("**52W Low + Strong Fundamentals**")
        low_quality = df[
            (df["distance_pct"] <= 20)
            &
            (df["fundamental_score"] >= 55)
        ].sort_values("final_conviction_score", ascending=False).head(10)
        display_table(
            low_quality,
            ["symbol", "sector", "industry", "current_price", "distance_pct", "fundamental_score", "final_conviction_score", "score_band"]
        )''',
'''        st.markdown("**52W Low + Sector-Adjusted Quality**")
        low_quality = df[
            (df["distance_pct"] <= 20)
            &
            (df["active_fundamental_score"] >= 55)
        ].sort_values("final_conviction_score", ascending=False).head(10)
        display_table(
            low_quality,
            ["symbol", "sector", "industry", "sector_bucket", "current_price", "distance_pct", "fundamental_score", "sector_fundamental_adjustment", "sector_adjusted_fundamental_score", "active_fundamental_score", "final_conviction_score", "score_band"]
        )''',
"52W Low signal uses active score"
)

replace_once(
'''        st.markdown("**High Fundamentals + Low Risk**")
        quality_low_risk = df[
            (df["fundamental_score"] >= 60)
            &
            (df["risk_penalty"] <= 10)
        ].sort_values("final_conviction_score", ascending=False).head(10)
        display_table(
            quality_low_risk,
            ["symbol", "sector", "industry", "fundamental_score", "risk_penalty", "final_conviction_score", "score_band"]
        )''',
'''        st.markdown("**High Sector-Adjusted Quality + Low Risk**")
        quality_low_risk = df[
            (df["active_fundamental_score"] >= 60)
            &
            (df["risk_penalty"] <= 10)
        ].sort_values("final_conviction_score", ascending=False).head(10)
        display_table(
            quality_low_risk,
            ["symbol", "sector", "industry", "sector_bucket", "fundamental_score", "sector_fundamental_adjustment", "active_fundamental_score", "risk_penalty", "final_conviction_score", "score_band"]
        )''',
"Quality low risk signal uses active score"
)

# 7) Opportunity tab low table
replace_once(
'''["symbol", "sector", "industry", "current_price", "day_change_pct", "52w_low", "distance_pct", "rsi", "volume_ratio", "fundamental_score", "final_conviction_score", "score_band", "reasons"]''',
'''["symbol", "sector", "industry", "sector_bucket", "current_price", "day_change_pct", "52w_low", "distance_pct", "rsi", "volume_ratio", "fundamental_score", "sector_fundamental_adjustment", "sector_adjusted_fundamental_score", "active_fundamental_score", "relative_strength_score", "final_conviction_score", "score_band", "reasons"]''',
"52W Low Opportunities columns"
)

# 8) Sector/industry aggregates
replace_once(
'''        avg_fundamental=("fundamental_score", "mean"),
        avg_relative_strength=("relative_strength_score", "mean"),''',
'''        avg_raw_fundamental=("fundamental_score", "mean"),
        avg_sector_adjusted_fundamental=("sector_adjusted_fundamental_score", "mean"),
        avg_active_fundamental=("active_fundamental_score", "mean"),
        avg_sector_fundamental_adjustment=("sector_fundamental_adjustment", "mean"),
        avg_relative_strength=("relative_strength_score", "mean"),''',
"Sector aggregate adjusted fundamentals"
)

replace_once(
'''        avg_fundamental=("fundamental_score", "mean"),
        avg_relative_strength=("relative_strength_score", "mean"),
        avg_risk_penalty=("risk_penalty", "mean"),''',
'''        avg_raw_fundamental=("fundamental_score", "mean"),
        avg_sector_adjusted_fundamental=("sector_adjusted_fundamental_score", "mean"),
        avg_active_fundamental=("active_fundamental_score", "mean"),
        avg_sector_fundamental_adjustment=("sector_fundamental_adjustment", "mean"),
        avg_relative_strength=("relative_strength_score", "mean"),
        avg_risk_penalty=("risk_penalty", "mean"),''',
"Industry aggregate adjusted fundamentals"
)

# 9) Fundamentals tab dashboard merge
replace_once(
'''            dashboard_cols = [
                "symbol", "sector", "industry", "current_price", "rsi",
                "technical_score", "relative_strength_score", "sector_score",
                "risk_penalty", "final_conviction_score", "score_band"
            ]''',
'''            dashboard_cols = [
                "symbol", "sector", "industry", "current_price", "rsi",
                "technical_score", "fundamental_score", "sector_bucket",
                "sector_fundamental_adjustment", "sector_adjusted_fundamental_score",
                "active_fundamental_score", "relative_strength_score", "sector_score",
                "risk_penalty", "final_conviction_score", "score_band"
            ]''',
"Fundamentals tab merge columns"
)

# 10) Add adjusted score sliders in fundamentals tab
replace_once(
'''            filtered_fundamentals = fundamentals_view.copy()

            if selected_fund_sectors:''',
'''            adjusted_fs_min, adjusted_fs_max = safe_range_slider(
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

            if selected_fund_sectors:''',
"Fundamentals tab adjusted sliders"
)

replace_once(
'''            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["fundamental_score"].between(fs_min, fs_max)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["roe"].between(roe_min2, roe_max2)]''',
'''            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["fundamental_score"].between(fs_min, fs_max)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["sector_adjusted_fundamental_score"].between(adjusted_fs_min, adjusted_fs_max)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["active_fundamental_score"].between(active_fs_min, active_fs_max)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["sector_fundamental_adjustment"].between(sector_adj_min, sector_adj_max)]
            filtered_fundamentals = filtered_fundamentals[filtered_fundamentals["roe"].between(roe_min2, roe_max2)]''',
"Fundamentals tab apply adjusted sliders"
)

replace_once(
'''            st.subheader("Fundamental Quality Table")
            display_table(filtered_fundamentals.sort_values("fundamental_score", ascending=False), display_cols)

            st.subheader("Top Fundamental Companies")
            display_table(filtered_fundamentals.sort_values("fundamental_score", ascending=False).head(25), display_cols)''',
'''            st.subheader("Fundamental Quality Table")
            display_table(filtered_fundamentals.sort_values("active_fundamental_score", ascending=False), display_cols)

            st.subheader("Top Sector-Adjusted Fundamental Companies")
            display_table(filtered_fundamentals.sort_values("sector_adjusted_fundamental_score", ascending=False).head(25), display_cols)''',
"Fundamentals tab sorting adjusted"
)

# 11) Add Avoid/Risky signal in market overview
if "**Avoid / Risky Watch**" not in text:
    replace_once(
'''        display_table(
            volume_breakouts,
            ["symbol", "sector", "industry", "volume_ratio", "rsi", "final_conviction_score", "score_band"]
        )''',
'''        display_table(
            volume_breakouts,
            ["symbol", "sector", "industry", "volume_ratio", "rsi", "active_fundamental_score", "final_conviction_score", "score_band"]
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
            ["symbol", "sector", "industry", "sector_bucket", "final_conviction_score", "active_fundamental_score", "relative_strength_score", "risk_penalty", "score_band", "risk_reasons"]
        )''',
"Avoid/Risky signal table"
    )
else:
    print("⚠️ Already patched: Avoid/Risky signal table")

DASHBOARD.write_text(text, encoding="utf-8")

print("")
print(f"✅ Dashboard patched: {DASHBOARD}")
print(f"✅ Backup created: {backup}")
print("")
print("Run this to check syntax:")
print("python -m py_compile app/dashboard/dashboard.py")
