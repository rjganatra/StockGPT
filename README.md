# 📈 StockGPT — NSE Market Intelligence Terminal

<img width="1254" height="1254" alt="image" src="https://github.com/user-attachments/assets/8160aae8-31f4-4867-a9e0-1f2ca8856e5e" />


StockGPT is a Streamlit-based market intelligence dashboard built for scanning Indian equities, identifying technical opportunities, evaluating fundamental quality, tracking relative strength, monitoring sectors/industries, and maintaining a permanent watchlist.

The system is designed around a broad NSE universe rather than only NIFTY 50 / NIFTY 500, so important mid-cap and small-cap opportunities are not missed.

---

## 🚀 What StockGPT Does

StockGPT scans Indian listed stocks and creates a multi-factor dashboard covering:

- Broad NSE stock universe
- 52-week low opportunity detection
- Near 52-week high momentum detection
- Swing candidate filtering
- Technical strength scoring
- Fundamental quality scoring
- Relative strength scoring
- Sector and industry strength analysis
- Risk penalty scoring
- Final conviction score
- Permanent GitHub-backed watchlist
- Historical scan snapshots
- Streamlit dashboard filters and query tools

---

## 🧠 Core Philosophy

StockGPT started as a 52-week-low opportunity scanner, but it is now evolving into a broader multi-factor stock intelligence system.

The goal is not to blindly recommend stocks based on one signal. Instead, the system combines:

```text
Technical Score
+ Fundamental Score
+ Relative Strength Score
+ Sector Score
- Risk Penalty
= Final Conviction Score
```

This helps avoid over-dependence on only one strategy such as 52-week low, RSI, or momentum.

---

## 🗂️ Project Structure

```text
StockGPT/
│
├── app/
│   ├── dashboard/
│   │   └── dashboard.py
│   ├── scanners/
│   │   └── scan_52w.py
│   ├── universe/
│   │   ├── fetch_nifty500.py
│   │   └── enrich_sectors.py
│   ├── fundamentals/
│   │   ├── fetch_fundamentals.py
│   │   └── fundamental_score.py
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── relative_strength.py
│   │   └── score_engine.py
│   ├── history/
│   │   └── history_engine.py
│   └── database/
│       └── store_scan.py
│
├── data/
│   ├── universe/
│   │   ├── universe.csv
│   │   └── sector_industry_map.csv
│   ├── scans/
│   │   ├── latest_scan.csv
│   │   └── failed_symbols.csv
│   ├── fundamentals/
│   │   ├── fundamentals.csv
│   │   ├── fundamental_scores.csv
│   │   └── failed_fundamentals.csv
│   ├── scoring/
│   │   └── relative_strength.csv
│   ├── history/
│   │   └── YYYY-MM-DD/latest_scan.csv
│   ├── database/
│   │   └── stockgpt.db
│   └── watchlist/
│       └── watchlist.csv
│
├── .github/workflows/
│   ├── phase6_pipeline.yml
│   └── weekly_fundamentals.yml
│
├── requirements.txt
└── README.md
```

---

## 🔁 Main Data Pipeline

The main scan pipeline runs through GitHub Actions.

Recommended order:

```text
1. Refresh Universe
2. Run Technical Scanner
3. Enrich Sector and Industry Data
4. Calculate Relative Strength
5. Run Final Score Engine
6. Save Historical Snapshot
7. Store Scan in SQLite Database
8. Commit and Push Updated Data
```

Workflow file:

```text
.github/workflows/phase6_pipeline.yml
```

---

## 🧾 Weekly Fundamentals Pipeline

Fundamental data is heavier and slower to fetch, so it runs separately.

Workflow file:

```text
.github/workflows/weekly_fundamentals.yml
```

Recommended order:

```text
1. Fetch Fundamentals
2. Score Fundamentals
3. Enrich Sector / Industry Map
4. Run Final Score Engine
5. Store Scan in Database
6. Commit and Push Updated Data
```

---

## 📊 Dashboard Tabs

Dashboard file:

```text
app/dashboard/dashboard.py
```

### 1. Market Overview

Shows:

- Stocks scanned
- Filtered stocks
- Near 52-week-low count
- Average RSI
- Bullish / bearish count
- Average final conviction score
- Average technical score
- Average fundamental score
- Average relative strength
- Average risk penalty
- Market table with readable market cap in ₹ crore

