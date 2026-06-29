---
name: project-context
description: Complete context for the Intraday Trading Agents project. Use this when working on Indian stock market intraday trading, Nifty 50 screener, Small Gap Snap paper trader, backtest engine, or any file in this repo (.opencode/agents/pick.md, paper_trader/trader.py, paper_trader/backtest_small_gap_snap.py, data.json, opencode.json, commt.md, index.html). This skill gives you the full project map — every file, strategy, workflow, data schema, and known issue — so you can understand the codebase without re-exploring.
---

# Intraday Trading Agents — Project Context

This file is the **master reference** for the project. Read it completely when you start working here.

---

## 1. What This Project Does

Automated **Indian NSE stock market intraday trading tools** with three components:

| Component | Entry Point | Purpose |
|-----------|-------------|---------|
| **Intraday Screener** | `/pick` command (via opencode) | Scans Nifty 50, applies 8-point filter, picks best stock, writes HTML report |
| **Paper Trader** | `paper_trader/trader.py` | Auto-trades "Small Gap Snap" strategy (gap 0.3-0.8%, reverse direction) |
| **Backtest Engine** | `paper_trader/backtest_small_gap_snap.py` | Validates gap strategy across 49 stocks × 62 trading days |

---

## 2. Complete File Map

### Configuration
| File | Role |
|------|------|
| `opencode.json` (root) | Main opencode config — defines `/pick` command and `context` block with Nifty 50 list, screener rules, critical issues |
| `.opencode/agents/pick.md` | Agent definition for the intraday screener (primary mode) — full 202-line workflow |
| `.opencode/package.json` | Plugin dependency `@opencode-ai/plugin@1.17.4` |
| `.gitignore` | Ignores `analysis/`, `node_modules/`, `agent/live_*.json`, `logs/` |

### Core Scripts
| File | Lines | What it does |
|------|-------|-------------|
| `paper_trader/trader.py` | 766 | Two-phase paper trader: `--mode morning` (scan gaps at open), `--mode evening` (resolve at close), `--mode backfill` (process history). Uses yfinance. Maintains `ledger.json`. Generates `index.html` dashboard with Chart.js. Sends Formspree reports. |
| `paper_trader/backtest_small_gap_snap.py` | 556 | Parallel backtest (8 threads) across 49 Nifty stocks, 2026-03-16 to 2026-06-15. Outputs `small-gap-snap-backtest.html`. |

### Data
| File | Contents |
|------|----------|
| `data.json` (53k+ lines) | OHLC + ema9, ema21, rsi14, gaps + gap_stats for RELIANCE and TCS (62 trading days) |
| `paper_trader/ledger.json` | Trade journal: stock, gap%, direction, entry, target, SL, result, PnL% |

### HTML Output
| File | Contents |
|------|----------|
| `index.html` | Paper trader dashboard (cumulative PnL, daily breakdown, strategy vs Nifty chart) |
| `small-gap-snap-backtest.html` | Full backtest report |
| `analysis/YYYY-MM-DD/one.html` | (Expected) Screener pick reports — directory doesn't exist yet |

### Docs
| File | Contents |
|------|----------|
| `commt.md` | Cron/automation notes (morning 04:00 UTC, evening 10:30 UTC, IST timezone) |
| `agents.md` (root) | Summary reference generated for quick lookup |
| `md files/*.md` | Strategy documentation (screener, gap-reversal, day-wise, findings) |

---

## 3. The `/pick` Intraday Screener (Primary Agent)

**Source:** `.opencode/agents/pick.md`

### Workflow
1. **Research** — Web search for Nifty 50, Bank Nifty, VIX, FII/DII, sector performance, news
2. **Scan** — Full Nifty 50 for top gainers + highest volume
3. **Anti-manipulation filter** — Prefer stocks >₹500 (Tier 1: >₹1,000). If equal criteria, higher price wins.
4. **8-Point Screener** on 4-6 candidates:

| # | Criteria | What to check |
|---|----------|---------------|
| 1 | **MOMENTUM** | Price > 20 EMA + 50 EMA, higher lows forming |
| 2 | **VOLUME** | >150% of 10-day avg volume |
| 3 | **VOLATILITY** | ATR > 1.5% of price |
| 4 | **SENTIMENT** | Positive catalyst + FII/DII flow supportive |
| 5 | **SUPPORT/RESISTANCE** | Clear support 1-2% below, resistance 3%+ above |
| 6 | **RISK/REWARD** | Minimum 1:2 |
| 7 | **SECTOR STRENGTH** | Stock in a leading sector today |
| 8 | **EMOTION TRACKER** | VIX level, fear/greed, institutional flow |

5. **Pick** — Most passes wins; tiebreak by highest price
6. **Build JSON** — Construct data matching schema in pick.md step 4a
7. **Write JSON** → `agent/live_pick_data.json`
8. **Generate HTML** → `python agent/generate_pick_html.py --stdin --date YYYY-MM-DD < agent/live_pick_data.json`
9. **Output** → `analysis/YYYY-MM-DD/<counter>.html` (one.html, two.html, three.html…)
10. **Cleanup** → `rm agent/live_pick_data.json`
11. **Return** → Final JSON with stock, entry, targets, confidence, reasoning

### JSON Output Schema
```json
{
  "stock": "SYMBOL",
  "company": "Full Company Name",
  "exchange": "NSE",
  "sector": "Sector Name",
  "ltp": "₹price",
  "entry": "entry range",
  "target1": "₹price",
  "target2": "₹price",
  "stopLoss": "₹price",
  "riskReward": "1:2",
  "volumeSignal": "High/Very High/Extreme",
  "momentumScore": 0-100,
  "sentimentScore": 0-100,
  "marketEmotion": "Fear/Greed/Neutral/Euphoria/Panic",
  "emotionOpportunity": "string",
  "catalyst": "string",
  "technicalSetup": "string",
  "keyRisk": "string",
  "confidence": 0-100,
  "strategy": "Momentum/Breakout/Reversal/Gap-Up/Gap-Down",
  "safetyRating": "Safe/Moderate/Aggressive",
  "reasoning": "detailed text",
  "emotionAnalysis": {
    "fearGreedIndex": 0-100,
    "retailSentiment": "Bullish/Bearish/Neutral",
    "institutionalFlow": "Buying/Selling/Neutral",
    "contrarySignal": "string"
  }
}
```

---

## 4. Small Gap Snap — Paper Trader

**Source:** `paper_trader/trader.py`

### Strategy
- Gap **0.3%-0.8%** between previous close and today's open
- **REVERSE** direction: Gap UP → SHORT, Gap DOWN → LONG
- **Target**: 50% of gap filled (if gap was 0.6%, target is 0.3% move in the reverse direction)
- **Stop Loss**: 0.5% from entry
- **Time Exit**: At EOD (3:30 PM IST) if neither target nor SL hit

### Modes

#### `--mode morning` (~9:30 AM IST)
1. Check weekday (skip Sat/Sun)
2. Fetch yesterday's close + today's first 5m candle via yfinance
3. Iterate 49 stocks, calculate gap%
4. If gap 0.3-0.8%, place pending trade (entry = open, target = 50% fill, SL = 0.5%)
5. Save to `paper_trader/ledger.json`
6. Generate/update `index.html` dashboard
7. Send email report via Formspree

#### `--mode evening` (~3:30 PM IST)
1. Load pending trades from ledger
2. Fetch EOD data (daily OHLC or last 5m candle)
3. For each pending trade: check if target hit (✓), SL hit (✗), or time exit
4. Calculate PnL%, update ledger
5. Generate/update `index.html`
6. Send summary report

#### `--mode backfill` (any time)
1. Fetch 70 days of OHLC data
2. For each weekday: calculate gap, simulate entry, check H/L for target/SL
3. Record every trade with result in ledger
4. Generate dashboard

