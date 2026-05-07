# Advanced Features Added

## 1. Weighted Scoring Engine

Each stock gets a weighted score.

Example:
- EPS Growth → 20
- CFO Growth → 20
- Low Debt → 15
- ROCE → 15
- Near 52W Low → 10
- Relative Volume → 10
- Promoter Holding Trend → 10

This allows:
- ranking
- watchlists
- alerts
- portfolio prioritization

---

## 2. Reason Engine

Instead of only returning numbers:

Example:

{
  "symbol": "INFY",
  "score": 81,
  "reasons": [
    "Near 52W low",
    "Positive CFO trend",
    "Low debt",
    "EPS growth strong"
  ]
}

This makes the scanner explainable.

---

## 3. Pure Swing Mode

No fundamentals.

Filters:
- Near 52W low
- Relative volume spike
- RSI oversold
- Bounce setup
- ATR expansion

Designed for temporary panic trades.

---

## 4. Hybrid Mode

Combines:
- quality fundamentals
- temporary price weakness

This becomes your “quality at discount” model.

---

## 5. Recommended Future Modules

- Telegram alerts
- Email alerts
- Sector rotation tracker
- Insider/promoter tracking
- Quarterly result analyzer
- AI-based reason summaries
- Portfolio monitor

---

## 6. IMPORTANT Anti-Block Rules

NEVER:
- blast NSE with parallel requests
- scrape entire exchange rapidly
- retry aggressively
- use cloud IPs without delays

ALWAYS:
- cache responses
- sleep between requests
- reuse sessions
- update incrementally
- store data locally