### 2. Heatmap

Two heatmaps are available:

#### Opportunity Heatmap

```text
Sector → Industry → Stock
```

Color logic:

```text
Green = Higher Final Conviction Score
Red = Lower Final Conviction Score
```

#### Daily Movement Heatmap

```text
Sector → Industry → Stock
```

Color logic:

```text
Green = Stock up today
Red = Stock down today
```

### 3. Opportunities

Opportunity baskets:

#### 🎯 52W Low Opportunities

```text
distance_pct <= 15
```

#### ⚡ Swing Candidates

```text
distance_pct <= 25
RSI <= 45
volume_ratio >= 1.0
```

#### 🚀 Near 52W High Momentum

```text
distance_from_high_pct <= 15
RSI >= 50
trend == Bullish
```

Each opportunity basket supports adding stocks to the permanent watchlist.

### 4. Sectors

Shows:

- Sector overview
- Industry overview
- Sector average final conviction
- Sector average technical score
- Sector average fundamental score
- Sector average relative strength
- Average risk penalty
- Average RSI
- 1M / 3M / 6M returns
- Bullish percentage
- Industry heatmap
- Top industries by final conviction

### 5. Stock Explorer

Allows deep-dive into any stock from the latest scan.

Shows:

- Current price
- Final conviction score
- RSI
- Risk penalty
- Technical score
- Fundamental score
- Relative strength score
- Sector score
- Full stock details
- Technical reasons
- Fundamental reasons
- Relative strength reasons
- Risk reasons
- Add-to-watchlist option

### 6. History

Shows historical snapshots stored under:

```text
data/history/YYYY-MM-DD/latest_scan.csv
```

### 7. Watchlist

Permanent watchlist backed by GitHub.

Visitors can view the watchlist, but editing requires an access key.

Watchlist baskets:

```text
52W Low Opportunities
Swing Candidates
Near 52W High Momentum
High Conviction
Personal Watchlist
Research
Avoid / Risky
```

Watchlist file:

```text
data/watchlist/watchlist.csv
```

Expected columns:

```text
symbol
basket
notes
added_at
```

### 8. Fundamentals

Shows real fundamental data where available.

Filters:

- Sector
- Industry
- Symbol / company search
- Fundamental score
- ROE
- Debt / equity
- Revenue growth
- Net profit margin
- Dividend yield
- Market cap in ₹ crore
- PE
- Price-to-book

Leaving sector or industry blank means all sectors / industries are included.

---

## 🧮 Technical Scanner Logic

Technical scanner file:

```text
app/scanners/scan_52w.py
```

The scanner fetches price history using Yahoo Finance and calculates:

```text
current_price
day_change_pct
52w_low
52w_high
distance_pct
distance_from_high_pct
RSI
SMA 50
SMA 200
average volume 20 days
latest volume
volume_ratio
trend
```

### Trend Logic

```text
If current price > SMA 50 → Bullish
Else → Bearish
```

### 52W Low Distance

```text
distance_pct = ((current_price - 52w_low) / 52w_low) * 100
```

### Distance from 52W High

```text
distance_from_high_pct = ((52w_high - current_price) / 52w_high) * 100
```

### Volume Ratio

```text
volume_ratio = latest_volume / average_volume_20
```

---

## 🏗️ Fundamental Data Logic

Fundamental fetcher file:

```text
app/fundamentals/fetch_fundamentals.py
```

Data is fetched from Yahoo Finance where available.

Fields include:

```text
company_name
sector_yf
industry_yf
market_cap
market_cap_cr
trailing_pe
forward_pe
price_to_book
debt_to_equity
roe
roa
operating_margin
net_profit_margin
gross_margin
revenue_growth
earnings_growth
current_ratio
quick_ratio
total_cash
total_cash_cr
total_debt
total_debt_cr
free_cashflow
free_cashflow_cr
operating_cashflow
operating_cashflow_cr
dividend_yield
beta
```

### Readable Crore Values

Large money fields are converted into ₹ crore:

```text
market_cap_cr = market_cap / 1,00,00,000
```

Same logic is used for:

```text
total_cash_cr
total_debt_cr
free_cashflow_cr
operating_cashflow_cr
```