### Nifty 50 Stock List (used by trader.py)
```
RELIANCE.NS, TCS.NS, HDFCBANK.NS, INFY.NS, ICICIBANK.NS, HINDUNILVR.NS, ITC.NS,
SBIN.NS, BHARTIARTL.NS, KOTAKBANK.NS, LT.NS, WIPRO.NS, AXISBANK.NS, BAJFINANCE.NS,
MARUTI.NS, TITAN.NS, SUNPHARMA.NS, ONGC.NS, NTPC.NS, POWERGRID.NS, M&M.NS,
HCLTECH.NS, ULTRACEMCO.NS, NESTLEIND.NS, ASIANPAINT.NS, JSWSTEEL.NS, ADANIPORTS.NS,
HINDALCO.NS, TATASTEEL.NS, BAJAJFINSV.NS, DRREDDY.NS, ADANIENT.NS, BRITANNIA.NS,
CIPLA.NS, COALINDIA.NS, DIVISLAB.NS, EICHERMOT.NS, GRASIM.NS, HEROMOTOCO.NS,
HDFCLIFE.NS, SBILIFE.NS, APOLLOHOSP.NS, BPCL.NS, BEL.NS, BAJAJHLDNG.NS,
INDUSINDBK.NS, SHRIRAMFIN.NS, TATACONSUM.NS, TRENT.NS
```

### Ledger JSON Schema (`paper_trader/ledger.json`)
```json
{
  "trades": [
    {
      "stock": "RELIANCE", "gap": 0.45, "abs_gap": 0.45,
      "vol_ratio": 0, "trade": "SHORT",
      "entry": 1392.56, "target": 1389.16, "sl": 1399.53,
      "close": 1391.17,
      "result": "TARGET_HIT", "pnl": 0.24,
      "date": "2026-03-17", "day": "Tuesday",
      "market_tide": "52% up"
    }
  ],
  "runs": [
    {"date": "2026-03-17", "mode": "morning", "trades": 12}
  ]
}
```

### Dashboard HTML Structure
`index.html` uses Chart.js with:
- Cumulative PnL line chart
- Daily PnL bar chart (with win rate overlay)
- Strategy vs Nifty 50 comparison chart
- Daily history table (expandable rows with morning picks + evening verdicts)

---

## 5. Backtest Engine

**Source:** `paper_trader/backtest_small_gap_snap.py`

- **Period:** 2026-03-16 to 2026-06-15 (62 trading days)
- **Universe:** 49 Nifty stocks (uses `.NS` suffix, different order than trader.py)
- **Parallel:** 8 workers via `ThreadPoolExecutor`
- **Per stock:** OHLC fetched via yfinance, strategy applied historically
- **Output:** `small-gap-snap-backtest.html` — equity curve, win rate by stock, PnL by stock, daily breakdown with expandable cards
- **Key stats:** Win rate, total PnL, avg PnL, profit factor

---

## 6. Critical Issues You Must Know

### 🚫 `agent/generate_pick_html.py` is MISSING
- The `pick.md` agent workflow references this file
- **It does not exist. The `agent/` directory itself does not exist.**
- The workflow needs it to convert the JSON pick data → rich HTML at `analysis/YYYY-MM-DD/<counter>.html`
- **Impact:** Running `/pick` will fail at HTML generation step

### 🚫 `analysis/` directory is MISSING
- Gitignored, but must exist for HTML output
- Create it on demand: `mkdir -p analysis/$(date +%Y-%m-%d)`

### 🚫 `agent/live_pick_data.json` path doesn't exist
- Both the `agent/` directory and the file it writes need creation

---

## 7. Quick Commands

```bash
# Run screener
/pick

# Paper trader — morning scan (9:30 AM IST)
python paper_trader/trader.py --mode morning

# Paper trader — evening verdict (3:30 PM IST)
python paper_trader/trader.py --mode evening

# Paper trader — backfill historical data
python paper_trader/trader.py --mode backfill

# Full backtest
python paper_trader/backtest_small_gap_snap.py

# Create missing directories
mkdir -p agent
mkdir -p analysis/$(date +%Y-%m-%d)
```

---

## 8. Important Conventions

- **Timezone:** Always use IST (UTC+5:30) for dates/times in this project
- **Stock data:** Uses yfinance with `.NS` suffix for NSE stocks
- **HTML style:** Dark theme (background: #0f1117), monospace fonts, Chart.js for graphs, green/red for profit/loss
- **Formspree:** Reports sent to `https://formspree.io/f/mrevdwen`
- **Report naming:** Counter files use English words: one.html, two.html, three.html...
- **Weekend handling:** Dashboard still generated on Sat/Sun but no trades placed
- **Anti-manipulation:** Always prefer stocks >₹500 (>₹1,000 best) — this is a non-negotiable rule
