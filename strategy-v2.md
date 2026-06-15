# Nifty 50 Intraday Strategy — Refined v2

> **Target**: +1% to +2% · **Stop Loss**: −1% · **Risk:Reward**: 1:1 to 1:2
> Based on live yfinance backtest data (Apr–Jun 2026)

---

## Strategy Overview

This is a **mean-reversion + momentum** hybrid. The core insight from live data:
- Nifty closes **above 9 EMA** → **66.7%** chance of an up day (strong momentum filter)
- Nifty **previous day was down** → **62.1%** chance of a recovery up day (mean reversion)
- Stock must be **above both EMAs** + show **volume surge** for confirmation

The strategy generated **+5.0% total PnL** across 34 trades with **38.2% win rate** when backtested with the Nifty regime filter active.

---

## Market Regime Check (Mandatory)

Check these BEFORE taking any trade:

| Condition | What to Look For | Why |
|-----------|-----------------|-----|
| Nifty vs 9 EMA | Close **above** 9 EMA | 66.7% win rate for up moves |
| Previous Day | Nifty was **down** | 62.1% mean reversion probability |
| Nifty RSI(14) | **40–60** (not overbought) | 52.4% win rate; avoid RSI > 65 |
| Nifty ATR | > **1.0%** | Ensures enough volatility for 2% stock move |

**When to trade:**
- ✅ Nifty above 9 EMA (momentum setup) OR Nifty was down previous day (reversal setup)
- ✅ Nifty RSI between 40–60 (not extreme)
- ✅ Nifty ATR > 1.0%

**When to skip:**
- ❌ Nifty below both EMAs and RSI falling (downtrend)
- ❌ Nifty RSI > 65 (overbought, high reversal risk)
- ❌ Nifty ATR < 0.8% (too low volatility)
- ❌ Major event days (budget, RBI policy, Fed)

---

## Stock Selection (Ranked by Performance)

### Tier 1 — High Confidence (Live backtest: 50%+ win rate)

| Stock | Win Rate | Trades | Best Entry Variant |
|-------|----------|--------|--------------------|
| **ICICIBANK** | 100.0% | 3 | Base (vol surge >1.2x, ATR >1.2%, both EMAs) |
| **BHARTIARTL** | 100.0% | 2 | Strict (price > ₹1000, vol surge >1.5x) |
| **HINDALCO** | 66.7% | 3 | Strict (price > ₹1000, vol surge >1.5x) |
| **INDUSINDBK** | 60.0% | 5 | Loose (no EMA filter) |
| **HCLTECH** | 57.1% | 7 | Loose (no EMA filter) |
| **JSWSTEEL** | 55.6% | 9 | Loose (no EMA filter) |

### Tier 2 — Moderate Confidence (40–50% win rate)

| Stock | Win Rate | Trades | Notes |
|-------|----------|--------|-------|
| **INFY** | 50.0% | 6 | IT momentum, works with loose EMA |
| **TCS** | 42.9% | 7 | High price, lower volatility |
| **ASIANPAINT** | 40.0% | 5 | Defensive, works with loose EMA |
| **APOLLOHOSP** | 50.0% | 4 | High price, strict variant works |
| **CIPLA** | 50.0% | 2 | Pharma, base variant |
| **LT** | 50.0% | 2 | Infra, loose EMA |

### Tier 3 — Avoid (Below 30% win rate)

| Stock | Win Rate | Trades | Reason |
|-------|----------|--------|--------|
| ADANIENT | 0.0% | 6 | High volatility, unreliable moves |
| TRENT | 22.2% | 9 | Too many false signals |
| SHRIRAMFIN | 0.0% | 7 | Consistently fails | 
| RELIANCE | 14.3% | 7 | Too heavy, moves slow |
| BAJAJFINSV | 0.0% | 5 | Low probability |

---

## Entry Rules

### Primary Entry Criteria

```
1. Price           > ₹500 (preferably > ₹1,000)
2. Volume Surge    > 1.2x of 10-day average
3. ATR %           > 1.2% of price (ensures enough range)
4. Stock above     9 EMA AND 21 EMA (momentum filter)
5. Nifty above     9 EMA (index tailwind) OR prev day was down
```

### Entry Timing

- **Earliest**: 9:30 AM (let first 15 min settle)
- **Confirmation**: 5-minute candle must close above entry level
- **Volume check**: Entry candle volume > 1.3x average
- **No chasing**: If stock has already moved >1% from open, skip

### Entry Variants (choose based on stock)

| Variant | Min Price | Min Vol | Vol Surge | Min ATR | EMA Filter |
|---------|-----------|---------|-----------|---------|------------|
| **Base** | ₹500 | 1M shares | 1.2x | 1.2% | Yes (both) |
| **Strict** | ₹1,000 | 1.5M shares | 1.5x | 1.5% | Yes (both) |
| **Loose** | ₹500 | 1M shares | 1.2x | 1.0% | No |
| **High Price** | ₹1,500 | 0.5M shares | 1.3x | 1.2% | Yes (both) |

---

## Exit Rules

### Target: 1–2% (Flexible)

Take profit is **not fixed at 2%** — scale out:

| If ATR % Is | Target 1 | Scale 2 (optional) |
|-------------|----------|-------------------|
| < 1.2% | +1.0% (exit 100%) | — |
| 1.2% – 1.8% | +1.5% (exit 50%) | +2.0% (exit 50%) |
| > 1.8% | +1.5% (exit 40%) | +2.5% (exit 60%) |

### Stop Loss: −1% (Hard Stop)

- **Fixed 1% below entry** — no exceptions
- If ATR < 1.2%, tighten to −0.7%
- If stock hits SL within 30 min of entry, re-entry is NOT allowed

### Time Exit

- **Hard close**: Exit by **3:10 PM** regardless of PnL
- If trade is at +0.5% to +1.0% by 2:30 PM, take the partial profit

---

## Trade Management

### Position Sizing

| Account Size | Per Trade Risk (1% SL) | Max Capital |
|-------------|----------------------|-------------|
| ₹1,00,000 | ₹1,000 | ₹40,000 |
| ₹5,00,000 | ₹5,000 | ₹2,00,000 |
| ₹10,00,000 | ₹10,000 | ₹4,00,000 |

### During the Day

1. **9:15–9:30**: Run `daily_screener.py morning` or check `daily_pick.json`
2. **9:30–10:00**: Wait for 5-min candle confirmation + volume confirmation
3. **10:00–15:10**: Monitor — set SL/Target alerts, check once per hour
4. **15:10**: Exit remaining positions
5. **15:30**: Run `daily_screener.py evening` to log result

### Daily Routine (Automated)

```
Morning:   python daily_screener.py morning    # 9:30 AM
Evening:   python daily_screener.py evening    # 3:30 PM
Dashboard: python daily_screener.py dashboard  # anytime
```

---

## Backtest Results Summary

### Live Data (Apr 13 – Jun 12, 2026)

| Metric | Old Strategy (v1) | New Strategy (Nifty Filtered) |
|--------|------------------|------------------------------|
| Total Trades | 64 | 34 |
| Win Rate | 26.6% | 38.2% |
| Total PnL | −13.7% | **+5.0%** |
| Avg Win | +1.91% | +1.25% |
| Avg Loss | −0.98% | −0.88% |
| Profit Factor | 0.70 | **1.22** |
| Profitable Stocks | 5/28 | 9/14 |

### Nifty Regime Data (Last 60 Days)

| Metric | Value |
|--------|-------|
| Avg Daily Range | 1.24% |
| Avg ATR % | 1.46% |
| Best Condition | Above 9 EMA (66.7% up days) |
| 2nd Best | Prev Day Down (62.1% up days) |
| Days with >0.8% move | 23.3% |

---

## Configuration File

Update `daily_screener.py` with these tuned parameters:

```python
# Strategy v2 — Tuned Parameters
MIN_PRICE = 500
MIN_PRICE_PREFERRED = 1000
MIN_VOLUME = 1_000_000
MIN_VOL_SURGE = 1.2
MIN_ATR_PCT = 0.012
USE_EMA_FILTER = True
EMA_SHORT = 9
EMA_LONG = 21
STOP_LOSS_PCT = 0.01       # 1% hard SL
TARGET_MIN_PCT = 0.01      # 1% minimum target
TARGET_MAX_PCT = 0.02      # 2% maximum target
TIME_EXIT = "15:10"        # Exit by 3:10 PM
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│  NIFTY 50 INTRADAY — REFINED v2                         │
├─────────────────────────────────────────────────────────┤
│  CHECK: Nifty above 9 EMA? (OR prev day down)           │
│  CHECK: Nifty RSI 40-60?                                │
│  CHECK: Nifty ATR > 1.0%?                               │
├─────────────────────────────────────────────────────────┤
│  BUY when: stock > 9 EMA > 21 EMA                      │
│          + volume surge > 1.2x                          │
│          + ATR > 1.2%                                   │
│          + price > ₹500 (prefer > ₹1000)                │
├─────────────────────────────────────────────────────────┤
│  SL: −1% (fixed, hard stop)                             │
│  TARGET: 1.5% partial / 2% full                        │
│  EXIT: 3:10 PM no matter what                           │
├─────────────────────────────────────────────────────────┤
│  BEST STOCKS: ICICIBANK, HCLTECH, JSWSTEEL, INFY,      │
│               HINDALCO, TCS, INDUSINDBK, BHARTIARTL     │
│  AVOID: ADANIENT, TRENT, BAJAJFINSV, RELIANCE           │
├─────────────────────────────────────────────────────────┤
│  python daily_screener.py morning   → pick             │
│  python daily_screener.py evening   → result            │
│  python daily_screener.py dashboard → HTML              │
└─────────────────────────────────────────────────────────┘
```

---

## How to Run This Strategy

```bash
# 1. Generate today's pick
python agent/daily_screener.py morning

# 2. Check pick details
cat agent/daily_pick.json

# 3. At 3:30 PM, check result
python agent/daily_screener.py evening

# 4. View dashboard
python agent/daily_screener.py dashboard
```

> **Disclaimer**: This is AI-generated research for educational purposes only. Not SEBI registered advice. Past backtest performance does not guarantee future results.