### Dividend Yield Handling

Yahoo Finance may return dividend yield in different formats:

```text
0.015 = 1.5%
1.5   = 1.5%
```

The fetcher corrects this to avoid inflated dividend yield values.

---

## 🧮 Fundamental Scoring Model v2

Fundamental scorer file:

```text
app/fundamentals/fundamental_score.py
```

The model splits fundamentals into components:

```text
Profitability Score      /25
Growth Score             /20
Balance Sheet Score      /20
Cashflow Score           /20
Valuation Score          /15
Fundamental Risk Penalty deducted
```

Final:

```text
fundamental_score =
profitability_score
+ growth_score
+ balance_sheet_score
+ cashflow_score
+ valuation_score
- fundamental_risk_penalty
```

The score is capped between 0 and 100.

---

## 💪 Profitability Score

Uses:

```text
ROE
ROA
Operating Margin
Net Profit Margin
```

Higher score means the business is generating strong returns and margins.

---

## 📈 Growth Score

Uses:

```text
Revenue Growth
Earnings Growth
```

Higher score means sales and earnings are expanding.

---

## 🏦 Balance Sheet Score

Uses:

```text
Debt / Equity
Current Ratio
Quick Ratio
Cash vs Debt
```

Higher score means the company has better financial stability.

---

## 💵 Cashflow Score

Uses:

```text
Operating Cash Flow
Free Cash Flow
Cashflow support for profitability
```

Higher score means profits are supported by actual cash generation.

---

## 🏷️ Valuation Score

Uses:

```text
Trailing PE
Forward PE
Price-to-Book
Dividend Yield
```

Higher score means valuation is more reasonable, subject to available data.

---

## ⚠️ Fundamental Risk Penalty

Penalty is applied for:

```text
Very weak ROE
Very high debt
Negative net margin
Revenue contraction
Earnings contraction
Negative operating cash flow
Negative free cash flow
Very high PE
Abnormally high dividend yield
```

---

## 📊 Relative Strength Logic

Relative strength file:

```text
app/scoring/relative_strength.py
```

It calculates:

```text
1M return
3M return
6M return
Nifty 1M return
Nifty 3M return
Nifty 6M return
Return vs Nifty 1M
Return vs Nifty 3M
Return vs Nifty 6M
Relative Strength Score
Sector Rank
Sector Rank %
```

Approximate trading-day windows:

```text
1M = 21 trading days
3M = 63 trading days
6M = 126 trading days
```

Formula:

```text
return = ((latest_close - past_close) / past_close) * 100
```

Return vs Nifty:

```text
return_vs_nifty = stock_return - nifty_return
```

If Nifty data is rate-limited or unavailable, the system continues and uses absolute returns.

---

## 🧠 Final Score Engine v2

Final scoring file:

```text
app/scoring/score_engine.py
```

Final conviction score:

```text
final_conviction_score =
technical_score * 0.25
+ fundamental_score * 0.35
+ relative_strength_score * 0.25
+ sector_score * 0.15
- risk_penalty
```

The final score is capped between 0 and 100.

The dashboard uses:

```text
score = final_conviction_score
```

for backward compatibility.

---

## 🧪 Score Bands

```text
75+  = A+ High Conviction
65+  = A Strong
55+  = B Watchlist
45+  = C Neutral
35+  = D Weak
<35  = E Avoid
```

---

## ⚠️ Risk Penalty Logic

Risk penalty includes both technical and fundamental risks.

Examples:

```text
Below 200 DMA
Extreme RSI weakness
Sharp daily fall
Far from 52W high
Low volume participation
Very high debt
Negative net margin
Revenue contraction
Earnings contraction
Negative operating cash flow
Negative free cash flow
```

---

## 🏭 Sector Score Logic

Sector score combines:

```text
Average technical score
Average relative strength score
Average fundamental score
```

Current formula:

```text
sector_score =
sector_avg_technical * 0.35
+ sector_avg_relative * 0.35
+ sector_avg_fundamental * 0.30
```

---

## 🧰 Dashboard Filters

The dashboard sidebar supports:

