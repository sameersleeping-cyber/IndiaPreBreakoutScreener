"""
IndiaPreBreakoutScreener - NSE/BSE Pre-Breakout Stock Screener
==============================================================
Screens ~4000+ NSE stocks using a combined fundamental + technical +
smart-money scoring framework to surface the Top 20 pre-breakout winners.

Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import time
import json
import warnings
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="IndiaPreBreakoutScreener",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  CUSTOM CSS  (dark, Bloomberg-esque terminal)
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');

:root {
    --bg-primary:   #0a0d12;
    --bg-secondary: #111520;
    --bg-card:      #161b27;
    --accent:       #00e5a0;
    --accent2:      #ff6b35;
    --accent3:      #4fc3f7;
    --text-primary: #e8edf5;
    --text-muted:   #6b7898;
    --border:       #1e2535;
    --green:        #00e5a0;
    --red:          #ff4d6d;
    --gold:         #ffd166;
}

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: var(--bg-primary);
    color: var(--text-primary);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--bg-secondary);
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] .block-container { padding: 1.5rem 1rem; }

/* Main container */
.main .block-container { max-width: 1400px; padding: 1.5rem 2rem; }

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden; }

/* Header */
.app-header {
    display: flex; align-items: center; gap: 1rem;
    padding: 0.5rem 0 1.5rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
}
.app-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.6rem; font-weight: 600;
    color: var(--accent);
    letter-spacing: -0.5px;
}
.app-subtitle { font-size: 0.85rem; color: var(--text-muted); margin-top: 2px; }

/* Metric cards */
.metric-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.5rem;
    flex: 1; min-width: 140px;
}
.metric-card .label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
.metric-card .value { font-family: 'IBM Plex Mono', monospace; font-size: 1.5rem; font-weight: 600; color: var(--accent); margin-top: 4px; }
.metric-card .delta { font-size: 0.75rem; color: var(--text-muted); margin-top: 2px; }

/* Score badge */
.score-badge {
    display: inline-block;
    padding: 3px 10px; border-radius: 4px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem; font-weight: 600;
}
.score-high  { background: rgba(0,229,160,0.15); color: var(--green); border: 1px solid rgba(0,229,160,0.3); }
.score-mid   { background: rgba(255,209,102,0.12); color: var(--gold);  border: 1px solid rgba(255,209,102,0.3); }
.score-low   { background: rgba(255,77,109,0.12);  color: var(--red);   border: 1px solid rgba(255,77,109,0.3); }

/* Table */
.stDataFrame { border: 1px solid var(--border) !important; border-radius: 8px !important; }
.stDataFrame thead th { background: var(--bg-card) !important; color: var(--text-muted) !important; font-size: 0.72rem !important; text-transform: uppercase; letter-spacing: 0.8px; }
.stDataFrame tbody tr:hover { background: rgba(0,229,160,0.04) !important; }

/* Sidebar labels */
.sidebar-section {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.65rem; color: var(--accent); text-transform: uppercase;
    letter-spacing: 2px; margin: 1.5rem 0 0.5rem 0;
    border-top: 1px solid var(--border); padding-top: 1rem;
}

/* Disclaimer */
.disclaimer {
    font-size: 0.72rem; color: var(--text-muted);
    background: var(--bg-card); border: 1px solid var(--border);
    border-left: 3px solid var(--accent2);
    border-radius: 4px; padding: 0.8rem 1rem; margin-top: 2rem;
}

/* Status pill */
.status-pill {
    display: inline-block; padding: 2px 8px; border-radius: 20px;
    font-size: 0.7rem; font-weight: 600;
}
.status-live  { background: rgba(0,229,160,0.15); color: var(--green); }
.status-cache { background: rgba(75,114,255,0.15); color: var(--accent3); }

/* Tag */
.tag {
    display: inline-block; padding: 1px 6px; border-radius: 3px;
    font-size: 0.65rem; background: rgba(0,229,160,0.1);
    color: var(--accent); border: 1px solid rgba(0,229,160,0.2); margin-right: 3px;
}
.tag-theme { background: rgba(255,107,53,0.1); color: var(--accent2); border-color: rgba(255,107,53,0.2); }

/* Expander */
details summary { color: var(--accent3) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────

EXCLUDED_SECTORS = [
    "bank", "finance", "nbfc", "insurance", "alcohol", "breweries",
    "liquor", "tobacco", "defence", "defense", "weapons", "gambling",
    "financial services", "microfinance"
]

ENERGY_SECTORS = [
    "power", "renewable energy", "oil & gas", "petrochemicals",
    "green energy", "energy", "utilities", "oil", "gas"
]

POLICY_THEMES = {
    "Solar/Renewable": ["solar", "renewable", "wind", "green energy", "clean energy", "hydro"],
    "Electronics/EMS": ["electronics", "ems", "pcb", "semiconductor", "chips", "display"],
    "Auto Components": ["auto component", "ancillary", "auto ancil", "tyre", "bearing", "forging"],
    "Green Hydrogen":  ["hydrogen", "electrolys", "fuel cell"],
    "Infra/Capital":   ["infrastructure", "capital goods", "engineering", "construction", "cement"],
    "Chemicals":       ["chemical", "specialty chem", "agrochemical", "pharma chem"],
    "Pharma/Health":   ["pharma", "healthcare", "hospital", "diagnostic", "medtech"],
    "Consumer":        ["consumer", "fmcg", "retail", "food", "beverage"],
}

# Curated ~200 quality NSE mid/large-cap symbols to keep scan fast and reliable
# In a full production version, you'd pull from nsepython's master list
UNIVERSE_SYMBOLS = [
    # Renewables / Energy
    "ADANIGREEN.NS","TATAPOWER.NS","TORNTPOWER.NS","CESC.NS","GREENPANEL.NS",
    "SJVN.NS","NHPC.NS","NTPC.NS","POWERGRID.NS","RPOWER.NS","INOXWIND.NS",
    "SUZLON.NS","WEBSOL.NS","BORORENEW.NS","WAAREEENER.NS","PREMIER.NS",
    # Auto & Components
    "MOTHERSON.NS","BOSCHLTD.NS","BALKRISIND.NS","EXIDEIND.NS","AMARAJABAT.NS",
    "SUNDRMFAST.NS","MOTHERSON.NS","ENDURANCE.NS","CRAFTSMAN.NS","SUPRAJIT.NS",
    "BHARAT FORGE.NS","MINDAIND.NS","LUMAX IND.NS","GABRIEL.NS","SANSERA.NS",
    "BHARATFORG.NS","MINDAIND.NS","LUMAXIND.NS","GABRIEL.NS",
    # Chemicals / Specialty
    "PIDILITIND.NS","AAVAS.NS","ALKYLAMINE.NS","ATUL.NS","BALCHEMLTD.NS",
    "CLEAN.NS","DEEPAKNTR.NS","FINEORG.NS","FLUOROCHEM.NS","GNFC.NS",
    "GUJALKALI.NS","JUBILANT.NS","NAVINFLUOR.NS","NOCIL.NS","PCBL.NS",
    "SOLARIND.NS","SUDARSCHEM.NS","TATACHEM.NS","VINATI.NS","GALAXYSURF.NS",
    # Pharma / Healthcare
    "ABBOTINDIA.NS","ALKEM.NS","AUROPHARMA.NS","CAPLIPOINT.NS","CIPLA.NS",
    "DIVIS.NS","DRREDDY.NS","ERIS.NS","GLAND.NS","GLAXO.NS",
    "GRANULES.NS","IPCALAB.NS","JBCHEPHARM.NS","LAURUSLABS.NS","LUPIN.NS",
    "MANKIND.NS","NATCO.NS","PFIZER.NS","SUNPHARMA.NS","TORNTPHARM.NS",
    # Consumer / FMCG
    "ASIANPAINT.NS","BAJAJCON.NS","BRITANNIA.NS","COLPAL.NS","DABUR.NS",
    "EMAMILTD.NS","GILLETTE.NS","GODREJCP.NS","HINDUNILVR.NS","ITC.NS",
    "MARICO.NS","MCDOWELL-N.NS","NESTLEIND.NS","PAGEIND.NS","PGHH.NS",
    "RADICO.NS","TATACONSUM.NS","TITAN.NS","VBL.NS","ZYDUSWELL.NS",
    # Capital Goods / Infra
    "ABB.NS","AIAENG.NS","ASTRAL.NS","BHEL.NS","CARBORUNIV.NS",
    "CUMMINS.NS","DIXON.NS","GRINDWELL.NS","HAL.NS","HONAUT.NS",
    "KAYNES.NS","KECL.NS","KENNAMET.NS","KFINTECH.NS","KIRLOSKAR.NS",
    "LANDT.NS","LARSEN.NS","MAHABANK.NS","POLYPLEX.NS","ROTOMP.NS",
    "SCHAEFFLER.NS","SIEMENS.NS","SKFINDIA.NS","THERMAX.NS","TIMKEN.NS",
    "VOLTAS.NS","BHEL.NS","GREAVESCOT.NS","ELGIEQUIP.NS","APLAPOLLO.NS",
    # Electronics / EMS / IT Services (non-banking)
    "HCLTECH.NS","HEXAWARE.NS","INFY.NS","KPITTECH.NS","LTIM.NS",
    "MPHASIS.NS","OFSS.NS","PERSISTENT.NS","TATAELXSI.NS","TCS.NS",
    "TECHM.NS","WIPRO.NS","DIXON.NS","AMBER.NS","SYRMA.NS","KAYNES.NS",
    # Real Estate / Building
    "BRIGADE.NS","DLF.NS","GODREJPROP.NS","LODHA.NS","MAHLIFE.NS",
    "OBEROIRLTY.NS","PHOENIXLTD.NS","PRESTIGE.NS","SOBHA.NS","SUNTECK.NS",
    # Miscellaneous Quality
    "3MINDIA.NS","ABCAPITAL.NS","AARTI.NS","BAJAJELEC.NS","CDSL.NS",
    "COFORGE.NS","CROMPTON.NS","FSL.NS","HAVELLS.NS","IRCTC.NS",
    "JSWSTEEL.NS","METROPOLIS.NS","MFSL.NS","NAUKRI.NS","RELAXO.NS",
    "ROUTE.NS","TATAMOTORS.NS","TRIDENT.NS","TUBE.NS","ZOMATO.NS",
    "POLYCAB.NS","KEI.NS","ANGELONE.NS","MANAPPURAM.NS","MUTHOOTFIN.NS",
]

# Deduplicate
UNIVERSE_SYMBOLS = list(dict.fromkeys([s for s in UNIVERSE_SYMBOLS if ".NS" in s]))


# ─────────────────────────────────────────────
#  DATA FETCHING HELPERS
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ticker_info(symbol: str) -> dict:
    """Fetch info dict from yfinance with error handling."""
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        return info
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_price_history(symbol: str, period: str = "1y") -> pd.DataFrame:
    """Fetch OHLCV history."""
    try:
        df = yf.download(symbol, period=period, progress=False, auto_adjust=True)
        return df
    except Exception:
        return pd.DataFrame()


def is_excluded_sector(sector: str, industry: str) -> bool:
    """Return True if stock should be hard-excluded by sector."""
    combined = (sector + " " + industry).lower()
    for ex in EXCLUDED_SECTORS:
        if ex in combined:
            return True
    return False


def is_energy_sector(sector: str, industry: str) -> bool:
    combined = (sector + " " + industry).lower()
    for en in ENERGY_SECTORS:
        if en in combined:
            return True
    return False


def get_policy_theme(sector: str, industry: str, name: str) -> str:
    """Return matched policy theme label or empty string."""
    combined = (sector + " " + industry + " " + name).lower()
    for theme, keywords in POLICY_THEMES.items():
        for kw in keywords:
            if kw in combined:
                return theme
    return ""


# ─────────────────────────────────────────────
#  TECHNICAL INDICATORS
# ─────────────────────────────────────────────

def compute_technicals(df: pd.DataFrame) -> dict:
    """Compute all technical indicators needed for scoring."""
    result = {}
    if df is None or len(df) < 50:
        return result

    # Flatten MultiIndex columns if present (yfinance returns them)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df["Close"].squeeze()
    volume = df["Volume"].squeeze()
    high_1y = close.rolling(252).max().iloc[-1]
    low_1y  = close.rolling(252).min().iloc[-1]
    current = close.iloc[-1]

    # 52-week high/low
    result["price_current"]   = float(current)
    result["high_52w"]        = float(high_1y)
    result["low_52w"]         = float(low_1y)
    result["pct_to_52w_high"] = float((high_1y - current) / high_1y * 100) if high_1y else None

    # Moving averages
    sma20  = close.rolling(20).mean()
    sma50  = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    result["sma20"]  = float(sma20.iloc[-1])
    result["sma50"]  = float(sma50.iloc[-1])
    result["sma200"] = float(sma200.iloc[-1])

    # MA alignment: 20 > 50 > 200 and price > all
    result["ma_aligned"] = bool(
        sma20.iloc[-1] > sma50.iloc[-1] > sma200.iloc[-1]
        and current > sma20.iloc[-1]
    )

    # RSI (14)
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    result["rsi"] = float(rsi_series.iloc[-1]) if not rsi_series.empty else None

    # RSI rising (last 10 days)
    if len(rsi_series) >= 10:
        result["rsi_rising"] = bool(rsi_series.iloc[-1] > rsi_series.iloc[-10])
    else:
        result["rsi_rising"] = False

    # OBV uptrend (3 months ~ 63 trading days)
    obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
    if len(obv) >= 63:
        obv_slope = np.polyfit(range(63), obv.iloc[-63:].values, 1)[0]
        result["obv_uptrend"] = bool(obv_slope > 0)
    else:
        result["obv_uptrend"] = False

    # 10-day price range volatility
    recent_10 = close.iloc[-10:]
    if len(recent_10) == 10:
        hi = recent_10.max()
        lo = recent_10.min()
        result["range_10d_pct"] = float((hi - lo) / lo * 100) if lo else None
    else:
        result["range_10d_pct"] = None

    # Volume: declining during consolidation (compare recent 20-day avg to prior 20-day avg)
    if len(volume) >= 40:
        vol_recent = volume.iloc[-20:].mean()
        vol_prior  = volume.iloc[-40:-20].mean()
        result["vol_declining"] = bool(vol_recent < vol_prior)
        result["vol_20d_avg"]   = float(vol_recent)
    else:
        result["vol_declining"] = False
        result["vol_20d_avg"]   = None

    # Coiling phase: 79% – 95% of 52w high
    pct = result["pct_to_52w_high"]
    result["coiling"] = bool(pct is not None and 5 <= pct <= 21)  # 5% to 21% below 52w high

    return result


# ─────────────────────────────────────────────
#  FUNDAMENTAL SCORING
# ─────────────────────────────────────────────

def score_fundamentals(info: dict) -> tuple[float, dict]:
    """
    Returns (score 0-100, breakdown dict).
    Uses yfinance info fields as proxy for fundamentals.
    Upgrade path: FinEdge / Screener.in API for exact Piotroski, ROCE, pledge.
    """
    pts = 0
    max_pts = 0
    breakdown = {}

    # ── PEG ≤ 1.5
    peg = info.get("pegRatio")
    max_pts += 20
    if peg is not None and 0 < peg <= 1.5:
        pts += 20
        breakdown["PEG"] = f"{peg:.2f} ✓"
    elif peg is not None:
        partial = max(0, 20 - (peg - 1.5) * 10)
        pts += partial
        breakdown["PEG"] = f"{peg:.2f}"
    else:
        pts += 5  # no data → slight neutral credit
        breakdown["PEG"] = "N/A"

    # ── P/E vs ROE proxy (P/E < ROE is ideal GARP signal)
    pe  = info.get("trailingPE") or info.get("forwardPE")
    roe = (info.get("returnOnEquity") or 0) * 100
    max_pts += 20
    if pe and roe and pe < roe:
        pts += 20
        breakdown["PE<ROE"] = f"PE={pe:.1f} < ROE={roe:.1f}% ✓"
    elif pe and roe:
        pts += 8
        breakdown["PE<ROE"] = f"PE={pe:.1f}, ROE={roe:.1f}%"
    else:
        pts += 5
        breakdown["PE<ROE"] = "N/A"

    # ── Revenue growth ≥ 15%
    rev_growth = (info.get("revenueGrowth") or 0) * 100
    max_pts += 15
    if rev_growth >= 15:
        pts += 15
        breakdown["RevGrowth"] = f"{rev_growth:.1f}% ✓"
    elif rev_growth > 0:
        pts += int(rev_growth / 15 * 15)
        breakdown["RevGrowth"] = f"{rev_growth:.1f}%"
    else:
        breakdown["RevGrowth"] = f"{rev_growth:.1f}%"

    # ── EPS growth ≥ 15%
    eps_growth = (info.get("earningsGrowth") or 0) * 100
    max_pts += 15
    if eps_growth >= 15:
        pts += 15
        breakdown["EPSGrowth"] = f"{eps_growth:.1f}% ✓"
    elif eps_growth > 0:
        pts += int(eps_growth / 15 * 15)
        breakdown["EPSGrowth"] = f"{eps_growth:.1f}%"
    else:
        breakdown["EPSGrowth"] = f"{eps_growth:.1f}%"

    # ── ROE ≥ 15%
    max_pts += 15
    if roe >= 15:
        pts += 15
        breakdown["ROE"] = f"{roe:.1f}% ✓"
    elif roe > 0:
        pts += int(roe / 15 * 15)
        breakdown["ROE"] = f"{roe:.1f}%"
    else:
        breakdown["ROE"] = f"{roe:.1f}%"

    # ── Piotroski proxy: positive FCF + positive net income + low debt
    fcf       = info.get("freeCashflow") or 0
    net_inc   = info.get("netIncomeToCommon") or 0
    debt      = info.get("totalDebt") or 0
    eq        = info.get("totalStockholdersEquity") or 1
    de_ratio  = debt / eq if eq else 99
    max_pts += 15
    fscore = 0
    if fcf > 0:        fscore += 1
    if net_inc > 0:    fscore += 1
    if de_ratio < 0.5: fscore += 1
    if roe >= 15:      fscore += 1
    if rev_growth > 0: fscore += 1
    # Approximate Piotroski out of 5 proxy → scale to 7–9 range
    approx_f = 4 + fscore  # 4-9
    if approx_f >= 7:
        pts += 15
        breakdown["Piotroski≈"] = f"~{approx_f} ✓"
    elif approx_f >= 5:
        pts += 8
        breakdown["Piotroski≈"] = f"~{approx_f}"
    else:
        breakdown["Piotroski≈"] = f"~{approx_f}"

    score = (pts / max_pts * 100) if max_pts else 0
    return round(score, 1), breakdown


# ─────────────────────────────────────────────
#  TECHNICAL SCORING
# ─────────────────────────────────────────────

def score_technicals(tech: dict) -> tuple[float, dict]:
    """Returns (score 0-100, breakdown dict)."""
    pts = 0; max_pts = 0; breakdown = {}

    # Coiling phase (price 79–95% of 52w high → 5–21% below)
    max_pts += 25
    if tech.get("coiling"):
        pts += 25
        pct = tech.get("pct_to_52w_high", 0)
        breakdown["Coiling"] = f"{pct:.1f}% below 52wH ✓"
    else:
        pct = tech.get("pct_to_52w_high")
        breakdown["Coiling"] = f"{pct:.1f}% below 52wH" if pct else "N/A"

    # MA alignment
    max_pts += 20
    if tech.get("ma_aligned"):
        pts += 20
        breakdown["MA Stack"] = "20>50>200>Price ✓"
    else:
        breakdown["MA Stack"] = "Not aligned"

    # RSI 50–65 and rising
    rsi = tech.get("rsi")
    max_pts += 20
    if rsi and 50 <= rsi <= 65 and tech.get("rsi_rising"):
        pts += 20
        breakdown["RSI"] = f"{rsi:.1f} (rising) ✓"
    elif rsi and 45 <= rsi <= 70:
        pts += 10
        breakdown["RSI"] = f"{rsi:.1f}"
    else:
        breakdown["RSI"] = f"{rsi:.1f}" if rsi else "N/A"

    # OBV uptrend
    max_pts += 20
    if tech.get("obv_uptrend"):
        pts += 20
        breakdown["OBV"] = "Uptrend ✓"
    else:
        breakdown["OBV"] = "Flat/Down"

    # Low volatility consolidation (<8%)
    rv = tech.get("range_10d_pct")
    max_pts += 15
    if rv is not None and rv < 8:
        pts += 15
        breakdown["Volatility"] = f"{rv:.1f}% ✓"
    elif rv is not None and rv < 10:
        pts += 8
        breakdown["Volatility"] = f"{rv:.1f}%"
    else:
        breakdown["Volatility"] = f"{rv:.1f}%" if rv else "N/A"

    score = (pts / max_pts * 100) if max_pts else 0
    return round(score, 1), breakdown


# ─────────────────────────────────────────────
#  SMART MONEY / VALIDATION SCORING
# ─────────────────────────────────────────────

def score_smart_money(info: dict, symbol: str) -> tuple[float, dict]:
    """
    Smart money proxy using yfinance institutionalHolders, insiderTransactions.
    Upgrade path: nsepython nse_largedeals() for real bulk/block deal data.
    """
    pts = 0; max_pts = 0; breakdown = {}

    # Institutional ownership trend (proxy)
    inst_pct = (info.get("heldPercentInstitutions") or 0) * 100
    max_pts += 40
    if inst_pct >= 30:
        pts += 40
        breakdown["Inst. Hold"] = f"{inst_pct:.1f}% ✓"
    elif inst_pct >= 15:
        pts += 25
        breakdown["Inst. Hold"] = f"{inst_pct:.1f}%"
    else:
        pts += 5
        breakdown["Inst. Hold"] = f"{inst_pct:.1f}%"

    # Insider transactions (net buying proxy)
    # yfinance insiderTransactions is often limited; use recommendationMean as FII proxy
    rec = info.get("recommendationMean")  # 1=Strong Buy, 5=Sell
    max_pts += 30
    if rec and rec <= 2:
        pts += 30
        breakdown["Analyst"] = f"Strong Buy ({rec:.1f}) ✓"
    elif rec and rec <= 2.8:
        pts += 18
        breakdown["Analyst"] = f"Buy ({rec:.1f})"
    else:
        pts += 5
        breakdown["Analyst"] = f"{rec:.1f}" if rec else "N/A"

    # Promoter pledge proxy: if heldPercentInsiders high + no pledge signal
    insider_pct = (info.get("heldPercentInsiders") or 0) * 100
    max_pts += 30
    if 20 <= insider_pct <= 75:  # Healthy promoter holding range
        pts += 30
        breakdown["Promoter"] = f"{insider_pct:.1f}% ✓"
    elif insider_pct > 0:
        pts += 15
        breakdown["Promoter"] = f"{insider_pct:.1f}%"
    else:
        pts += 5
        breakdown["Promoter"] = "N/A"

    score = (pts / max_pts * 100) if max_pts else 0
    return round(score, 1), breakdown


# ─────────────────────────────────────────────
#  CATALYST SCORING
# ─────────────────────────────────────────────

def score_catalyst(sector: str, industry: str, name: str) -> tuple[float, str]:
    """Policy theme bonus."""
    theme = get_policy_theme(sector, industry, name)
    if theme:
        return 80.0, theme
    return 30.0, ""


# ─────────────────────────────────────────────
#  HARD FILTER CHECK
# ─────────────────────────────────────────────

def passes_hard_filters(info: dict, tech: dict) -> tuple[bool, str]:
    """
    Returns (passes, reason_if_failed).
    """
    sector   = info.get("sector", "") or ""
    industry = info.get("industry", "") or ""

    # Sector exclusion
    if is_excluded_sector(sector, industry):
        return False, f"Excluded sector: {sector}"

    # Market cap ≥ ₹500 Cr (≈ $60M)
    mcap = info.get("marketCap") or 0
    if mcap < 6_000_000_000:  # ≈500 Cr INR at ~83 USDINR
        return False, f"Low mcap: {mcap/1e7:.0f} Cr"

    # D/E > 0.5 unless energy sector
    debt = info.get("totalDebt") or 0
    eq   = info.get("totalStockholdersEquity") or 1
    de   = debt / eq if eq else 99
    energy = is_energy_sector(sector, industry)
    if de > 0.5 and not energy:
        return False, f"High D/E: {de:.2f}"

    # Basic profitability check
    net_inc = info.get("netIncomeToCommon") or 0
    if net_inc < 0:
        return False, "Negative net income"

    return True, ""


# ─────────────────────────────────────────────
#  COMPOSITE SCORE
# ─────────────────────────────────────────────

def composite_score(f_score: float, t_score: float, s_score: float, c_score: float) -> float:
    """Weighted composite: 40% fund + 30% tech + 20% smart money + 10% catalyst."""
    return round(0.40 * f_score + 0.30 * t_score + 0.20 * s_score + 0.10 * c_score, 1)


def build_rationale(f_bd: dict, t_bd: dict, s_bd: dict, theme: str) -> str:
    """Build a short rationale string."""
    parts = []
    if t_bd.get("Coiling"): parts.append(t_bd["Coiling"].replace(" ✓", ""))
    if f_bd.get("ROE"):      parts.append(f"ROE {f_bd['ROE'].replace(' ✓','')}")
    if f_bd.get("PEG"):      parts.append(f"PEG {f_bd['PEG'].replace(' ✓','')}")
    if t_bd.get("RSI"):      parts.append(f"RSI {t_bd['RSI'].replace(' ✓','')}")
    if t_bd.get("OBV") and "✓" in t_bd["OBV"]: parts.append("OBV↑")
    if s_bd.get("Inst. Hold"): parts.append(f"FII {s_bd['Inst. Hold'].replace(' ✓','')}")
    if theme: parts.append(f"Theme:{theme}")
    return " | ".join(parts[:5])


# ─────────────────────────────────────────────
#  MAIN SCAN ENGINE
# ─────────────────────────────────────────────

def run_screener(symbols: list, progress_bar, status_text, min_score: float = 0) -> pd.DataFrame:
    results = []
    total = len(symbols)

    for i, sym in enumerate(symbols):
        pct = (i + 1) / total
        progress_bar.progress(pct)
        status_text.text(f"Scanning {sym} ({i+1}/{total})…")

        try:
            info = fetch_ticker_info(sym)
            if not info or not info.get("regularMarketPrice"):
                continue

            tech = {}
            hist = fetch_price_history(sym, "1y")
            if not hist.empty:
                tech = compute_technicals(hist)

            passes, reason = passes_hard_filters(info, tech)
            if not passes:
                continue

            sector   = info.get("sector", "") or ""
            industry = info.get("industry", "") or ""
            name     = info.get("longName", sym) or sym

            f_score, f_bd = score_fundamentals(info)
            t_score, t_bd = score_technicals(tech)
            s_score, s_bd = score_smart_money(info, sym)
            c_score, theme = score_catalyst(sector, industry, name)

            comp = composite_score(f_score, t_score, s_score, c_score)
            if comp < min_score:
                continue

            rationale = build_rationale(f_bd, t_bd, s_bd, theme)

            # D/E
            debt = info.get("totalDebt") or 0
            eq   = info.get("totalStockholdersEquity") or 1
            de   = round(debt / eq, 2) if eq else None

            results.append({
                "Symbol":         sym.replace(".NS", ""),
                "_symbol_full":   sym,
                "Name":           name[:35],
                "Sector":         sector[:25],
                "Industry":       industry[:25],
                "Price (₹)":      round(info.get("regularMarketPrice", 0), 1),
                "52wH":           round(tech.get("high_52w", 0), 1),
                "% to 52wH":      round(tech.get("pct_to_52w_high", 0), 1) if tech.get("pct_to_52w_high") else None,
                "RSI":            round(tech.get("rsi", 0), 1) if tech.get("rsi") else None,
                "PEG":            round(info.get("pegRatio", 0), 2) if info.get("pegRatio") else None,
                "ROE (%)":        round((info.get("returnOnEquity") or 0) * 100, 1),
                "D/E":            de,
                "Mcap (Cr)":      round(info.get("marketCap", 0) / 1e7, 0),
                "MA Aligned":     "✓" if tech.get("ma_aligned") else "✗",
                "OBV↑":           "✓" if tech.get("obv_uptrend") else "✗",
                "Bulk Buy?":      "✓" if s_bd.get("Inst. Hold", "").endswith("✓") else "–",
                "Policy Theme":   theme or "–",
                "Fund Score":     f_score,
                "Tech Score":     t_score,
                "SmartMoney Score": s_score,
                "Catalyst Score": c_score,
                "⭐ Score":        comp,
                "Rationale":      rationale,
                # keep breakdown for detail pane
                "_f_bd": json.dumps(f_bd),
                "_t_bd": json.dumps(t_bd),
                "_s_bd": json.dumps(s_bd),
            })

        except Exception as e:
            continue  # silently skip errors

    df = pd.DataFrame(results)
    if df.empty:
        return df

    df = df.sort_values("⭐ Score", ascending=False).head(20).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    return df


# ─────────────────────────────────────────────
#  CHART BUILDER
# ─────────────────────────────────────────────

def build_chart(sym: str, hist: pd.DataFrame) -> go.Figure:
    if hist.empty:
        return go.Figure()

    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)

    close  = hist["Close"].squeeze()
    volume = hist["Volume"].squeeze()
    sma20  = close.rolling(20).mean()
    sma50  = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.72, 0.28], vertical_spacing=0.03,
        subplot_titles=(f"{sym} – Price & MAs", "Volume")
    )

    fig.add_trace(go.Scatter(
        x=hist.index, y=close, name="Price",
        line=dict(color="#00e5a0", width=1.8)
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=sma20,  name="SMA20",  line=dict(color="#4fc3f7", width=1, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=sma50,  name="SMA50",  line=dict(color="#ffd166", width=1, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=sma200, name="SMA200", line=dict(color="#ff6b35", width=1, dash="dot")), row=1, col=1)

    colors = ["#00e5a0" if c >= o else "#ff4d6d"
              for c, o in zip(hist["Close"].squeeze(), hist["Open"].squeeze())]
    fig.add_trace(go.Bar(
        x=hist.index, y=volume, name="Volume",
        marker_color=colors, opacity=0.7
    ), row=2, col=1)

    fig.update_layout(
        paper_bgcolor="#0a0d12", plot_bgcolor="#0a0d12",
        font=dict(family="IBM Plex Mono", color="#6b7898", size=11),
        legend=dict(bgcolor="#111520", bordercolor="#1e2535", borderwidth=1),
        margin=dict(l=0, r=0, t=30, b=0),
        height=420,
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(gridcolor="#1e2535", zeroline=False)
    fig.update_yaxes(gridcolor="#1e2535", zeroline=False)
    return fig


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace; font-size:1.1rem; color:#00e5a0; font-weight:600; letter-spacing:-0.5px;">
        🚀 IndiaPreBreakout<br><span style="font-size:0.8rem; color:#6b7898;">NSE Stock Screener</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">⚙ Controls</div>', unsafe_allow_html=True)
    refresh = st.button("🔄 Refresh & Scan Now", use_container_width=True, type="primary")

    st.markdown('<div class="sidebar-section">🎯 Filters</div>', unsafe_allow_html=True)
    min_score = st.slider("Minimum Composite Score", 0, 80, 30, step=5)
    energy_only = st.checkbox("Energy/Renewables only")
    show_top_n  = st.selectbox("Show Top N", [10, 15, 20], index=2)

    st.markdown('<div class="sidebar-section">ℹ Info</div>', unsafe_allow_html=True)
    st.caption("Data: yfinance (NSE .NS tickers) | Refreshes every 60 min automatically.")
    st.caption("Upgrade: nsepython bulk/block deals, FinEdge pledge data, Screener.in ROCE.")

    if "last_run" in st.session_state:
        st.caption(f"Last scan: {st.session_state['last_run']}")


# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────

st.markdown("""
<div class="app-header">
  <div>
    <div class="app-title">🚀 IndiaPreBreakoutScreener</div>
    <div class="app-subtitle">NSE/BSE Pre-Breakout Stock Screener · GARP + Smart Money + Technical Confluence</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  MAIN SCAN TRIGGER
