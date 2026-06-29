# Intraday Trading Agents — Project Reference

> **Generated:** 2026-06-29  
> **Purpose:** Gives any AI agent a head-start understanding of the project structure, agents, workflows, and known issues.

---

## 1. Overview

This project contains **automated Indian stock market intraday trading tools** for NSE. It has:

| Component | Description |
|-----------|-------------|
| **Intraday Screener Agent** (`/pick`) | Scans Nifty 50 with 8-point filter, picks high-value stocks, generates rich HTML reports |
| **Paper Trader** | Automated "Small Gap Snap" strategy — trades gaps 0.3-0.8%, reverse direction |
| **Backtest Engine** | Validates gap strategy across 49 Nifty stocks over 62 trading days |

---

## 2. Agents

### 2.1 `pick` — Intraday Screener (Primary Agent)

**File:** `.opencode/agents/pick.md`  
**Command:** `/pick`  
**Mode:** `primary`

**Workflow:**
1. Research live NSE data (Nifty, Bank Nifty, VIX, FII/DII, sector performance, news)
2. Scan the full Nifty 50 for top gainers + highest volume
3. Apply primary (anti-manipulation) filter: prefer stocks > ₹500, best > ₹1,000
4. Apply 8-point screener on 4-6 candidates
5. Pick the best stock (most passes, tiebreak by highest price)
6. Build JSON data and pass to `generate_pick_html.py`
7. Output rich HTML to `analysis/YYYY-MM-DD/counter.html`
8. Return final JSON with the pick details

**8-Point Screener Criteria:**
1. **MOMENTUM** — Price > 20 EMA + 50 EMA, higher lows
2. **VOLUME** — >150% of 10-day avg volume
3. **VOLATILITY** — ATR > 1.5% of price
4. **SENTIMENT** — Positive catalyst + FII/DII flow
5. **SUPPORT/RESISTANCE** — Clear levels
6. **RISK/REWARD** — Minimum 1:2
7. **SECTOR STRENGTH** — Leading sector today
8. **EMOTION TRACKER** — VIX, fear/greed, institutional flow

---

## 3. Scripts & Tools

### 3.1 Paper Trader (`paper_trader/trader.py`)

**Strategy:** Small Gap Snap — Gap 0.3-0.8%, reverse direction (gap UP → SHORT, gap DOWN → LONG), target 50% fill, SL 0.5%, time exit at EOD.

**Modes:**
| Mode | When | What it does |
|------|------|--------------|
| `--mode morning` | ~9:30 AM IST | Scans Nifty 50 for gaps, places pending trades |
| `--mode evening` | ~3:30 PM IST | Resolves pending trades with EOD data |
| `--mode backfill` | Any time | Processes historical data, populates ledger |

**Key details:**
- Uses `yfinance` for NSE data (`.NS` suffix)
- Maintains `paper_trader/ledger.json` as trade database
- Generates `index.html` dashboard with Chart.js
- Sends email reports via Formspree
- Runs daily incl weekends (writes dashboard with timestamp, no trades on Sat/Sun)

**Nifty 50 Stock List (trader.py):**
RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, HINDUNILVR, ITC, SBIN, BHARTIARTL, KOTAKBANK, LT, WIPRO, AXISBANK, BAJFINANCE, MARUTI, TITAN, SUNPHARMA, ONGC, NTPC, POWERGRID, M&M, HCLTECH, ULTRACEMCO, NESTLEIND, ASIANPAINT, JSWSTEEL, ADANIPORTS, HINDALCO, TATASTEEL, BAJAJFINSV, DRREDDY, ADANIENT, BRITANNIA, CIPLA, COALINDIA, DIVISLAB, EICHERMOT, GRASIM, HEROMOTOCO, HDFCLIFE, SBILIFE, APOLLOHOSP, BPCL, BEL, BAJAJHLDNG, INDUSINDBK, SHRIRAMFIN, TATACONSUM, TRENT

### 3.2 Backtest Engine (`paper_trader/backtest_small_gap_snap.py`)

Tests the gap strategy over 62 trading days (2026-03-16 to 2026-06-15).
- Parallel execution (8 workers) across 49 stocks
- Outputs `small-gap-snap-backtest.html` with Chart.js visualizations
- Per-stock stats: trades, win rate, total/avg PnL
- Daily breakdown with expandable trade details

---

## 4. Data Files

### 4.1 `data.json`
Historical OHLC data for RELIANCE and TCS (62 trading days).
Per stock: open, high, low, close, volume, ema9, ema21, rsi14, gaps (direction, fill status), gap_stats (fill rates).

### 4.2 `paper_trader/ledger.json`
Trade journal for the paper trader. Contains all trades with: stock, gap%, direction, entry, target, SL, result, PnL%.

---

## 5. Configuration Files

| File | Purpose |
|------|---------|
| `opencode.json` (root) | Main opencode config — defines `/pick` command and project context |
| `.opencode/agents/pick.md` | Agent definition for the intraday screener |
| `.opencode/package.json` | Plugin dependency (`@opencode-ai/plugin@1.17.4`) |
| `.gitignore` | Ignores `analysis/`, `node_modules/`, `agent/live_*.json`, `logs/` |

---

## 6. HTML Output Files

| File | Contents |
|------|----------|
| `index.html` | Paper trader dashboard (cumulative PnL, daily breakdown, strategy vs Nifty chart) |
| `small-gap-snap-backtest.html` | Full backtest report across 49 stocks |
| `analysis/YYYY-MM-DD/one.html` | Intraday screener pick report (auto-named one, two, three…) |

---

## 7. Critical Known Issues

### ⚠️ `agent/generate_pick_html.py` MISSING
The `pick.md` agent workflow references `agent/generate_pick_html.py` to convert the JSON data into rich HTML output. **This file does not exist.** The `agent/` directory itself is missing.

**Impact:** Running `/pick` will fail at the HTML generation step.

**Fix needed:** Create `agent/generate_pick_html.py` that:
1. Reads JSON from stdin (or `agent/live_pick_data.json`)
2. Auto-detects next counter by scanning `analysis/YYYY-MM-DD/`
3. Generates a rich HTML report
4. Prints the output path

### ⚠️ `analysis/` Directory Not Created
The `analysis/` directory (gitignored) must exist for HTML output to work.

---

## 8. Cron / Automation Notes

From `commt.md`:
- **Morning:** Runs at 04:00 UTC (09:30 IST) — scans gaps at open
- **Evening:** Runs at 10:30 UTC (16:00 IST) — resolves pending trades
- Uses `datetime.now(IST)` for correct Indian timezone
- Footer shows "Last run: ... IST"

---

## 9. Quick Reference

```bash
# Run the intraday screener (via opencode)
/pick

# Run paper trader morning scan
python paper_trader/trader.py --mode morning

# Run paper trader evening verdict
python paper_trader/trader.py --mode evening

# Backfill historical data
python paper_trader/trader.py --mode backfill

# Run full backtest
python paper_trader/backtest_small_gap_snap.py
```