```text
Symbol search
Reason search
Sector filter
Industry filter
Trend filter
Distance from 52W low
Distance from 52W high
RSI
Score
Final conviction score
Technical score
Fundamental score
Relative strength score
Sector score
Risk penalty
Volume ratio
Day change %
Current price
1M return
3M return
6M return
Preset strategies
Custom query tool
Sorting
Max rows displayed
```

---

## 🔎 Custom Query Examples

```python
sector == "Technology" and rsi > 60
```

```python
industry == "Software - Application" and final_conviction_score >= 60
```

```python
fundamental_score >= 70 and relative_strength_score >= 50
```

```python
risk_penalty <= 10 and final_conviction_score >= 60
```

---

## ⭐ Watchlist Logic

The watchlist is stored permanently in GitHub.

File:

```text
data/watchlist/watchlist.csv
```

Editing requires a secret key configured in Streamlit Secrets.

Required Streamlit secrets:

```text
GITHUB_TOKEN
GITHUB_REPO
GITHUB_BRANCH
WATCHLIST_SECRET
```

Example:

```toml
GITHUB_TOKEN = "your_github_token"
GITHUB_REPO = "username/StockGPT"
GITHUB_BRANCH = "main"
WATCHLIST_SECRET = "your_private_password"
```

---

## ⏱️ Scheduling

### Main Scanner

Suggested scan times:

```text
10:00 AM IST
3:40 PM IST
```

GitHub Actions cron uses UTC:

```text
10:00 AM IST = 04:30 UTC
03:40 PM IST = 10:10 UTC
```

Example:

```yaml
schedule:
  - cron: "30 4 * * 1-5"
  - cron: "10 10 * * 1-5"
```

### Weekly Fundamentals

Suggested:

```text
Sunday morning
```

Example:

```yaml
schedule:
  - cron: "30 3 * * 0"
```

This runs at approximately 09:00 AM IST Sunday.

---

## ⚙️ Requirements

Main dependencies:

```text
streamlit
pandas
plotly
yfinance
ta
requests
numpy
```

---

## 🚧 Known Limitations

StockGPT depends heavily on Yahoo Finance data.

Possible limitations:

```text
Some NSE symbols may fail temporarily
Yahoo Finance may rate-limit requests
Fundamental data may be missing for some stocks
Some ratios may not be available for all sectors
Banks and NBFCs need sector-specific scoring treatment
Some small-cap symbols may have incomplete data
```

To reduce missed symbols:

```text
failed_symbols.csv is saved
failed_fundamentals.csv is saved
previously failed symbols are prioritized in future runs
```

---

## 🧩 Why Some Stocks Fail

A stock may fail because:

```text
Yahoo Finance does not have the symbol
Symbol format mismatch
Temporary rate limit
Recently listed stock
Insufficient 1-year price history
Missing OHLC data
Missing fundamental data
```

The system retries failed price symbols one-by-one after batch download.

---

## 🔐 Security Notes

Do not commit secrets to GitHub.

Never commit:

```text
GITHUB_TOKEN
WATCHLIST_SECRET
Telegram bot token
Chat ID
```

Use Streamlit Secrets and GitHub Actions Secrets instead.

---

## 🧠 Current Status

Completed modules:

```text
Broad NSE scanner
Technical scanner
Sector and industry enrichment
Fundamental fetcher
Fundamental scoring v2
Relative strength engine
Final score engine v2
Dashboard filters
Heatmaps
Sector and industry overview
Permanent watchlist
Historical snapshots
SQLite storage
Failed-symbol tracking
```

---

## 🔮 Future Improvements

Possible next upgrades:

```text
Sector-specific fundamental scoring
Bank/NBFC scoring model
Promoter holding data
FII/DII holding data
Quarterly result acceleration
Institutional ownership trend
Delivery volume analysis
Volatility and drawdown score
Telegram alerts
Telegram bot commands
AI-generated stock summaries
Watchlist alerts
Backtesting engine
Export to Excel
Portfolio tracker
```

---

## ⚠️ Disclaimer

StockGPT is an analytical tool for educational and research purposes.

It does not provide financial advice, investment recommendations, or buy/sell signals.

Always do your own research before making investment decisions.

Market data and fundamental data may be delayed, incomplete, inaccurate, or unavailable.

---

## 👤 Author

Built by Raj Ganatra.

StockGPT is designed as a personal market intelligence terminal for Indian equities.

