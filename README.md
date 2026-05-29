# 🚀 IndiaPreBreakoutScreener

**NSE/BSE Pre-Breakout Stock Screener** — surfaces the Top 20 potential winners using a
combined GARP + Technical + Smart Money + Policy Catalyst scoring framework.

---

## ✨ Features

| Category | What it does |
|---|---|
| **Hard Exclusions** | Drops banks, NBFCs, insurance, alcohol, tobacco, defence, low-mcap (<₹500 Cr), high D/E |
| **Fundamentals (40%)** | PEG ≤ 1.5, P/E < ROE, Rev/EPS growth ≥ 15%, ROE ≥ 15%, Piotroski proxy |
| **Technicals (30%)** | Coiling phase (79–95% of 52wH), MA stack, RSI 50-65 rising, OBV uptrend, low volatility |
| **Smart Money (20%)** | Institutional holding, analyst consensus, promoter holding proxy |
| **Catalyst (10%)** | Policy theme bonus (renewables, EMS, auto components, green hydrogen…) |
| **UI** | Dark terminal theme, sortable table, CSV export, per-stock chart + metric breakdown |

---

## 🛠 Setup

### Prerequisites
- Python 3.10+
- pip

### Install

```bash
git clone <repo>
cd IndiaPreBreakoutScreener
pip install -r requirements.txt
```

### Run

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## 🔄 How It Works

1. **Universe**: ~200 curated NSE mid/large-cap symbols (extensible — see `UNIVERSE_SYMBOLS` list in `app.py`).
2. **Scan**: Click **🔄 Refresh & Scan Now** in the sidebar. Takes 2–5 minutes depending on rate limits.
3. **Caching**: Results cached for 1 hour (`@st.cache_data(ttl=3600)`) — subsequent loads are instant.
4. **Top 20**: Ranked by composite score, shown in a sortable table with per-stock detail cards.

---

## 📊 Scoring Formula

```
Composite = 0.40 × Fundamentals
           + 0.30 × Technicals
           + 0.20 × SmartMoney
           + 0.10 × Catalyst
```

Each sub-score is normalised to 0–100.

---

## 🔧 Extending the Screener

### Add more stocks
Edit `UNIVERSE_SYMBOLS` in `app.py`. Add any NSE ticker with `.NS` suffix:
```python
UNIVERSE_SYMBOLS.append("NEWSTOCK.NS")
```

### Pull full NSE master list (nsepython)
```python
# Requires: pip install nsepython
from nsepython import nse_eq_symbols
all_symbols = [s + ".NS" for s in nse_eq_symbols()]
```

### Add real bulk/block deal data (nsepython)
```python
from nsepython import nse_largedeals
deals = nse_largedeals("bulk")  # or "block"
# Filter last 30 days, net institutional buying
```

### Add pledge data (Upgrade path)
- **FinEdge API** (`https://finedge.in`) — real-time pledge %, shareholding pattern
- **Screener.in** — ROCE, Piotroski F-Score, 5-yr avg P/E
- **Trendlyne** — insider filings, FII/DII by stock

---

## ⚠️ Known Limitations & Upgrade Paths

| Data Point | Current Approach | Upgrade |
|---|---|---|
| Pledge % | Promoter holding proxy via yfinance | FinEdge API |
| Piotroski F-Score | 5-factor proxy (FCF, NI, D/E, ROE, growth) | Screener.in API |
| ROCE | Not separately computed | Screener.in / FinEdge |
| Bulk/Block Deals | Institutional holding % proxy | nsepython `nse_largedeals()` |
| FII/DII by stock | Analyst consensus as proxy | NSE FII data via nsepython |
| Insider filings | Not fetched | NSE SAST/SEBI RSS feed parsing |
| 5-yr avg P/E | Not fetched | Screener.in |

---

## 📁 File Structure

```
IndiaPreBreakoutScreener/
├── app.py            # Main Streamlit application
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

---

## ⚖️ Disclaimer

> **For educational use only. Not financial advice.**
> Data sourced from public APIs (yfinance). Always verify from official NSE/BSE filings and
> consult a SEBI-registered investment advisor before making any investment decisions.
> Past screening results do not guarantee future returns.