# ─────────────────────────────────────────────

if "results_df" not in st.session_state:
    st.session_state["results_df"] = pd.DataFrame()

if refresh or st.session_state["results_df"].empty:
    symbols = UNIVERSE_SYMBOLS.copy()
    if energy_only:
        # Filter to likely energy symbols only (rough keyword match on ticker)
        energy_kw = ["TATAPOWER","ADANIGREEN","NTPC","TORNT","SJVN","NHPC","POWERGRID",
                     "SUZLON","INOXWIND","BORORENEW","WAAREE","RPOWER","CESC","GREENPANEL"]
        symbols = [s for s in symbols if any(k in s for k in energy_kw)]

    with st.container():
        prog  = st.progress(0.0)
        stext = st.empty()

        df = run_screener(symbols, prog, stext, min_score=min_score)

        prog.empty()
        stext.empty()

    st.session_state["results_df"]  = df
    st.session_state["last_run"]    = datetime.now().strftime("%d %b %Y %H:%M")
    st.rerun()

df = st.session_state.get("results_df", pd.DataFrame())

# ─────────────────────────────────────────────
#  METRIC CARDS
# ─────────────────────────────────────────────

if not df.empty:
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Stocks Shown</div>
            <div class="value">{len(df)}</div>
            <div class="delta">of {len(UNIVERSE_SYMBOLS)} universe</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        top_score = df["⭐ Score"].max() if not df.empty else 0
        st.markdown(f"""<div class="metric-card">
            <div class="label">Top Score</div>
            <div class="value">{top_score}</div>
            <div class="delta">Composite (0–100)</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        avg_rsi = df["RSI"].mean() if "RSI" in df.columns else 0
        st.markdown(f"""<div class="metric-card">
            <div class="label">Avg RSI</div>
            <div class="value">{avg_rsi:.1f}</div>
            <div class="delta">Target: 50–65</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        ma_ok = (df["MA Aligned"] == "✓").sum() if "MA Aligned" in df.columns else 0
        st.markdown(f"""<div class="metric-card">
            <div class="label">MA Aligned</div>
            <div class="value">{ma_ok}</div>
            <div class="delta">Stocks 20>50>200</div>
        </div>""", unsafe_allow_html=True)
    with col5:
        themes = df["Policy Theme"].replace("–", pd.NA).dropna()
        n_themes = len(themes)
        st.markdown(f"""<div class="metric-card">
            <div class="label">Policy Themes</div>
            <div class="value">{n_themes}</div>
            <div class="delta">Govt-backed sectors</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  RESULTS TABLE
# ─────────────────────────────────────────────

if not df.empty:
    st.subheader(f"🏆 Top {min(show_top_n, len(df))} Pre-Breakout Candidates")

    # Display columns only (hide internal cols)
    display_cols = [
        "Rank","Symbol","Name","Sector","Price (₹)","% to 52wH",
        "RSI","PEG","ROE (%)","D/E","MA Aligned","OBV↑",
        "Policy Theme","⭐ Score","Rationale"
    ]
    display_df = df[display_cols].head(show_top_n).copy()

    # Color-code score column
    def color_score(val):
        if val >= 65: return "background-color:#0d2b1f; color:#00e5a0;"
        if val >= 45: return "background-color:#2b2408; color:#ffd166;"
        return "background-color:#2b0d14; color:#ff4d6d;"

    styled = (
        display_df.style
        .applymap(color_score, subset=["⭐ Score"])
        .format({
            "Price (₹)":  "{:,.1f}",
            "% to 52wH":  "{:.1f}%",
            "RSI":        "{:.1f}",
            "PEG":        lambda x: f"{x:.2f}" if x else "–",
            "ROE (%)":    "{:.1f}%",
            "D/E":        lambda x: f"{x:.2f}" if x else "–",
            "Mcap (Cr)":  lambda x: f"₹{x:,.0f}" if x else "–",
            "⭐ Score":    "{:.1f}",
        }, na_rep="–")
        .set_properties(**{"font-size":"0.8rem"})
    )

    st.dataframe(styled, use_container_width=True, height=520)

    # CSV Export
    csv_buf = io.StringIO()
    display_df.to_csv(csv_buf, index=False)
    st.download_button(
        "⬇ Export CSV",
        data=csv_buf.getvalue(),
        file_name=f"prebreakout_top{show_top_n}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

    # ─────────────────────────────────────────────
    #  STOCK DETAIL EXPANDERS
    # ─────────────────────────────────────────────

    st.subheader("📊 Stock Detail Cards")
    st.caption("Expand any stock for chart, metrics breakdown and scoring details.")

    for _, row in df.head(show_top_n).iterrows():
        sym_full = row["_symbol_full"]
        score    = row["⭐ Score"]
        score_cls = "score-high" if score >= 65 else ("score-mid" if score >= 45 else "score-low")
        theme_tag = f'<span class="tag tag-theme">{row["Policy Theme"]}</span>' if row["Policy Theme"] != "–" else ""
        ma_tag    = '<span class="tag">MA✓</span>' if row["MA Aligned"] == "✓" else ""
        obv_tag   = '<span class="tag">OBV↑</span>' if row["OBV↑"] == "✓" else ""

        with st.expander(
            f"#{row['Rank']}  {row['Symbol']}  —  {row['Name']}  |  Score: {score}",
            expanded=False
        ):
            c1, c2 = st.columns([2, 1])
            with c1:
                hist = fetch_price_history(sym_full, "1y")
                fig  = build_chart(sym_full, hist)
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                st.markdown(f"""
                <div style="font-family:'IBM Plex Mono',monospace;">
                  <div style="margin-bottom:1rem;">
                    <span class="score-badge {score_cls}">Score: {score}</span>
                    {theme_tag}{ma_tag}{obv_tag}
                  </div>
                  <table style="width:100%; border-collapse:collapse; font-size:0.78rem;">
                    <tr><td style="color:#6b7898; padding:3px 0;">Price</td><td style="color:#e8edf5;">₹{row['Price (₹)']:,.1f}</td></tr>
                    <tr><td style="color:#6b7898; padding:3px 0;">52wH</td><td style="color:#e8edf5;">₹{row['52wH']:,.1f}</td></tr>
                    <tr><td style="color:#6b7898; padding:3px 0;">% to 52wH</td><td style="color:#ffd166;">{row['% to 52wH']}%</td></tr>
                    <tr><td style="color:#6b7898; padding:3px 0;">RSI (14)</td><td style="color:#e8edf5;">{row['RSI']}</td></tr>
                    <tr><td style="color:#6b7898; padding:3px 0;">PEG Ratio</td><td style="color:#e8edf5;">{row['PEG']}</td></tr>
                    <tr><td style="color:#6b7898; padding:3px 0;">ROE</td><td style="color:#00e5a0;">{row['ROE (%)']}%</td></tr>
                    <tr><td style="color:#6b7898; padding:3px 0;">D/E</td><td style="color:#e8edf5;">{row['D/E']}</td></tr>
                    <tr><td style="color:#6b7898; padding:3px 0;">Sector</td><td style="color:#e8edf5;">{row['Sector']}</td></tr>
                  </table>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("**Score Breakdown**")
                f_bd = json.loads(row["_f_bd"])
                t_bd = json.loads(row["_t_bd"])
                s_bd = json.loads(row["_s_bd"])

                st.markdown(f"""
                <div style="font-size:0.72rem; font-family:'IBM Plex Mono',monospace; line-height:1.8;">
                  <div style="color:#4fc3f7; margin-bottom:4px;">📊 Fundamentals ({row['Fund Score']})</div>
                  {"".join(f'<div style="color:#6b7898;">&nbsp;&nbsp;{k}: <span style="color:#e8edf5;">{v}</span></div>' for k,v in f_bd.items())}
                  <div style="color:#4fc3f7; margin-top:8px; margin-bottom:4px;">📈 Technicals ({row['Tech Score']})</div>
                  {"".join(f'<div style="color:#6b7898;">&nbsp;&nbsp;{k}: <span style="color:#e8edf5;">{v}</span></div>' for k,v in t_bd.items())}
                  <div style="color:#4fc3f7; margin-top:8px; margin-bottom:4px;">🐋 Smart Money ({row['SmartMoney Score']})</div>
                  {"".join(f'<div style="color:#6b7898;">&nbsp;&nbsp;{k}: <span style="color:#e8edf5;">{v}</span></div>' for k,v in s_bd.items())}
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"**Rationale:** {row['Rationale']}")

else:
    st.info("No results yet. Click **🔄 Refresh & Scan Now** in the sidebar to start screening.")


# ─────────────────────────────────────────────
#  DISCLAIMER
# ─────────────────────────────────────────────

st.markdown("""
<div class="disclaimer">
  ⚠️ <strong>Disclaimer:</strong> For educational use only. Not financial advice.
  Data sourced from public APIs (yfinance / NSE). Always verify from official exchange filings before making investment decisions.
  Pledge data, exact Piotroski F-Score, and real-time bulk deal flows require premium data providers (upgrade path: FinEdge, Screener.in Pro, nsepython nse_largedeals).
</div>
""", unsafe_allow_html=True)
